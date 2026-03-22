from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from src.graph.state import AgentState
from src.agents.llm_logging import log_llm_start, log_llm_complete
from src.agents.model_util import resolve_chat_model

def quality_check_agent(state: AgentState):
    """Quality Check / Governance Agent."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are the Chief Enterprise Architecture Governance Reviewer.\n"
                   "Review the consolidated capability models and the proposed vendor research.\n"
                   "Check for consistency, alignment with EA principles (like DRY, strategic alignment, no vendor lock-in), and completeness.\n"
                   "Enforce structure rules:\n"
                   "- Every capability must be assigned to a domain.\n"
                   "- Capability parent-child relationships must not cross domains.\n"
                   "- Every process must be linked to one or more capabilities.\n"
                   "- When Canonical Capability Registry is provided, capability names must have a single owning domain "
                   "consistent with that registry; domain expert JSON must not contradict it.\n"
                   "- Process objects must use the key 'name' for the process title (not 'process_name').\n\n"
                   "You MUST respond using one of the two formats below (no other opening line):\n\n"
                   "If the work is acceptable:\n"
                   "STATUS: APPROVED\n"
                   "Optional: one short sentence summarizing what passed review.\n\n"
                   "If the work must be rejected:\n"
                   "STATUS: REJECTED\n"
                   "## Rejection reason\n"
                   "- Use bullet points. Be specific (what failed, which rule or gap).\n"
                   "## How to improve\n"
                   "- Use bullet points. Give concrete, actionable fixes (e.g. add domain X to capability Y, "
                   "link process Z to capabilities A and B, fix parent-child across domains).\n"
                   "## Suggested next steps\n"
                   "- Short checklist the user or agents can follow before re-submitting.\n\n"
                   "Do not approve and reject in the same response. The first line must be STATUS: APPROVED or STATUS: REJECTED."),
        ("user", "Request: {query}\n\n"
                 "Canonical Capability Registry (JSON):\n{capability_registry}\n\n"
                 "Domain Outputs: {domain_outputs}\n\n"
                 "Research Results: {research_results}")
    ])
    
    openai_api_key = state.get("openai_api_key")
    model_id = resolve_chat_model(state)
    llm = ChatOpenAI(
        model=model_id,
        temperature=0,
        api_key=SecretStr(openai_api_key) if openai_api_key else None
    )
    chain = prompt | llm
    
    log_llm_start("QualityCheck", model=model_id)
    response = chain.invoke({
        "query": state.get("query"),
        "capability_registry": state.get("capability_registry") or "{}",
        "domain_outputs": state.get("domain_outputs", {}),
        "research_results": state.get("research_results", [])
    })
    log_llm_complete("QualityCheck")

    raw = response.content if isinstance(response.content, str) else str(response.content)
    text = raw.strip()
    first_line = text.split("\n", 1)[0].strip().upper() if text else ""

    if first_line.startswith("STATUS:"):
        if "REJECT" in first_line:
            status = "REJECTED"
        elif "APPROV" in first_line:
            status = "APPROVED"
        else:
            status = "REJECTED"
    else:
        # Legacy responses without STATUS line
        upper = text.upper()
        if "STATUS: REJECTED" in upper:
            status = "REJECTED"
        elif "STATUS: APPROVED" in upper:
            status = "APPROVED"
        else:
            status = "APPROVED" if "APPROVED" in upper and "REJECT" not in upper else "REJECTED"

    return {
        "quality_status": status,
        "quality_feedback": raw,
    }
