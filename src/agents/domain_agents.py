import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from src.graph.state import AgentState
from src.db.neo4j import neo4j_client

# We assume OPENAI_API_KEY is available in the AgentState
def create_domain_node(domain_name: str, domain_description: str):
    """Factory function to create domain expert nodes."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are an Enterprise Architecture expert focused on the {domain_name} domain.\n"
                   f"Your focus is: {domain_description}\n"
                   "Analyze the user's request and propose a faceted model update.\n"
                   "IMPORTANT: Review 'Existing Context' and avoid duplication.\n"
                   "Output a structured JSON containing:\n"
                   "- 'capabilities': List of business/technical functions.\n"
                   "- 'processes': List of processes with process name, description, and related capability name.\n"
                   "- 'applications': List of software systems/apps fulfilling those capabilities.\n"
                   "- 'technologies': Underlying stack (platforms, infra) supporting the applications.\n"
                   "- 'business_drivers': Strategic goals.\n"
                   "- 'recommendations': Architecture advice."),
        ("user", "Request: {query}\n\nExisting Context from Neo4j: {existing_context}\nCurrent Peer Domain Outputs: {domain_outputs}")
    ])
    
    def domain_node(state: AgentState):
        llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=state.get("openai_api_key"))
        chain = prompt | llm
        
        # Fetch existing capabilities from Neo4j for this domain
        query = "MATCH (d:Domain {name: $domain})-[:HAS_CAPABILITY]->(c) RETURN c.name as name, c.description as description"
        existing_data = neo4j_client.query(query, {"domain": domain_name})
        existing_context = json.dumps(existing_data) if existing_data else "None found."

        response = chain.invoke({
            "query": state["query"],
            "existing_context": existing_context,
            "domain_outputs": state.get("domain_outputs", {})
        })
        
        # Update state domain outputs
        current_outputs = state.get("domain_outputs", {})
        current_outputs[domain_name] = response.content
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
