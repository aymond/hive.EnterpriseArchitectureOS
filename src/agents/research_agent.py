from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_community.tools.tavily_search import TavilySearchResults
from src.graph.state import AgentState

def research_agent(state: AgentState):
    """Research agent to identify suitable vendors and tools."""
    system_message = (
        "You are an Enterprise Architecture Sourcing Expert.\n"
        "Review the identified capabilities from the domain experts and find leading market products/vendors.\n"
        "Output a structured JSON list called 'vendors' where each item contains:\n"
        "- 'name': Vendor Name\n"
        "- 'product': Product Name\n"
        "- 'capabilities_covered': List of capability names this product maps to.\n"
        "Use the search tool for live market validation."
    )
    user_message = f"Capabilities: {state.get('domain_outputs', {})}\nQuery: {state['query']}"
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2, api_key=state.get("openai_api_key"))
    
    tools = []
    tavily_key = state.get("tavily_api_key")
    if tavily_key:
        tools.append(TavilySearchResults(max_results=3, api_key=tavily_key))
        
    if tools:
        agent_executor = create_react_agent(llm, tools)
        user_message_with_system = f"{system_message}\n\n{user_message}"
        response = agent_executor.invoke({"messages": [("user", user_message_with_system)]})
        content = response["messages"][-1].content
    else:
        # Fallback if no Tavily key is provided
        fallback_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an Enterprise Architecture Sourcing Expert.\n"
                       "Review the identified capabilities from the domain experts and find leading market products/vendors.\n"
                       "Output a structured JSON list called 'vendors' where each item contains:\n"
                       "- 'name': Vendor Name\n"
                       "- 'product': Product Name\n"
                       "- 'capabilities_covered': List of capability names this product maps to.\n"
                       "Note: No search tool is available. Rely on your internal knowledge."),
            ("user", "Capabilities: {domain_outputs}\nQuery: {query}")
        ])
        chain = fallback_prompt | llm
        response = chain.invoke({
            "query": state["query"],
            "domain_outputs": state.get("domain_outputs", {})
        })
        content = response.content
    
    # Store actual LLM research results
    current_results = state.get("research_results", [])
    current_results.append({"sourcing_recommendations": content})
    
    return {"research_results": current_results}
