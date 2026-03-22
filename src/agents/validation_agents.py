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


def quality_check_agent(state: AgentState):
    """Soft governance review: never blocks publication; surfaces user notice + admin log."""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are the Chief Enterprise Architecture Governance Reviewer.\n"
                "Outputs have already passed an automated remediation step. Your job is to ASSESS, not to block delivery.\n\n"
                "You MUST NEVER use STATUS: REJECTED or tell the user to manually fix domain/capability/process relationships.\n"
                "Return ONLY valid JSON (no markdown, no prose outside JSON) with exactly these keys:\n"
                '{{\n'
                '  "status": "APPROVED" | "APPROVED_WITH_WARNINGS",\n'
                '  "user_summary": "<1–3 short sentences, plain language, reassuring; no instructions to edit the graph>",\n'
                '  "admin_log": "<technical notes for operators: residual risks, assumptions, anything an admin should monitor>"\n'
                "}}\n\n"
                "Use APPROVED when alignment with the registry and process rules looks good after remediation.\n"
                "Use APPROVED_WITH_WARNINGS when minor residual ambiguity remains — still ship the report.\n"
                "user_summary must not ask the user to assign domains, relink processes, or re-run with fixes.\n"
                "admin_log may include concrete technical detail for logs and administrators only.\n",
            ),
            (
                "user",
                "Request: {query}\n\n"
                "Canonical Capability Registry (JSON):\n{capability_registry}\n\n"
                "Domain Outputs (post-remediation):\n{domain_outputs}\n\n"
                "Research Results:\n{research_results}\n",
            ),
        ]
    )

    model_id = resolve_chat_model(state)
    llm = get_chat_llm(state, temperature=0)
    chain = prompt | llm

    log_llm_start("QualityCheck", model=model_id)
    response = chain.invoke(
        {
            "query": state.get("query"),
            "capability_registry": state.get("capability_registry") or "{}",
            "domain_outputs": state.get("domain_outputs", {}),
            "research_results": state.get("research_results", []),
        }
    )
    log_llm_complete("QualityCheck")

    raw = response.content if isinstance(response.content, str) else str(response.content)
    text = _strip_code_fence(raw)

    user_summary = "Governance review completed."
    admin_log = text[:8000] if text else ""
    status = "APPROVED_WITH_WARNINGS"

    try:
        obj = json.loads(text)
        st = obj.get("status", "")
        if st == "APPROVED":
            status = "APPROVED"
        elif st == "APPROVED_WITH_WARNINGS":
            status = "APPROVED_WITH_WARNINGS"
        else:
            status = "APPROVED_WITH_WARNINGS"
        if isinstance(obj.get("user_summary"), str) and obj["user_summary"].strip():
            user_summary = obj["user_summary"].strip()
        if isinstance(obj.get("admin_log"), str) and obj["admin_log"].strip():
            admin_log = obj["admin_log"].strip()
    except json.JSONDecodeError:
        # Legacy markdown / free text — treat as warning, keep report flowing
        upper = raw.upper()
        if "REJECT" in upper or "REJECTED" in upper:
            status = "APPROVED_WITH_WARNINGS"
            user_summary = (
                "A governance pass noted some modeling nuances; your report is still provided below. "
                "Our team reviews technical details in system logs."
            )
        elif "APPROVED" in upper and "WARN" not in upper:
            status = "APPROVED"
            user_summary = "Governance review completed with no material warnings."
        admin_log = f"(Unparsed reviewer output)\n{raw[:8000]}"

    logger.info("Governance review (admin_log):\n%s", admin_log[:16000])

    return {
        "quality_status": status,
        "quality_feedback": user_summary,
        "governance_admin_log": admin_log,
    }
