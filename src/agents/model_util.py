"""Resolve LLM model id from graph state."""

from __future__ import annotations

from typing import Any, Mapping

from src.config.openai_models import normalize_llm_model


def resolve_chat_model(state: Mapping[str, Any]) -> str:
    return normalize_llm_model(state.get("llm_model"))
