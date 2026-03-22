from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_tavily import TavilySearch
from pydantic import SecretStr
from src.graph.state import AgentState
from src.agents.llm_logging import log_llm_start, log_llm_complete
from src.agents.model_util import resolve_chat_model

def research_agent(state: AgentState):
    """Research agent to identify suitable vendors and tools."""
    system_message = (
        "You are an Enterprise Architecture Sourcing Expert.\n"
        "Use the Canonical Capability Registry and domain expert outputs to ground vendor mapping.\n"
        "When a web search tool is available, call it to validate current product names and positioning; "
        "then synthesize findings into structured vendor recommendations.\n\n"
        "Your FINAL message must be ONLY valid JSON (no markdown fences, no prose outside JSON) with this exact shape:\n"
        '{"vendors": [{"name": "<vendor>", "product": "<product>", "capabilities_covered": ["<capability name>"]}]}\n'
        "Use the keys exactly: name, product, capabilities_covered. Do not use vendor_name, product_name, or process_name.\n"
        "Map capabilities_covered to names from the registry or domain outputs when possible."
    )
    registry = state.get("capability_registry") or "{}"
    user_message = (
        f"Canonical Capability Registry (JSON):\n{registry}\n\n"
        f"Domain expert outputs (by domain):\n{state.get('domain_outputs', {})}\n\n"
        f"User query:\n{state['query']}"
    )
    
    openai_api_key = state.get("openai_api_key")
    model_id = resolve_chat_model(state)
    llm = ChatOpenAI(
        model=model_id,
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
        log_llm_start("Research", model=model_id, tavily_enabled=tavily_enabled, mode="react_agent")
        response = agent_executor.invoke({"messages": [("user", user_message_with_system)]})
        log_llm_complete("Research", mode="react_agent", tavily_enabled=tavily_enabled)
        response_content = response["messages"][-1].content
        content = response_content if isinstance(response_content, str) else str(response_content)
    else:
        # Fallback if no Tavily key is provided
        fallback_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an Enterprise Architecture Sourcing Expert.\n"
                       "No search tool is available — use internal knowledge only.\n"
                       "Your response must be ONLY valid JSON (no markdown) with shape:\n"
                       '{{"vendors": [{{"name": "<vendor>", "product": "<product>", "capabilities_covered": ["..."]}}]}}\n'
                       "Use keys: name, product, capabilities_covered only."),
            ("user", "Canonical registry:\n{capability_registry}\n\n"
                     "Domain outputs:\n{domain_outputs}\n\nQuery:\n{query}")
        ])
        chain = fallback_prompt | llm
        log_llm_start("Research", model=model_id, tavily_enabled=tavily_enabled, mode="fallback_chain")
        response = chain.invoke({
            "query": state["query"],
            "capability_registry": state.get("capability_registry") or "{}",
            "domain_outputs": state.get("domain_outputs", {}),
        })
        log_llm_complete("Research", mode="fallback_chain", tavily_enabled=tavily_enabled)
        content = response.content if isinstance(response.content, str) else str(response.content)
    
    # Store actual LLM research results
    current_results = state.get("research_results", [])
    current_results.append({"sourcing_recommendations": content})
    
    return {"research_results": current_results}
