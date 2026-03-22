import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from src.graph.state import AgentState
from src.db.neo4j import neo4j_client
from src.agents.llm_logging import log_llm_start, log_llm_complete
from src.agents.model_util import resolve_chat_model

# We assume OPENAI_API_KEY is available in the AgentState
def create_domain_node(domain_name: str, domain_description: str):
    """Factory function to create domain expert nodes."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are an Enterprise Architecture expert focused on the {domain_name} domain.\n"
                   f"Your focus is: {domain_description}\n"
                   "Analyze the user's request and propose a faceted model update.\n"
                   "IMPORTANT: Review 'Existing Context' and avoid duplication.\n"
                   "Output a structured JSON containing:\n"
                   "- 'capabilities': List of business/technical functions. Every capability must include domain.\n"
                   "- 'processes': List of processes with process name, description, and related_capability_names (array).\n"
                   "  A process may map to many capabilities, and capabilities may have many processes.\n"
                   "  Never emit a process without at least one related capability.\n"
                   "- 'applications': List of software systems/apps fulfilling those capabilities.\n"
                   "- 'technologies': Underlying stack (platforms, infra) supporting the applications.\n"
                   "- 'business_drivers': Strategic goals.\n"
                   "- 'recommendations': Architecture advice."),
        ("user", "Request: {query}\n\nExisting Context from Neo4j: {existing_context}\nCurrent Peer Domain Outputs: {domain_outputs}")
    ])
    
    def domain_node(state: AgentState):
        openai_api_key = state.get("openai_api_key")
        model_id = resolve_chat_model(state)
        llm = ChatOpenAI(
            model=model_id,
            temperature=0,
            api_key=SecretStr(openai_api_key) if openai_api_key else None
        )
        chain = prompt | llm
        
        # Fetch existing capabilities from Neo4j for this domain
        query = "MATCH (d:Domain {name: $domain})-[:HAS_CAPABILITY]->(c) RETURN c.name as name, c.description as description"
        existing_data = neo4j_client.query(query, {"domain": domain_name})
        existing_context = json.dumps(existing_data) if existing_data else "None found."

        log_llm_start(domain_name, model=model_id)
        response = chain.invoke({
            "query": state["query"],
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
