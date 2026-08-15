# phoenix_tracer.py - Arize Phoenix integration for tracing.
"""
phoenix_tracer.py
─────────────────────────────────────────────────────────────────
Arize Phoenix observability setup for the AI Deep Research Agent.

What this module does:
  1. Launches an embedded Phoenix server (localhost:6006) or points
     at an external Phoenix collector via PHOENIX_COLLECTOR_ENDPOINT.
  2. Registers OpenTelemetry (OTEL) trace providers so every LLM call,
     RAG operation, and agent step is automatically captured.
  3. Auto-instruments LangChain / LangGraph (covers the full research
     graph including planner, search, retrieval, analysis, report agents).
  4. Auto-instruments OpenAI and Groq HTTP calls if those SDKs are present.
  5. Exposes a manual span context manager (`phoenix_span`) for
     custom instrumentation of our bespoke RAG steps (embedding,
     Qdrant retrieval, cross-encoder reranking, KG builder).

Environment variables (all optional – sensible defaults provided):
  PHOENIX_ENABLED            true | false  (default: true)
  PHOENIX_COLLECTOR_ENDPOINT grpc://host:4317  (default: embedded server)
  PHOENIX_PROJECT_NAME       any string  (default: "deep-research-agent")
  PHOENIX_PORT               int  (default: 6006)
"""

import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────
# Global state
# ────────────────────────────────────────────────────────────────────
_phoenix_session = None          # embedded px.launch_app() session
_tracer_provider = None          # OTEL TracerProvider
_tracer = None                   # module-level OTEL Tracer
_initialized = False


# ────────────────────────────────────────────────────────────────────
# Public init – call once at application startup (main.py)
# ────────────────────────────────────────────────────────────────────
def init_phoenix() -> bool:
    """
    Set up Arize Phoenix tracing.

    Returns True if successfully initialised, False if Phoenix is
    disabled or the packages are not installed.
    """
    global _phoenix_session, _tracer_provider, _tracer, _initialized

    if _initialized:
        return True

    # Respect kill-switch
    if os.getenv("PHOENIX_ENABLED", "true").lower() in ("false", "0", "no"):
        logger.info("[Phoenix] Observability disabled via PHOENIX_ENABLED=false")
        return False

    try:
        import phoenix as px
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from phoenix.otel import register

        project_name = os.getenv("PHOENIX_PROJECT_NAME", "deep-research-agent")
        collector_endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "")
        port = int(os.getenv("PHOENIX_PORT", "6006"))
        host = os.getenv("PHOENIX_HOST", "0.0.0.0")

        # ── 1. Launch embedded Phoenix UI (if no external collector) ──
        if not collector_endpoint:
            try:
                _phoenix_session = px.launch_app(host=host, port=port)
                logger.info(
                    f"[Phoenix] Embedded UI launched → http://{host}:{port}"
                )
            except Exception as e:
                logger.warning(f"[Phoenix] Could not launch embedded UI: {e}")

        # ── 2. Register OTEL TracerProvider via phoenix.otel ──
        #    `register()` creates an OTLP exporter pointing at Phoenix
        #    and sets it as the global OTEL provider.
        tracer_provider = register(
            project_name=project_name,
            endpoint=collector_endpoint or f"http://localhost:{port}",
        )
        _tracer_provider = tracer_provider
        _tracer = trace.get_tracer(__name__)

        # ── 3. Auto-instrument LangChain / LangGraph ──
        try:
            from openinference.instrumentation.langchain import LangChainInstrumentor
            LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
            logger.info("[Phoenix] LangChain/LangGraph auto-instrumented ✓")
        except ImportError:
            logger.warning(
                "[Phoenix] openinference-instrumentation-langchain not installed. "
                "LangChain spans will be missing."
            )

        # ── 4. Auto-instrument OpenAI (if present) ──
        try:
            from openinference.instrumentation.openai import OpenAIInstrumentor
            OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
            logger.info("[Phoenix] OpenAI auto-instrumented ✓")
        except (ImportError, Exception) as e:
            logger.debug(f"[Phoenix] OpenAI instrumentation skipped: {e}")

        _initialized = True
        logger.info(
            f"[Phoenix] Observability initialised — project='{project_name}' ✓"
        )
        return True

    except ImportError as e:
        logger.warning(
            f"[Phoenix] Package not installed ({e}). "
            "Run: pip install arize-phoenix openinference-instrumentation-langchain"
        )
        return False
    except Exception as e:
        logger.error(f"[Phoenix] Initialisation failed (non-fatal): {e}")
        return False


# ────────────────────────────────────────────────────────────────────
# Manual span context manager
# ────────────────────────────────────────────────────────────────────
@contextmanager
def phoenix_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    span_kind: str = "CHAIN",   # CHAIN | LLM | RETRIEVER | RERANKER | TOOL
) -> Iterator[Any]:
    """
    Context manager that wraps a code block in a named Phoenix / OTEL span.

    Usage:
        with phoenix_span("qdrant.retrieve", {"query": q, "limit": 5}) as span:
            results = vector_store.search(q)
            span.set_attribute("result_count", len(results))

    No-ops gracefully if Phoenix is not initialised.
    """
    global _tracer

    if _tracer is None or not _initialized:
        # Phoenix not available – run the block untraced
        yield _NoopSpan()
        return

    try:
        from opentelemetry.trace import SpanKind
        kind_map = {
            "LLM": SpanKind.CLIENT,
            "RETRIEVER": SpanKind.CLIENT,
            "CHAIN": SpanKind.INTERNAL,
            "TOOL": SpanKind.CLIENT,
            "RERANKER": SpanKind.INTERNAL,
        }
        otel_kind = kind_map.get(span_kind.upper(), SpanKind.INTERNAL)

        with _tracer.start_as_current_span(name, kind=otel_kind) as span:
            if attributes:
                for k, v in attributes.items():
                    try:
                        span.set_attribute(str(k), str(v) if not isinstance(v, (bool, int, float)) else v)
                    except Exception:
                        pass
            try:
                yield span
            except Exception as exc:
                span.record_exception(exc)
                span.set_attribute("error", True)
                raise
    except ImportError:
        yield _NoopSpan()


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────
class _NoopSpan:
    """Fallback span that silently ignores all attribute calls."""
    def set_attribute(self, *args, **kwargs): pass
    def record_exception(self, *args, **kwargs): pass


def get_phoenix_url() -> Optional[str]:
    """Return the Phoenix UI URL if running."""
    if not is_enabled():
        return None
    if _phoenix_session:
        port = int(os.getenv("PHOENIX_PORT", "6006"))
        return f"http://localhost:{port}"
    # If we are using an external collector container mapped to 6006, return localhost:6006 for the browser
    collector_endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "")
    if collector_endpoint:
        return "http://localhost:6006"
    return None


def is_enabled() -> bool:
    return _initialized
