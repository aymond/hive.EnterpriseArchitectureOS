import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from src.graph.state import AgentState
from src.agents.llm_logging import log_llm_start, log_llm_complete
from src.agents.model_util import resolve_chat_model

def coordinator_agent(state: AgentState):
    """Chief EA Coordinator - Analyzes the user request and determines which domains to engage."""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are the Chief Enterprise Architect Coordinator.\n"
                   "Analyze the user's request and determine which EA domains need to participate in modeling this capability.\n"
                   "The available domains are: 'Strategy', 'Enterprise', 'Technology', 'Security', 'Data', 'Compliance', 'Process'.\n"
                   "Return your response ONLY as a JSON array of strings containing the required domain names.\n"
                   "Example: [\"Strategy\", \"Enterprise\", \"Technology\"]"),
        ("user", "Request: {query}")
    ])
    
    openai_api_key = state.get("openai_api_key")
    model_id = resolve_chat_model(state)
    llm = ChatOpenAI(
        model=model_id,
        temperature=0,
        api_key=SecretStr(openai_api_key) if openai_api_key else None
    )
    chain = prompt | llm
    
    log_llm_start("Coordinator", model=model_id)
    response = chain.invoke({"query": state["query"]})
    log_llm_complete("Coordinator")
    response_content = response.content if isinstance(response.content, str) else "[]"
    
    try:
        # Parse the JSON array from the response
        required_domains = json.loads(response_content)
        if not isinstance(required_domains, list):
            required_domains = ["Enterprise", "Technology"] # Fallback
    except json.JSONDecodeError:
        # Fallback if the LLM didn't return pure JSON
        required_domains = ["Enterprise", "Technology"]
        
    return {"required_domains": required_domains}

def synthesis_agent(state: AgentState):
    """Synthesizes the final EA response from all gathered domain outputs and research."""
    openai_api_key = state.get("openai_api_key")
    model_id = resolve_chat_model(state)
    llm = ChatOpenAI(
        model=model_id,
        temperature=0,
        api_key=SecretStr(openai_api_key) if openai_api_key else None
    )

    quality_status = state.get("quality_status", "UNKNOWN")
    if quality_status == "REJECTED":
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are the Chief Enterprise Architect communicating a governance outcome to stakeholders.\n"
                       "The quality review REJECTED this run. Do NOT present a full approved architecture proposal.\n"
                       "Produce clear Markdown for the user with this exact structure:\n"
                       "1) # Governance outcome: Rejected\n"
                       "2) ## Summary — Briefly state that the proposal did not pass governance and reference the original request.\n"
                       "3) ## Why it was rejected — Use bullet points. Base this ONLY on 'Governance review details' below; "
                       "if a section is missing there, say so and quote what is available.\n"
                       "4) ## How to improve — Use bullet points. Concrete, actionable changes (data model, process links, domains, etc.).\n"
                       "5) ## Suggested next steps — Short checklist before re-running the analysis.\n"
                       "Use professional tone. Do not invent violations not stated in the governance details."),
            ("user", "Original request: {query}\n\n"
                     "Canonical Capability Registry:\n{capability_registry}\n\n"
                     "Governance review details (verbatim from reviewer):\n{quality_feedback}\n\n"
                     "Optional context — Domain outputs (for your awareness only; do not override the reviewer):\n{domain_outputs}\n\n"
                     "Optional context — Research results:\n{research_results}")
        ])
        chain = prompt | llm
        log_llm_start("Synthesizer", model=model_id, mode="governance_rejected")
        response = chain.invoke({
            "query": state["query"],
            "capability_registry": state.get("capability_registry") or "{}",
            "domain_outputs": state.get("domain_outputs", {}),
            "research_results": state.get("research_results", []),
            "quality_feedback": state.get("quality_feedback", "No details provided."),
        })
        log_llm_complete("Synthesizer", mode="governance_rejected")
        out = response.content if isinstance(response.content, str) else str(response.content)
        return {"final_response": out}

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are the Chief Enterprise Architect.\n"
                   "Synthesize the consolidated findings from the domain experts and the vendor research into a final cohesive Enterprise Architecture proposal.\n"
                   "FOLLOW THESE TECHNICAL WRITING GUIDELINES (inspired by Google Developer Documentation Style Guide):\n"
                   "- Use active voice and clear, concise language.\n"
                   "- Use a clear hierarchy with consistent header levels (H1 for title, H2 for major sections).\n"
                   "- Use bullet points for unordered lists and numbered lists for sequential steps.\n"
                   "- Bold UI elements or key terms for emphasis.\n"
                   "- Maintain a professional, objective tone.\n"
                   "- Ensure consistent terminology across all sections.\n"
                   "FORMAT THE OUTPUT USING THIS EXACT SECTION STRUCTURE AND ORDER:\n"
                   "1) # Enterprise Architecture Proposal\n"
                   "2) ## Executive Summary\n"
                   "3) ## Capability Model\n"
                   "4) ## Process Model\n"
                   "5) ## Application & Technology Landscape\n"
                   "6) ## Governance, Risk, and Compliance\n"
                   "7) ## Recommendations\n"
                   "For every H2 section, use concise bullet points and keep list formatting consistent across all sections.\n"
                   "The Recommendations section must use the same bullet style as the other H2 sections.\n"
                   "In ## Process Model, explicitly list processes and their mapped capabilities.\n"
                   "Output Markdown formatted text."),
        ("user", "Initial Request: {query}\n"
                 "Canonical Capability Registry:\n{capability_registry}\n\n"
                 "Domain Outputs: {domain_outputs}\n"
                 "Research Results: {research_results}\n"
                 "Quality Status: {quality_status}\n"
                 "Quality Feedback: {quality_feedback}")
    ])
    chain = prompt | llm

    log_llm_start("Synthesizer", model=model_id, mode="full_proposal")
    response = chain.invoke({
        "query": state["query"],
        "capability_registry": state.get("capability_registry") or "{}",
        "domain_outputs": state.get("domain_outputs", {}),
        "research_results": state.get("research_results", []),
        "quality_status": quality_status,
        "quality_feedback": state.get("quality_feedback", "None provided.")
    })
    log_llm_complete("Synthesizer", mode="full_proposal")

    out = response.content if isinstance(response.content, str) else str(response.content)
    return {"final_response": out}
