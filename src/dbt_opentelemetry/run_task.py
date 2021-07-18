import json

import dbt.task.run
from dbt.node_types import RunHookType
from opentelemetry.propagators.textmap import CarrierT
from opentelemetry.trace.status import Status, StatusCode
from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

import dbt_opentelemetry
from dbt_opentelemetry import tracer

# Keep pointers to originals to avoid recursion issues
original_run_task = dbt.task.run.RunTask


class RunTaskOpenTelemetry(original_run_task):
    def run_hooks(self, adapter, hook_type, extra_context):
        if hook_type == RunHookType.Start:
            # not proud of this hehe..
            dbt_opentelemetry.root_span = tracer.start_span("run_start_hooks")
            try:
                super(RunTaskOpenTelemetry, self).run_hooks(
                    adapter, hook_type, extra_context
                )
            finally:
                dbt_opentelemetry.root_span.set_status(Status(StatusCode.OK))
                dbt_opentelemetry.root_span.end()
        else:
            run_end_hooks_span = tracer.start_span(
                "run_end_hooks",
                context=trace.set_span_in_context(dbt_opentelemetry.root_span),
            )
            try:
                super(RunTaskOpenTelemetry, self).run_hooks(
                    adapter, hook_type, extra_context
                )
            finally:
                run_end_hooks_span.set_status(Status(StatusCode.OK))
                run_end_hooks_span.end()
                # We write the trace context to a file
                # so other processes (in production, Airflow for example)
                # can add to the trace
                propagator = TraceContextTextMapPropagator()
                carrier: CarrierT = {}
                propagator.inject(
                    carrier, trace.set_span_in_context(dbt_opentelemetry.root_span)
                )
                with open("trace.json", "w") as file:
                    file.write(json.dumps(carrier))
