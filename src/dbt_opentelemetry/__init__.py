from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Span, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

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

root_span: Span
