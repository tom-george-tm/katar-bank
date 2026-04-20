from agent.core.config import settings
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


def setup_opentelemetry():
    resource = Resource.create({"service.name": settings.AGENT_NAME})
    provider = TracerProvider(resource=resource)

    # Export to Console for Local Docker Logs
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    # Export to GCP Cloud Trace
    exporter = CloudTraceSpanExporter(project_id=settings.GOOGLE_CLOUD_PROJECT)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)

    return trace.get_tracer(__name__)


tracer = setup_opentelemetry()


def instrument_fastapi(app):
    FastAPIInstrumentor.instrument_app(app)