"""This is where we do all the "monkey patching" to wrap the functions we want to trace in Open Telemetry code."""

import dbt.main
import dbt.task.run
from dbt.node_types import RunHookType
from dbt.contracts.graph.compiled import CompiledNode
import sys
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry import trace
from opentelemetry.sdk.trace import Span, TracerProvider
from opentelemetry.context.context import Context
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.propagation import set_span_in_context
from opentelemetry.trace.status import Status, StatusCode
import logging
from typing import List, Dict

# Open Telemetry tracing init
trace.set_tracer_provider(
    TracerProvider(
        resource=Resource.create(
            {
                "service.name": "dbt",
            }
        ),
    )
)

trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint="localhost:4317",
        )
    )
)

tracer = trace.get_tracer("dbt")

# Logging init
logger = logging.getLogger(__name__)

# Keep pointers to originals to avoid recursion issues
original_run_task = dbt.task.run.RunTask
root_span: Span


class RunTaskOpenTelemetry(original_run_task):
    def run_hooks(self, adapter, hook_type, extra_context):
        if hook_type == RunHookType.Start:
            # not proud of this hehe..
            global root_span
            root_span = tracer.start_span("run_start_hooks")
            try:
                super(RunTaskOpenTelemetry, self).run_hooks(
                    adapter, hook_type, extra_context
                )
            finally:
                root_span.set_status(Status(StatusCode.OK))
                root_span.end()
        else:
            run_end_hooks_span = tracer.start_span(
                "run_end_hooks", context=set_span_in_context(root_span)
            )
            try:
                super(RunTaskOpenTelemetry, self).run_hooks(
                    adapter, hook_type, extra_context
                )
            finally:
                run_end_hooks_span.set_status(Status(StatusCode.OK))
                run_end_hooks_span.end()


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
            parents = [node for node in model.depends_on.nodes]
            contexts = [
                set_span_in_context(node)
                for p in parents
                for node in self.saved_spans[p]
            ]
        else:
            # If there are no parents, we just link that span to the root span
            contexts = [set_span_in_context(root_span)]
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


def main():
    logger.info("Monkey patching dbt with dbt-opentelemetry..")
    dbt.task.run.ModelRunner = ModelRunnerOpenTelemetry
    dbt.task.run.RunTask = RunTaskOpenTelemetry
    dbt.main.main(sys.argv[1:])
