from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from src.graph.state import AgentState

llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

def research_agent(state: AgentState):
    """Research agent to identify suitable vendors and tools."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an Enterprise Architecture Sourcing Expert.\n"
                   "Review the identified capabilities from the domain experts and find leading market products/vendors.\n"
                   "Output a structured JSON list called 'vendors' where each item contains:\n"
                   "- 'name': Vendor Name\n"
                   "- 'product': Product Name\n"
                   "- 'capabilities_covered': List of capability names this product maps to.\n"
                   "Use the search tool for live market validation."),
        ("user", "Capabilities: {domain_outputs}\nQuery: {query}")
    ])
    
    chain = prompt | llm
    
    response = chain.invoke({
        "query": state["query"],
        "domain_outputs": state.get("domain_outputs", {})
    })
    
    # Store dummy or real LLM research results
    current_results = state.get("research_results", [])
    current_results.append({"sourcing_recommendations": response.content})
    
    return {"research_results": current_results}
