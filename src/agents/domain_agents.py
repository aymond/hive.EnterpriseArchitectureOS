import json
from langchain_core.prompts import ChatPromptTemplate
from src.graph.state import AgentState
from src.db.neo4j import neo4j_client
from src.agents.llm_factory import get_chat_llm
from src.agents.llm_logging import log_llm_start, log_llm_complete
from src.agents.model_util import resolve_chat_model

# LLM credentials come from AgentState (OpenAI cloud or OpenAI-compatible base URL).
def create_domain_node(domain_name: str, domain_description: str):
    """Factory function to create domain expert nodes."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are an Enterprise Architecture expert focused on the {domain_name} domain.\n"
                   f"Your focus is: {domain_description}\n"
                   "Analyze the user's request and propose a faceted model update.\n"
                   "You work under a Canonical Capability Registry (see user message). It is authoritative for "
                   "which capability belongs to which domain.\n"
                   "RULES:\n"
                   f"- Your domain is exactly \"{domain_name}\". Every entry in 'capabilities' MUST set "
                   f'\"domain\": \"{domain_name}\".\n'
                   "- Only include capabilities in 'capabilities' that the registry assigns to YOUR domain. "
                   "Do NOT re-home or duplicate a capability owned by another domain under your domain.\n"
                   "For capabilities owned by peer domains, you may reference them only in 'recommendations' or cross-domain notes, "
                   "not as your owned capabilities.\n"
                   "- Parent/child capability relationships you propose must stay within YOUR domain (same 'domain' value).\n"
                   "- 'processes': use the key \"name\" for the process title (never \"process_name\"). "
                   "Each process MUST include 'related_capability_names' (array) using exact capability names from the registry "
                   "or names your domain legitimately owns.\n"
                   "  Every process needs at least one related capability. A process may map to multiple capabilities.\n"
                   "- Use consistent naming: reuse registry capability names verbatim when referring to the same thing.\n"
                   "Output a structured JSON containing:\n"
                   "- 'capabilities': List for YOUR domain only; each includes name, description, domain, parent_capability_name (optional).\n"
                   "- 'processes': List with name, description, related_capability_names (array).\n"
                   "- 'applications': List of software systems/apps fulfilling capabilities.\n"
                   "- 'technologies': Underlying stack supporting the applications.\n"
                   "- 'business_drivers': Strategic goals.\n"
                   "- 'recommendations': Architecture advice.\n"
                   "IMPORTANT: Review 'Existing Context' and avoid duplication."),
        ("user", "Request: {query}\n\n"
                 "Canonical Capability Registry (JSON — follow ownership strictly):\n{capability_registry}\n\n"
                 "Existing Context from Neo4j: {existing_context}\n"
                 "Current Peer Domain Outputs: {domain_outputs}")
    ])
    
    def domain_node(state: AgentState):
        model_id = resolve_chat_model(state)
        llm = get_chat_llm(state, temperature=0)
        chain = prompt | llm
        
        # Fetch existing capabilities from Neo4j for this domain
        query = "MATCH (d:Domain {name: $domain})-[:HAS_CAPABILITY]->(c) RETURN c.name as name, c.description as description"
        existing_data = neo4j_client.query(query, {"domain": domain_name})
        existing_context = json.dumps(existing_data) if existing_data else "None found."

        log_llm_start(domain_name, model=model_id)
        response = chain.invoke({
            "query": state["query"],
            "capability_registry": state.get("capability_registry") or "{}",
            "existing_context": existing_context,
            "domain_outputs": state.get("domain_outputs", {})
        })
        log_llm_complete(domain_name)
        
        # Update state domain outputs
        current_outputs = state.get("domain_outputs", {})
        out = response.content if isinstance(response.content, str) else str(response.content)
        current_outputs[domain_name] = out
        return {"domain_outputs": current_outputs}
    
    return domain_node

# Define specific domain experts
strategy_agent = create_domain_node(
    "Strategy", 
    "Aligning business goals, drivers, and high-level enterprise objectives."
)

enterprise_agent = create_domain_node(
    "Enterprise", 
    "Focusing on business processes, organizational structures, and business capabilities."
)

technology_agent = create_domain_node(
    "Technology", 
    "Managing the technology capability model, infrastructure, and application portfolio."
)

security_agent = create_domain_node(
    "Security", 
    "Ensuring security controls, identity management, risk assessment, and cyber principles."
)

data_agent = create_domain_node(
    "Data", 
    "Governing data architecture, data models, information flows, and analytics capabilities."
)

process_agent = create_domain_node(
    "Process",
    "Modeling business and operational processes, process ownership, and process-to-capability traceability."
)

compliance_agent = create_domain_node(
    "Compliance", 
    "Validating against regulatory requirements, standard policies, and legal frameworks."
)
