"""
Domain Steward — maintains a canonical registry so each capability has exactly one owning domain
before parallel domain experts run.
"""

from __future__ import annotations

import json
import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from src.graph.state import AgentState
from src.agents.llm_logging import log_llm_start, log_llm_complete
from src.agents.model_util import resolve_chat_model

logger = logging.getLogger(__name__)


def _strip_code_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```json"):
        t = t[7:]
    elif t.startswith("```"):
        t = t[3:]
    if t.endswith("```"):
        t = t[:-3]
    return t.strip()


def domain_steward_agent(state: AgentState):
    """Builds authoritative domain + capability ownership JSON for downstream agents."""
    required = list(state.get("required_domains") or [])
    if not required:
        required = ["Enterprise", "Technology"]

    domains_json = json.dumps(required)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are the Chief EA Domain Steward. You maintain overarching EA domains and a single-owner capability map.\n"
                "The Coordinator selected these engaged domains (exact spelling — use only these strings): {domains_json}\n\n"
                "Return ONLY valid JSON (no markdown, no commentary) with this shape:\n"
                "{{\n"
                '  "domains": [ {{ "name": "<one engaged domain>", "purpose": "one line" }} ],\n'
                '  "capabilities": [\n'
                '     {{ "name": "<globally unique name>", "owning_domain": "<one engaged domain>", '
                '"parent_capability_name": null | "<must be another entry; same owning_domain>", '
                '"description": "short" }}\n'
                "  ]\n"
                "}}\n\n"
                "RULES:\n"
                "- Each capability `name` appears at most ONCE in the array. Each has exactly ONE `owning_domain`.\n"
                "- `owning_domain` must equal one of the engaged domain strings exactly.\n"
                "- If `parent_capability_name` is set, that parent MUST exist in the same array and share the same `owning_domain`.\n"
                "- Split overloaded or ambiguous capabilities so ownership is clear; avoid duplicates across domains.\n"
                "- Cover capabilities implied by the user request; stay as small as practical.\n",
            ),
            ("user", "User request:\n{query}\n"),
        ]
    )

    openai_api_key = state.get("openai_api_key")
    model_id = resolve_chat_model(state)
    llm = ChatOpenAI(
        model=model_id,
        temperature=0,
        api_key=SecretStr(openai_api_key) if openai_api_key else None,
    )
    chain = prompt | llm

    log_llm_start("DomainSteward", model=model_id)
    response = chain.invoke({"query": state["query"], "domains_json": domains_json})
    log_llm_complete("DomainSteward")

    raw = response.content if isinstance(response.content, str) else str(response.content)
    text = _strip_code_fence(raw)

    try:
        obj = json.loads(text)
        caps = obj.get("capabilities")
        doms = obj.get("domains")
        if not isinstance(caps, list):
            caps = []
        if not isinstance(doms, list):
            doms = []
        # Light normalization: drop capabilities with wrong domain or duplicate names
        seen: set[str] = set()
        cleaned: list[dict] = []
        for c in caps:
            if not isinstance(c, dict):
                continue
            name = c.get("name")
            od = c.get("owning_domain")
            if not isinstance(name, str) or not name.strip():
                continue
            if not isinstance(od, str) or od not in required:
                continue
            n = name.strip()
            if n.lower() in {x.lower() for x in seen}:
                continue
            seen.add(n)
            cleaned.append(
                {
                    "name": n,
                    "owning_domain": od.strip(),
                    "parent_capability_name": c.get("parent_capability_name"),
                    "description": (c.get("description") or "") if isinstance(c.get("description"), str) else "",
                }
            )
        obj["capabilities"] = cleaned
        obj["domains"] = doms
        return {"capability_registry": json.dumps(obj)}
    except json.JSONDecodeError as e:
        logger.warning("DomainSteward JSON parse failed: %s", e)
        return {
            "capability_registry": json.dumps(
                {
                    "domains": [],
                    "capabilities": [],
                    "steward_parse_failed": True,
                }
            )
        }
