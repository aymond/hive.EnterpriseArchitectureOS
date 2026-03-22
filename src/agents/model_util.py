"""Resolve LLM model id from graph state."""

from __future__ import annotations

from typing import Any, Mapping

from src.config.llm_providers import normalize_llm_provider
from src.config.openai_models import normalize_llm_model_for_provider


def resolve_chat_model(state: Mapping[str, Any]) -> str:
    p = normalize_llm_provider(state.get("llm_provider"))
    return normalize_llm_model_for_provider(p, state.get("llm_model"))
