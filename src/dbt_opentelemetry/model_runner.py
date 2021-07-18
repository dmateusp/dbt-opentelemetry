"""Patch the class that runs models."""

from typing import Dict, List, Optional

import dbt.main
import dbt.task.run
from dbt.contracts.graph.compiled import CompiledNode
from opentelemetry.context.context import Context
from opentelemetry.sdk.trace import Span
from opentelemetry.trace.status import Status, StatusCode
from opentelemetry.trace import Link
from opentelemetry import trace

import dbt_opentelemetry
from dbt_opentelemetry import tracer

# Keep pointers to originals to avoid recursion issues
original_model_runner = dbt.task.run.ModelRunner


class ModelRunnerOpenTelemetry(original_model_runner):
    # We save model spans so we can link children and parents
    saved_spans: Dict[str, Span] = {}

    def execute(self, model: CompiledNode, manifest):
        context: Optional[Context] = None
        links: Optional[List[Link]] = None
        if model.depends_on.nodes:
            parents = (
                trace.set_span_in_context(self.saved_spans.get(parent))
                for parent in model.depends_on.nodes
                if parent in self.saved_spans
            )
            # If there are parents, we pick the first parent
            context = next(parents, None)
            # We add the rest of the parents as links
            # TODO: right now, adding the links in the start_span call seems to break the trace export
            links = [Link(trace.set_span_in_context(p)) for p in list(parents)]
        # the was no parent or the parents were not models
        if not context:
            # If there are no parents, we just link that span to the root span
            context = trace.set_span_in_context(dbt_opentelemetry.root_span)
        # We create one copy of span per parent so we can visualize all the paths
        self.span = tracer.start_span(model.unique_id, context=context)

        self.span.set_attributes(
            {
                "alias": model.alias,
                "compiled_path": model.compiled_path,
                "materialization": model.get_materialization(),
                "dbt_tags": model.tags,
            }
        )

        try:
            res = super(ModelRunnerOpenTelemetry, self).execute(model, manifest)
            self.span.set_status(Status(StatusCode.OK, description="Model ran fine"))
            self.saved_spans[model.unique_id] = self.span
            return res
        finally:
            self.span.end()
