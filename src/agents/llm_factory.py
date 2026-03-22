"""Build LangChain ChatOpenAI from AgentState (OpenAI cloud or OpenAI-compatible base URL)."""

from __future__ import annotations

from typing import Any, Mapping

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from src.config.llm_providers import (
    LLM_PROVIDER_OPENAI_COMPATIBLE,
    normalize_llm_provider,
    resolve_openai_compatible_base_url_for_client,
)


def get_chat_llm(state: Mapping[str, Any], **kwargs: Any) -> ChatOpenAI:
    """
    ChatOpenAI with optional base_url for local/vLLM/Ollama OpenAI-compatible APIs.
    Pass through temperature, max_tokens, etc. as kwargs.
    """
    provider = normalize_llm_provider(state.get("llm_provider"))
    model_id = state.get("llm_model") or "gpt-4o"
    api_key_raw = state.get("openai_api_key") or ""

    if provider == LLM_PROVIDER_OPENAI_COMPATIBLE:
        raw_base = (state.get("openai_base_url") or "").strip()
        if not raw_base:
            raise ValueError("openai_base_url is required when llm_provider is openai_compatible")
        base_url = resolve_openai_compatible_base_url_for_client(raw_base)
        key = api_key_raw.strip() if api_key_raw.strip() else "ollama"
        return ChatOpenAI(
            model=model_id,
            api_key=SecretStr(key),
            base_url=base_url,
            **kwargs,
        )

    key = api_key_raw.strip()
    if not key:
        raise ValueError("openai_api_key is required when llm_provider is openai")
    return ChatOpenAI(model=model_id, api_key=SecretStr(key), **kwargs)
