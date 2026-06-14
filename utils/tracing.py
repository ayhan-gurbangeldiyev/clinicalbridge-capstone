"""LangFuse observability integration.

Provides a single LangChain callback handler that traces every agent call
(prompt, output, latency, token usage, errors) into LangFuse. The handler is
attached once at the LangGraph ``ainvoke`` call and LangGraph propagates it to
all underlying ``prompt | llm | parser`` chains automatically.

Graceful degradation: if the ``LANGFUSE_*`` environment variables are not set,
``get_langfuse_handler`` returns ``None`` and the system runs untraced without
errors. This keeps the project runnable for anyone without LangFuse keys.
"""

import os

# Cache one LangFuse client + handler per process. Re-creating them on every
# orchestrator run can drop queued spans in short-lived scripts (only the last
# client flushes at exit); a single shared client + explicit flush is reliable.
_client = None
_handler = None


def langfuse_configured() -> bool:
    """True only when both LangFuse API keys look like real credentials.

    Real LangFuse keys are prefixed ``pk-lf-`` / ``sk-lf-``. This guards against
    the ``.env.example`` placeholders (``your_..._here``) being mistaken for
    configured keys, which would otherwise produce 401 errors on trace export.
    """
    pub = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    sec = os.environ.get("LANGFUSE_SECRET_KEY", "")
    return pub.startswith("pk-lf-") and sec.startswith("sk-lf-")


def get_langfuse_handler():
    """Return a LangFuse LangChain callback handler, or None if not configured.

    Supports both LangFuse v3 (``langfuse.langchain``, where the handler reads
    credentials from an initialized ``Langfuse`` client) and the legacy v2 API
    (``langfuse.callback``, where keys are passed to the constructor).

    Returns None (rather than raising) when keys are missing or the langfuse
    package is unavailable, so callers can pass the result straight into a
    ``callbacks`` list without branching. The handler is created once and reused.
    """
    global _client, _handler
    if not langfuse_configured():
        return None
    if _handler is not None:
        return _handler

    public_key = os.environ["LANGFUSE_PUBLIC_KEY"]
    secret_key = os.environ["LANGFUSE_SECRET_KEY"]
    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")

    # LangFuse v3: initialize one client, then create a parameter-less handler.
    try:
        from langfuse import Langfuse
        from langfuse.langchain import CallbackHandler

        _client = Langfuse(public_key=public_key, secret_key=secret_key, host=host)
        _handler = CallbackHandler()
        return _handler
    except ImportError:
        pass

    # LangFuse v2 fallback.
    try:
        from langfuse.callback import CallbackHandler as CallbackHandlerV2

        _handler = CallbackHandlerV2(public_key=public_key, secret_key=secret_key, host=host)
        _client = _handler
        return _handler
    except ImportError:
        return None


def flush_langfuse() -> None:
    """Flush any queued traces to LangFuse. Call at the end of short-lived scripts so
    spans are delivered before the process exits."""
    if _client is not None and hasattr(_client, "flush"):
        try:
            _client.flush()
        except Exception:
            pass
