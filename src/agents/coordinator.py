import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from src.graph.state import AgentState

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
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        api_key=SecretStr(openai_api_key) if openai_api_key else None
    )
    chain = prompt | llm
    
    response = chain.invoke({"query": state["query"]})
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
                   "4) ## Application & Technology Landscape\n"
                   "5) ## Governance, Risk, and Compliance\n"
                   "6) ## Recommendations\n"
                   "For every H2 section, use concise bullet points and keep list formatting consistent across all sections.\n"
                   "The Recommendations section must use the same bullet style as the other H2 sections.\n"
                   "Output Markdown formatted text."),
        ("user", "Initial Request: {query}\n"
                 "Domain Outputs: {domain_outputs}\n"
                 "Research Results: {research_results}\n"
                 "Quality Status: {quality_status}\n"
                 "Quality Feedback: {quality_feedback}")
    ])
    
    openai_api_key = state.get("openai_api_key")
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        api_key=SecretStr(openai_api_key) if openai_api_key else None
    )
    chain = prompt | llm
    
    response = chain.invoke({
        "query": state["query"],
        "domain_outputs": state.get("domain_outputs", {}),
        "research_results": state.get("research_results", []),
        "quality_status": state.get("quality_status", "UNKNOWN"),
        "quality_feedback": state.get("quality_feedback", "None provided.")
    })
    
    return {"final_response": response.content}
