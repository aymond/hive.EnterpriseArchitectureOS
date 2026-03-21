import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from src.graph.state import AgentState

llm = ChatOpenAI(model="gpt-4o", temperature=0)

def coordinator_agent(state: AgentState):
    """Chief EA Coordinator - Analyzes the user request and determines which domains to engage."""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are the Chief Enterprise Architect Coordinator.\n"
                   "Analyze the user's request and determine which EA domains need to participate in modeling this capability.\n"
                   "The available domains are: 'Strategy', 'Enterprise', 'Technology', 'Security', 'Data', 'Compliance'.\n"
                   "Return your response ONLY as a JSON array of strings containing the required domain names.\n"
                   "Example: [\"Strategy\", \"Enterprise\", \"Technology\"]"),
        ("user", "Request: {query}")
    ])
    
    chain = prompt | llm
    
    response = chain.invoke({"query": state["query"]})
    
    try:
        # Parse the JSON array from the response
        required_domains = json.loads(response.content)
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
                   "Output Markdown formatted text."),
        ("user", "Initial Request: {query}\n"
                 "Domain Outputs: {domain_outputs}\n"
                 "Research Results: {research_results}\n"
                 "Quality Status: {quality_status}\n"
                 "Quality Feedback: {quality_feedback}")
    ])
    
    chain = prompt | llm
    
    response = chain.invoke({
        "query": state["query"],
        "domain_outputs": state.get("domain_outputs", {}),
        "research_results": state.get("research_results", []),
        "quality_status": state.get("quality_status", "UNKNOWN"),
        "quality_feedback": state.get("quality_feedback", "None provided.")
    })
    
    return {"final_response": response.content}
