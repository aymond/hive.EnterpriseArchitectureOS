"""Centralized logging for LLM-bound graph nodes (OpenAI / tool-using agents)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def log_llm_start(node: str, **kwargs: Any) -> None:
    """Log immediately before a node triggers an LLM chain or agent invoke."""
    if kwargs:
        parts = [f"{k}={v!r}" for k, v in kwargs.items()]
        logger.info("LLM request: node=%s (%s)", node, ", ".join(parts))
    else:
        logger.info("LLM request: node=%s", node)


def log_llm_complete(node: str, **kwargs: Any) -> None:
    """Optional post-invoke breadcrumb (e.g. mode, outcome)."""
    if kwargs:
        parts = [f"{k}={v!r}" for k, v in kwargs.items()]
        logger.info("LLM complete: node=%s (%s)", node, ", ".join(parts))
    else:
        logger.info("LLM complete: node=%s", node)
