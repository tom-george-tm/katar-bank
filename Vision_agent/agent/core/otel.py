"""OpenTelemetry setup for ADK A2A agent.

Initializes the global TracerProvider so ADK's built-in instrumentation (LLM calls,
tool runs, sub-agent delegation) is exported. Call setup_opentelemetry() before
creating the Runner or any agents. Then call instrument_fastapi(app) after
building the FastAPI app.

See: https://docs.cloud.google.com/stackdriver/docs/instrumentation/ai-agent-adk
"""

from __future__ import annotations

import os
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

# Lazy imports so GCP/optional deps don't break when not configured
def _get_cloud_trace_exporter():
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
    return CloudTraceSpanExporter


def setup_opentelemetry() -> trace.Tracer:
    """Configure OpenTelemetry and set the global TracerProvider.

    Must be called once at application startup, before any ADK Runner or Agent
    is created, so that ADK's built-in spans (call_llm, tools, sub_agents)
    are recorded and exported.

    - Always adds ConsoleSpanExporter for local logs.
    - Adds CloudTraceSpanExporter when GOOGLE_CLOUD_PROJECT is set and not a placeholder.
    - Sets resource service.name (and optional service.version) for GCP.

    Returns:
        A Tracer instance for custom spans (e.g. in tools).
    """
    from agent.core.config import settings

    service_name = os.environ.get("OTEL_SERVICE_NAME") or settings.AGENT_NAME
    resource_attrs: dict[str, Any] = {"service.name": service_name}
    if settings.AGENT_VERSION:
        resource_attrs["service.version"] = settings.AGENT_VERSION

    resource = Resource.create(resource_attrs)
    provider = TracerProvider(resource=resource)

    # Console exporter (always) for local/docker logs
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    # GCP Cloud Trace when explicitly enabled and project is set
    project = (settings.GOOGLE_CLOUD_PROJECT or "").strip()
    if (
        settings.ENABLE_CLOUD_TRACE
        and project
        and project not in ("CHANGE_ME", "your-project-id", "")
    ):
        try:
            CloudTraceSpanExporter = _get_cloud_trace_exporter()
            exporter = CloudTraceSpanExporter(project_id=project)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except Exception:
            pass  # e.g. missing credentials; console only

    trace.set_tracer_provider(provider)

    # Instrument outbound HTTP so MCP and remote agent calls are traced
    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        RequestsInstrumentor().instrument()
    except Exception:
        pass

    # Instrument Google GenAI so Gemini/Vertex LLM calls are traced (ADK uses these)
    try:
        from opentelemetry.instrumentation.google_genai import GoogleGenAiSdkInstrumentor
        GoogleGenAiSdkInstrumentor().instrument()
    except Exception:
        pass

    return trace.get_tracer(__name__, settings.AGENT_VERSION or "0.0.0")


def instrument_fastapi(app) -> None:
    """Instrument the FastAPI app for request/response tracing.

    Call this after building the app (e.g. after to_a2a(...)) so that
    HTTP requests to the A2A server are traced.
    """
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FastAPIInstrumentor.instrument_app(app)


def get_tracer(name: str | None = None, version: str | None = None) -> trace.Tracer:
    """Return a tracer for custom spans (e.g. inside tools or helpers)."""
    return trace.get_tracer(name or __name__, version)
