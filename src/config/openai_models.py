"""User-selectable OpenAI chat models (validated server-side)."""

from __future__ import annotations

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
