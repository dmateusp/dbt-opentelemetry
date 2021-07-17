"""Patch the class that runs models."""

from typing import Dict, List

import dbt.main
import dbt.task.run
from dbt.contracts.graph.compiled import CompiledNode
from opentelemetry.context.context import Context
from opentelemetry.sdk.trace import Span
from opentelemetry.trace.status import Status, StatusCode
from opentelemetry import trace

import dbt_opentelemetry
from dbt_opentelemetry import tracer

# Keep pointers to originals to avoid recursion issues
original_model_runner = dbt.task.run.ModelRunner


class ModelRunnerOpenTelemetry(original_model_runner):
    # We save model spans so we can link children and parents
    saved_spans: Dict[str, List[Span]] = {}

    def execute(self, model: CompiledNode, manifest):
        contexts: List[Context] = []
        if model.depends_on.nodes:
            # If there are parents, we create a span for each parent
            # so all the "paths" of the DAG are represented.
            # This creates duplication, but allows us to visualize the full DAG in one trace.
            contexts = [
                trace.set_span_in_context(node)
                for p in model.depends_on.nodes
                for node in self.saved_spans[p]
            ]
        else:
            # If there are no parents, we just link that span to the root span
            contexts = [trace.set_span_in_context(dbt_opentelemetry.root_span)]
        # We create one copy of span per parent so we can visualize all the paths
        spans = [tracer.start_span(model.unique_id, context=c) for c in contexts]

        try:
            res = super(ModelRunnerOpenTelemetry, self).execute(model, manifest)
            for span in spans:
                span.set_status(Status(StatusCode.OK, description="Model ran fine"))
            self.saved_spans[model.unique_id] = spans
            return res
        finally:
            for span in spans:
                span.end()
