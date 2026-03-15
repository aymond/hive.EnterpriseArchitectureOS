import json
import logging
import re
from src.graph.state import AgentState
from src.db.neo4j import neo4j_client
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import os

logger = logging.getLogger(__name__)
llm = ChatOpenAI(model="gpt-4o", temperature=0)

def persistence_agent(state: AgentState):
    """
    Persistence Agent - Uses an LLM to extract a high-fidelity EA graph 
    from multi-agent outputs and commits it to Neo4j.
    """
    
    if state.get("quality_status") != "APPROVED":
        logger.info(f"Governance check status is {state.get('quality_status')}. Skipping persistence.")
        return {"status": "SKIPPED_PERSISTENCE"}
    
    domain_outputs = state.get("domain_outputs", {})
    research_results = state.get("research_results", [])
    
    logger.info("Persistence agent starting. Extracting graph structure via LLM...")

    # Combine all context for the extractor
    combined_context = f"User Request: {state['query']}\n\n"
    for domain, output in domain_outputs.items():
        combined_context += f"--- {domain} Domain Expert Output ---\n{output}\n\n"
    
    for res in research_results:
        combined_context += f"--- Sourcing/Research Output ---\n{res.get('sourcing_recommendations', '')}\n\n"

    extractor_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an EA Data Architect. Your task is to transform technical agent outputs into a formal TOGAF-aligned graph structure.\n"
                   "Extract the following entities and relationships as a JSON object:\n"
                   "ENTITIES:\n"
                   "- 'capabilities': {{name, description, domain, parent_capability_name}}\n"
                   "- 'applications': {{name, description, fulfilled_capability_name}}\n"
                   "- 'technologies': {{name, category, supported_app_name}}\n"
                   "- 'vendors': {{name, product, fulfilling_entity_name, entity_type (Capability|Application|Technology)}}\n\n"
                   "Respond ONLY with a valid JSON object."),
        ("user", "Context to parse:\n{context}")
    ])

    try:
        chain = extractor_prompt | llm
        response = chain.invoke({"context": combined_context})
        
        # Clean response content (handle triple backticks if present)
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        graph_data = json.loads(content)
        
        # 1. Persist Capabilities
        for cap in graph_data.get("capabilities", []):
            name = cap.get("name")
            if not name:
                logger.warning("Skipping capability with null name.")
                continue
                
            neo4j_client.upsert_capability(cap.get("domain", "General"), name, cap.get("description", ""))
            if cap.get("parent_capability_name"):
                neo4j_client.set_capability_parent(cap.get("parent_capability_name"), name)
            
        # 2. Persist Applications
        for app in graph_data.get("applications", []):
            neo4j_client.upsert_application(app.get("fulfilled_capability_name"), app.get("name"), app.get("description", ""))

        # 3. Persist Technologies
        for tech in graph_data.get("technologies", []):
            neo4j_client.upsert_technology(tech.get("supported_app_name"), tech.get("name"), tech.get("category", ""))

        # 4. Persist Vendor Products
        for v in graph_data.get("vendors", []):
            neo4j_client.upsert_vendor_product(
                v.get("name"), 
                v.get("product"), 
                v.get("entity_type", "Capability"), 
                v.get("fulfilling_entity_name")
            )

        involved_capabilities = [cap.get("name") for cap in graph_data.get("capabilities", []) if cap.get("name")]

        logger.info("Successfully committed EA graph to Neo4j.")
        return {
            "status": "KNOWLEDGE_GRAPH_UPDATED",
            "involved_capabilities": involved_capabilities
        }

    except Exception as e:
        logger.error(f"Failed to extract or persist EA graph: {e}")
        return {"status": "PERSISTENCE_ERROR", "error": str(e)}
