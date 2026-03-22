from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_tavily import TavilySearch
from pydantic import SecretStr
from src.graph.state import AgentState
from src.agents.llm_logging import log_llm_start, log_llm_complete

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
    
    openai_api_key = state.get("openai_api_key")
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.2,
        api_key=SecretStr(openai_api_key) if openai_api_key else None
    )
    
    tools = []
    tavily_key = state.get("tavily_api_key")
    if tavily_key:
        tools.append(TavilySearch(max_results=3, api_key=tavily_key))

    tavily_enabled = bool(tools)

    if tools:
        agent_executor = create_react_agent(llm, tools)
        user_message_with_system = f"{system_message}\n\n{user_message}"
        log_llm_start("Research", model="gpt-4o", tavily_enabled=tavily_enabled, mode="react_agent")
        response = agent_executor.invoke({"messages": [("user", user_message_with_system)]})
        log_llm_complete("Research", mode="react_agent", tavily_enabled=tavily_enabled)
        response_content = response["messages"][-1].content
        content = response_content if isinstance(response_content, str) else str(response_content)
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
        log_llm_start("Research", model="gpt-4o", tavily_enabled=tavily_enabled, mode="fallback_chain")
        response = chain.invoke({
            "query": state["query"],
            "domain_outputs": state.get("domain_outputs", {})
        })
        log_llm_complete("Research", mode="fallback_chain", tavily_enabled=tavily_enabled)
        content = response.content if isinstance(response.content, str) else str(response.content)
    
    # Store actual LLM research results
    current_results = state.get("research_results", [])
    current_results.append({"sourcing_recommendations": content})
    
    return {"research_results": current_results}
