"""LLM backend selection: OpenAI cloud vs OpenAI-compatible servers (Ollama, vLLM, LM Studio, …)."""

from __future__ import annotations

import logging
import os
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)

LLM_PROVIDER_OPENAI = "openai"
LLM_PROVIDER_OPENAI_COMPATIBLE = "openai_compatible"

ALLOWED_LLM_PROVIDERS: tuple[str, ...] = (LLM_PROVIDER_OPENAI, LLM_PROVIDER_OPENAI_COMPATIBLE)

DEFAULT_COMPAT_LLM_MODEL = os.getenv("DEFAULT_COMPAT_LLM_MODEL", "llama3.2")

# Ollama’s OpenAI-compatible API is under /v1 (e.g. …/v1/chat/completions). “/” on :11434 is only the status page.
EXAMPLE_COMPATIBLE_BASE_URL = "http://localhost:11434/v1"
# When the Python API runs in Docker, localhost is the container — use the host gateway instead.
EXAMPLE_COMPATIBLE_BASE_URL_DOCKER = "http://host.docker.internal:11434/v1"


def normalize_llm_provider(value: str | None) -> str:
    if not value or not isinstance(value, str):
        return LLM_PROVIDER_OPENAI
    v = value.strip().lower().replace("-", "_")
    if v in ("openai", "openai_cloud", "cloud"):
        return LLM_PROVIDER_OPENAI
    if v in ("openai_compatible", "compatible", "ollama", "local"):
        return LLM_PROVIDER_OPENAI_COMPATIBLE
    return LLM_PROVIDER_OPENAI


def validate_openai_compatible_base_url(url: str) -> str:
    """Return trimmed base URL or raise ValueError."""
    u = url.strip()
    if not u:
        raise ValueError("Base URL is required for OpenAI-compatible mode.")
    parsed = urlparse(u)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Base URL must start with http:// or https://")
    if not parsed.netloc:
        raise ValueError("Base URL must include a host.")
    # OpenAI SDK posts to {base_url}/chat/completions — same layout as api.openai.com/v1.
    path = (parsed.path or "").rstrip("/")
    if path in ("", "/"):
        u = f"{parsed.scheme}://{parsed.netloc}/v1"
    elif not path.endswith("/v1"):
        u = u.rstrip("/") + "/v1"
    return u.rstrip("/")


def sanitize_optional_base_url(url: str | None) -> str | None:
    if not url or not isinstance(url, str) or not url.strip():
        return None
    return validate_openai_compatible_base_url(url)


def running_in_docker() -> bool:
    """True when this process is inside a container (e.g. Compose app service)."""
    return os.path.exists("/.dockerenv")


def rewrite_loopback_host_for_docker(url: str) -> str:
    """
    Inside Docker, localhost/127.0.0.1 refers to the container, not the host where Ollama runs.
    Rewrite to host.docker.internal (override with OPENAI_COMPATIBLE_DOCKER_HOST).
    Set DISABLE_LLM_DOCKER_HOST_REWRITE=1 to skip.
    """
    if os.getenv("DISABLE_LLM_DOCKER_HOST_REWRITE", "").strip().lower() in ("1", "true", "yes"):
        return url
    if not running_in_docker():
        return url
    p = urlparse(url)
    host = (p.hostname or "").lower()
    if host not in ("localhost", "127.0.0.1"):
        return url
    docker_host = (os.getenv("OPENAI_COMPATIBLE_DOCKER_HOST") or "host.docker.internal").strip()
    port = p.port
    if port:
        new_netloc = f"{docker_host}:{port}"
    else:
        new_netloc = docker_host
    out = urlunparse((p.scheme, new_netloc, p.path, p.params, p.query, p.fragment))
    logger.debug("LLM base URL inside Docker: rewrote %s -> %s", url, out)
    return out


def resolve_openai_compatible_base_url_for_client(url: str) -> str:
    """Validate, normalize /v1, then rewrite loopback host when running in Docker."""
    return rewrite_loopback_host_for_docker(validate_openai_compatible_base_url(url))
