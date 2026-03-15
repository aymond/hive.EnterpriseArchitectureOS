from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from src.graph.state import AgentState

llm = ChatOpenAI(model="gpt-4o", temperature=0)

def quality_check_agent(state: AgentState):
    """Quality Check / Governance Agent."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are the Chief Enterprise Architecture Governance Reviewer.\n"
                   "Review the consolidated capability models and the proposed vendor research.\n"
                   "Check for consistency, alignment with EA principles (like DRY, strategic alignment, no vendor lock-in), and completeness.\n"
                   "If approved, state 'APPROVED'. If rejected, provide specific 'REJECTED: <feedback>'."),
        ("user", "Domain Outputs: {domain_outputs}\nResearch: {research_results}")
    ])
    
    chain = prompt | llm
    
    response = chain.invoke({
        "domain_outputs": state.get("domain_outputs", {}),
        "research_results": state.get("research_results", [])
    })
    
    status = "APPROVED" if "APPROVED" in response.content.upper() else "REJECTED"
    
    return {
        "quality_status": status,
        "quality_feedback": response.content
    }
