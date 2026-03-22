"""User-selectable OpenAI chat models (validated server-side for OpenAI cloud)."""

from __future__ import annotations

from src.config.llm_providers import DEFAULT_COMPAT_LLM_MODEL, LLM_PROVIDER_OPENAI_COMPATIBLE

DEFAULT_LLM_MODEL = "gpt-4o"

ALLOWED_LLM_MODELS: list[str] = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4-turbo-preview",
    "gpt-3.5-turbo",
]


def normalize_llm_model(model: str | None) -> str:
    if not model or not isinstance(model, str):
        return DEFAULT_LLM_MODEL
    cleaned = model.strip()
    return cleaned if cleaned in ALLOWED_LLM_MODELS else DEFAULT_LLM_MODEL


def normalize_llm_model_for_provider(provider: str, model: str | None) -> str:
    """OpenAI cloud: allowlist. OpenAI-compatible: any non-empty model id (Ollama tag, etc.)."""
    if provider == LLM_PROVIDER_OPENAI_COMPATIBLE:
        if not model or not isinstance(model, str) or not model.strip():
            return DEFAULT_COMPAT_LLM_MODEL
        cleaned = model.strip()
        if len(cleaned) > 200:
            cleaned = cleaned[:200]
        return cleaned
    return normalize_llm_model(model)
