import json
import logging
import re
from src.graph.state import AgentState
from src.db.neo4j import neo4j_client
from src.db.vendor_canonical import (
    capability_names_from_registry_json,
    vendor_naming_hint_for_prompts,
)
from langchain_core.prompts import ChatPromptTemplate
import os
from src.agents.llm_factory import get_chat_llm
from src.agents.llm_logging import log_llm_start, log_llm_complete
from src.agents.model_util import resolve_chat_model

logger = logging.getLogger(__name__)

def _reconcile_domains_with_registry(graph_data: dict, registry_json: str) -> None:
    """Force capability.domain to match registry owning_domain when names align."""
    try:
        reg = json.loads(registry_json)
        owners: dict[str, str] = {}
        for c in reg.get("capabilities", []):
            if not isinstance(c, dict):
                continue
            n, od = c.get("name"), c.get("owning_domain")
            if isinstance(n, str) and n.strip() and isinstance(od, str) and od.strip():
                owners[n.strip()] = od.strip()
        for cap in graph_data.get("capabilities", []):
            if not isinstance(cap, dict):
                continue
            name = cap.get("name")
            if isinstance(name, str) and name.strip() in owners:
                cap["domain"] = owners[name.strip()]
    except (json.JSONDecodeError, TypeError):
        pass


def _dedupe_capabilities_by_name(graph_data: dict) -> None:
    caps = graph_data.get("capabilities")
    if not isinstance(caps, list):
        return
    seen: set[str] = set()
    out: list[dict] = []
    for cap in caps:
        if not isinstance(cap, dict):
            continue
        n = cap.get("name")
        if not isinstance(n, str) or not n.strip():
            continue
        key = n.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cap)
    graph_data["capabilities"] = out


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
    
    qs = state.get("quality_status")
    if qs not in ("APPROVED", "APPROVED_WITH_WARNINGS"):
        logger.info(f"Governance check status is {qs}. Skipping persistence.")
        return {"status": "SKIPPED_PERSISTENCE"}
    
    domain_outputs = state.get("domain_outputs", {})
    research_results = state.get("research_results", [])
    
    logger.info("Persistence agent starting. Extracting graph structure via LLM...")

    # Combine all context for the extractor
    reg = (state.get("capability_registry") or "").strip() or "{}"
    combined_context = (
        "Canonical Capability Registry (use as source of truth for owning_domain when names match):\n"
        f"{reg}\n\n"
        f"User Request: {state['query']}\n\n"
    )
    for domain, output in domain_outputs.items():
        combined_context += f"--- {domain} Domain Expert Output ---\n{output}\n\n"
    
    for res in research_results:
        combined_context += f"--- Sourcing/Research Output ---\n{res.get('sourcing_recommendations', '')}\n\n"

    tenant_id = state.get("tenant_id")
    cap_names_ctx = capability_names_from_registry_json(reg)
    if tenant_id and cap_names_ctx:
        try:
            vrows = neo4j_client.get_vendor_capability_context(tenant_id, cap_names_ctx)
            if vrows:
                combined_context += (
                    "Existing Vendor→Product links in the knowledge graph for registry capabilities "
                    "(reuse exact vendor names when the same company is meant; avoid alternate spellings):\n"
                    + json.dumps(vrows, indent=2)
                    + "\n\n"
                )
        except Exception as ex:
            logger.warning("Could not load vendor/capability context from Neo4j: %s", ex)

    combined_context += vendor_naming_hint_for_prompts() + "\n\n"

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
                   "- Process objects MUST use the key 'name' (never 'process_name').\n"
                   "- Each capability name must appear at most once in the output; no duplicate names with different domains.\n"
                   "- When the registry lists a capability, set 'domain' to that capability's owning_domain from the registry.\n"
                   "- 'applications': {{name, description, fulfilled_capability_name}}\n"
                   "- 'technologies': {{name, category, supported_app_name}}\n"
                   "- 'vendors': {{name, product, fulfilling_entity_name, entity_type (Capability|Application|Technology)}}\n"
                   "- For vendors: prefer names from the existing graph list above when it is the same company; "
                   "follow the canonical vendor naming rules in the context.\n\n"
                   "Respond ONLY with a valid JSON object."),
        ("user", "Context to parse:\n{context}")
    ])

    try:
        model_id = resolve_chat_model(state)
        llm = get_chat_llm(state, temperature=0)
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
        _reconcile_domains_with_registry(graph_data, state.get("capability_registry") or "{}")
        _dedupe_capabilities_by_name(graph_data)
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
            if (not isinstance(process_name, str) or not process_name.strip()) and isinstance(
                process.get("process_name"), str
            ):
                process_name = process.get("process_name")
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
                    fulfilling,
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
