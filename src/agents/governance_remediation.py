"""
Governance Remediation — proactively fixes domain outputs (single owner per capability,
process links, naming) before soft quality review. Technical details go to logs only.
"""

from __future__ import annotations

import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from src.graph.state import AgentState
from src.agents.llm_factory import get_chat_llm
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


def governance_remediation_agent(state: AgentState):
    """Rewrite domain_outputs to satisfy registry and process rules without user action."""
    domain_outputs = dict(state.get("domain_outputs") or {})
    if not domain_outputs:
        return {}

    bundle = json.dumps(domain_outputs, default=str, ensure_ascii=False)
    registry = state.get("capability_registry") or "{}"

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are the EA Governance Remediation Agent. You fix modeling outputs before review.\n"
                "You MUST proactively resolve inconsistencies — never defer fixes to the end user.\n\n"
                "Rules:\n"
                "1) Use the Canonical Capability Registry: each capability name has exactly one owning_domain. "
                "That capability must appear in the 'capabilities' array of at most ONE domain expert JSON output. "
                "Remove duplicates from other domains' capabilities arrays. If a domain had a legitimate local nuance, "
                "express it in 'recommendations' text only, not as a second owned capability with the same name.\n"
                "2) When choosing which domain keeps a disputed capability, prefer the registry owning_domain. "
                "State your choice and brief rationale in admin_remediation_log only.\n"
                "3) Every process must have key 'name' (not process_name) and a non-empty 'related_capability_names' "
                "array referencing real capability names from the registry or the owning domain output.\n"
                "4) If a process lacked links, infer the best capability from context and the registry.\n"
                "5) Preserve valid JSON inside each domain string; each value is the full corrected document that domain would have emitted.\n\n"
                "Return ONLY valid JSON (no markdown fences):\n"
                "{{\n"
                '  "domain_outputs": {{ "<DomainName>": "<string: full corrected JSON text>", ... }},\n'
                '  "admin_remediation_log": "<technical multi-line: changes and assumptions for operators>"\n'
                "}}\n"
                "You MUST include every domain key from the input domain_outputs.",
            ),
            (
                "user",
                "Canonical Capability Registry (JSON):\n{registry}\n\n"
                "Current domain_outputs (JSON object of domain -> string):\n{bundle}\n\n"
                "User request:\n{query}\n",
            ),
        ]
    )

    model_id = resolve_chat_model(state)
    llm = get_chat_llm(state, temperature=0)
    chain = prompt | llm

    log_llm_start("GovernanceRemediation", model=model_id)
    response = chain.invoke(
        {"registry": registry, "bundle": bundle, "query": state.get("query", "")}
    )
    log_llm_complete("GovernanceRemediation")

    raw = response.content if isinstance(response.content, str) else str(response.content)
    text = _strip_code_fence(raw)

    try:
        obj = json.loads(text)
        new_outputs = obj.get("domain_outputs")
        admin = obj.get("admin_remediation_log", "")
        if isinstance(admin, str) and admin.strip():
            logger.info("GovernanceRemediation admin_remediation_log:\n%s", admin.strip()[:16000])

        if not isinstance(new_outputs, dict) or not new_outputs:
            logger.warning("GovernanceRemediation returned empty domain_outputs; keeping originals.")
            return {}

        parsed: dict[str, str] = {}
        for k, v in new_outputs.items():
            if k not in domain_outputs:
                continue
            parsed[str(k)] = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)

        merged: dict[str, str] = {}
        for k, v in domain_outputs.items():
            merged[k] = parsed[k] if k in parsed else (v if isinstance(v, str) else json.dumps(v, default=str))
        return {"domain_outputs": merged}
    except json.JSONDecodeError as e:
        logger.warning("GovernanceRemediation JSON parse failed: %s", e)
        return {}
