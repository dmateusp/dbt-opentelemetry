"""Simulates running another process after dbt as part of the same data pipeline, reusing the trace."""
import json

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.propagators.textmap import CarrierT
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from time import sleep
import sys

# Open Telemetry tracing init
trace.set_tracer_provider(
    TracerProvider(
        resource=Resource.create(
            {
                "service.name": "other-process",
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

tracer = trace.get_tracer("other-process")


def main():
    path_to_trace_file = sys.argv[1]
    with open(path_to_trace_file, "r") as file:
        data_pipeline_trace: CarrierT = json.load(file)
    propagator = TraceContextTextMapPropagator()
    context = propagator.extract(data_pipeline_trace)
    with tracer.start_as_current_span("other_process", context):
        sleep(0.5)


if __name__ == "__main__":
    main()
