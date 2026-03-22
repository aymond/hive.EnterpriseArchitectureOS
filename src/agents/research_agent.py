import json

from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent
from langchain_tavily import TavilySearch
from src.graph.state import AgentState
from src.agents.llm_factory import get_chat_llm
from src.agents.llm_logging import log_llm_start, log_llm_complete
from src.agents.model_util import resolve_chat_model
from src.db.neo4j import neo4j_client
from src.config.llm_providers import LLM_PROVIDER_OPENAI_COMPATIBLE, normalize_llm_provider
from src.db.vendor_canonical import (
    capability_names_from_registry_json,
    vendor_naming_hint_for_prompts,
)

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
        "Map capabilities_covered to names from the registry or domain outputs when possible.\n"
        + vendor_naming_hint_for_prompts()
    )
    registry = state.get("capability_registry") or "{}"
    user_message = (
        f"Canonical Capability Registry (JSON):\n{registry}\n\n"
        f"Domain expert outputs (by domain):\n{state.get('domain_outputs', {})}\n\n"
    )
    tenant_id = state.get("tenant_id")
    cap_names = capability_names_from_registry_json(registry)
    if tenant_id and cap_names:
        try:
            vrows = neo4j_client.get_vendor_capability_context(tenant_id, cap_names)
            if vrows:
                user_message += (
                    "Existing Vendor→Product→Capability links in the knowledge graph for registry capabilities "
                    "(prefer these vendor names when the same company applies):\n"
                    + json.dumps(vrows, indent=2)
                    + "\n\n"
                )
        except Exception:
            pass
    user_message += f"User query:\n{state['query']}"
    
    model_id = resolve_chat_model(state)
    llm = get_chat_llm(state, temperature=0.2)
    
    tools = []
    tavily_key = state.get("tavily_api_key")
    if tavily_key:
        tools.append(TavilySearch(max_results=3, api_key=tavily_key))

    tavily_enabled = bool(tools)
    # Ollama (and many OpenAI-compatible servers) reject ReAct/tool-calling payloads; use plain chat only.
    use_react_agent = bool(tools) and normalize_llm_provider(state.get("llm_provider")) != LLM_PROVIDER_OPENAI_COMPATIBLE

    if use_react_agent:
        agent_executor = create_react_agent(llm, tools)
        user_message_with_system = f"{system_message}\n\n{user_message}"
        log_llm_start("Research", model=model_id, tavily_enabled=tavily_enabled, mode="react_agent")
        response = agent_executor.invoke({"messages": [("user", user_message_with_system)]})
        log_llm_complete("Research", mode="react_agent", tavily_enabled=tavily_enabled)
        response_content = response["messages"][-1].content
        content = response_content if isinstance(response_content, str) else str(response_content)
    else:
        # No Tavily key, or OpenAI-compatible LLM (no tool-calling / ReAct with Tavily).
        fallback_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an Enterprise Architecture Sourcing Expert.\n"
                       "No search tool is available — use internal knowledge only.\n"
                       + vendor_naming_hint_for_prompts()
                       + "\nYour response must be ONLY valid JSON (no markdown) with shape:\n"
                       '{{"vendors": [{{"name": "<vendor>", "product": "<product>", "capabilities_covered": ["..."]}}]}}\n'
                       "Use keys: name, product, capabilities_covered only."),
            ("user", "Canonical registry:\n{capability_registry}\n\n"
                     "Domain outputs:\n{domain_outputs}\n\n"
                     "{vendor_graph}\n\n"
                     "Query:\n{query}")
        ])
        chain = fallback_prompt | llm
        log_llm_start(
            "Research",
            model=model_id,
            tavily_enabled=False,
            mode="fallback_chain",
            openai_compatible_skip_tools=tavily_enabled,
        )
        _tid = state.get("tenant_id")
        _caps = capability_names_from_registry_json(state.get("capability_registry") or "{}")
        _vg = ""
        if _tid and _caps:
            try:
                _vr = neo4j_client.get_vendor_capability_context(_tid, _caps)
                if _vr:
                    _vg = "Existing vendor→capability links:\n" + json.dumps(_vr, indent=2)
            except Exception:
                pass
        response = chain.invoke({
            "query": state["query"],
            "capability_registry": state.get("capability_registry") or "{}",
            "domain_outputs": state.get("domain_outputs", {}),
            "vendor_graph": _vg,
        })
        log_llm_complete(
            "Research",
            mode="fallback_chain",
            tavily_enabled=False,
            openai_compatible_skip_tools=tavily_enabled,
        )
        content = response.content if isinstance(response.content, str) else str(response.content)
    
    # Store actual LLM research results
    current_results = state.get("research_results", [])
    current_results.append({"sourcing_recommendations": content})
    
    return {"research_results": current_results}
