import json
import logging
import re
from src.graph.state import AgentState
from src.db.neo4j import neo4j_client
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import SecretStr
import os
from src.agents.llm_logging import log_llm_start, log_llm_complete
from src.agents.model_util import resolve_chat_model

logger = logging.getLogger(__name__)

def _normalize_related_capabilities(process: dict) -> list[str]:
    """Normalizes process capability references to a deduplicated list."""
    names = process.get("related_capability_names")
    if isinstance(names, list):
        return [n.strip() for n in names if isinstance(n, str) and n.strip()]
    single_name = process.get("related_capability_name")
    if isinstance(single_name, str) and single_name.strip():
        return [single_name.strip()]
    return []

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
                   "- 'processes': {{name, description, related_capability_names[]}}\n"
                   "CONSTRAINTS:\n"
                   "- Every capability must include a non-empty domain.\n"
                   "- If a capability has parent_capability_name, parent and child must belong to the same domain.\n"
                   "- Every process must include at least one related capability in related_capability_names.\n"
                   "- 'applications': {{name, description, fulfilled_capability_name}}\n"
                   "- 'technologies': {{name, category, supported_app_name}}\n"
                   "- 'vendors': {{name, product, fulfilling_entity_name, entity_type (Capability|Application|Technology)}}\n\n"
                   "Respond ONLY with a valid JSON object."),
        ("user", "Context to parse:\n{context}")
    ])

    try:
        openai_api_key = state.get("openai_api_key")
        model_id = resolve_chat_model(state)
        llm = ChatOpenAI(
            model=model_id,
            temperature=0,
            api_key=SecretStr(openai_api_key) if openai_api_key else None
        )
        chain = extractor_prompt | llm
        log_llm_start("Persistence", model=model_id)
        response = chain.invoke({"context": combined_context})
        log_llm_complete("Persistence")
        
        # Clean response content (handle triple backticks if present)
        raw_content = response.content if isinstance(response.content, str) else ""
        content = raw_content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        graph_data = json.loads(content)
        tenant_id = state.get("tenant_id")
        capability_domain_by_name: dict[str, str] = {}
        parent_links: list[tuple[str, str]] = []
        validation_errors: list[str] = []
        
        # 1. Persist Capabilities
        for cap in graph_data.get("capabilities", []):
            name = cap.get("name")
            if not name:
                logger.warning("Skipping capability with null name.")
                continue
                
            domain = cap.get("domain")
            if not isinstance(domain, str) or not domain.strip():
                validation_errors.append(f"Capability '{name}' is missing a valid domain.")
                continue
            domain = domain.strip()
            desc = cap.get("description") or ""
            capability_domain_by_name[name] = domain
            neo4j_client.upsert_capability(tenant_id, domain, name, desc)
            
            parent = cap.get("parent_capability_name")
            if isinstance(parent, str) and parent.strip():
                parent_links.append((parent.strip(), name))

        for parent_name, child_name in parent_links:
            parent_domain = capability_domain_by_name.get(parent_name)
            child_domain = capability_domain_by_name.get(child_name)
            if parent_domain and child_domain and parent_domain != child_domain:
                validation_errors.append(
                    f"Capability hierarchy violation: '{parent_name}' ({parent_domain}) cannot parent '{child_name}' ({child_domain})."
                )
                continue
            neo4j_client.set_capability_parent(tenant_id, parent_name, child_name)
            
        # 2. Persist Processes
        for process in graph_data.get("processes", []):
            process_name = process.get("name")
            if not isinstance(process_name, str) or not process_name.strip():
                continue
            process_name = process_name.strip()
            related_capabilities = _normalize_related_capabilities(process)
            if not related_capabilities:
                validation_errors.append(f"Process '{process_name}' has no related capabilities.")
                continue

            for related_capability in related_capabilities:
                neo4j_client.upsert_process(
                    tenant_id,
                    related_capability,
                    process_name,
                    process.get("description") or ""
                )

        if validation_errors:
            error_message = "; ".join(validation_errors)
            logger.error(f"Validation failed before persistence commit completion: {error_message}")
            return {
                "status": "PERSISTENCE_ERROR",
                "error": error_message
            }

        # 3. Persist Applications
        for app in graph_data.get("applications", []):
            fulfilled = app.get("fulfilled_capability_name")
            app_name = app.get("name")
            if app_name and fulfilled:
                neo4j_client.upsert_application(tenant_id, fulfilled, app_name, app.get("description") or "")

        # 4. Persist Technologies
        for tech in graph_data.get("technologies", []):
            supported = tech.get("supported_app_name")
            tech_name = tech.get("name")
            if tech_name and supported:
                neo4j_client.upsert_technology(tenant_id, supported, tech_name, tech.get("category") or "")

        # 5. Persist Vendor Products
        for v in graph_data.get("vendors", []):
            v_name = v.get("name")
            product = v.get("product")
            fulfilling = v.get("fulfilling_entity_name")
            if v_name and fulfilling:
                neo4j_client.upsert_vendor_product(
                    tenant_id,
                    v_name, 
                    product or "", 
                    v.get("entity_type") or "Capability", 
                    fulfilling
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
