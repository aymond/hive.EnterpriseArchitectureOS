import logging
import json
from src.graph.state import AgentState
from src.db.neo4j import neo4j_client
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)
llm = ChatOpenAI(model="gpt-4o", temperature=0)

def discovery_agent(state: AgentState):
    """
    Discovery Agent - Scans the Neo4j graph for latent relationships 
    between new and existing capabilities to enable continuous learning.
    """
    
    involved_capabilities = state.get("involved_capabilities", [])
    user_query = state.get("query", "")
    
    if not involved_capabilities:
        return {"status": "SKIPPED_DISCOVERY"}
        
    try:
        # 1. Get all capabilities from the graph for context
        all_caps = neo4j_client.get_all_capabilities()
        
        # Filter out the current ones to avoid redundant comparisons
        existing_caps = [c for c in all_caps if c["name"] not in involved_capabilities]
        
        if not existing_caps:
            return {"status": "NO_EXISTING_CONTEXT"}

        logger.info(f"Discovery agent scanning for links between {involved_capabilities} and {len(existing_caps)} existing capabilities.")

        # 2. Use LLM to find latent relationships
        discovery_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an EA Knowledge Discovery Agent. Your task is to identify latent relationships between new architectural capabilities and existing ones in the knowledge graph.\n\n"
                       "USER INTENT (Current Request): {query}\n"
                       "NEW CAPABILITIES PROPOSED: {involved}\n"
                       "EXISTING KNOWLEDGE GRAPH CAPABILITIES: {existing}\n\n"
                       "GOAL: Identify if any of the new capabilities are logical sub-capabilities (children) of existing ones, or vice versa.\n"
                       "EXAMPLE: If new is 'MFA' and existing is 'Identity Management', then 'Identity Management' is likely PARENT_OF 'MFA'.\n"
                       "Return ONLY a JSON array of relationship objects: [{{ \"parent\": \"Parent Name\", \"child\": \"Child Name\", \"type\": \"PARENT_OF\" }}]\n"
                       "If no relationships are found, return an empty array []."),
            ("user", "Analyze the context and propose improvements to the capability hierarchy.")
        ])

        chain = discovery_prompt | llm
        response = chain.invoke({
            "query": user_query,
            "involved": json.dumps(involved_capabilities),
            "existing": json.dumps(existing_caps)
        })

        # IMPROVED: Clean and parse JSON
        content = response.content.strip()
        logger.info(f"Discovery agent raw response: {content[:100]}...") # Log start of response
        
        # Use regex to find the first JSON array in the response
        import re
        match = re.search(r"(\[.*\])", content, re.DOTALL)
        if match:
            json_str = match.group(1)
            try:
                new_relationships = json.loads(json_str)
            except json.JSONDecodeError as je:
                logger.error(f"Failed to parse discovered JSON: {je}. Raw: {json_str}")
                return {"discovery_status": "JSON_PARSE_ERROR"}
        else:
            logger.warning("No JSON array found in discovery response.")
            return {"discovery_status": "NO_RELATIONS_FOUND"}

        # 3. Commit discovered relationships to Neo4j
        discovered_count = 0
        if isinstance(new_relationships, list):
            for rel in new_relationships:
                if rel.get("type") == "PARENT_OF" and rel.get("parent") and rel.get("child"):
                    neo4j_client.set_capability_parent(rel["parent"], rel["child"])
                    discovered_count += 1
                    # Also update state so visualizer sees them immediately
                    if rel["parent"] not in involved_capabilities:
                        involved_capabilities.append(rel["parent"])
                    if rel["child"] not in involved_capabilities:
                        involved_capabilities.append(rel["child"])

        logger.info(f"Discovered and committed {discovered_count} new relationships.")
        return {
            "involved_capabilities": list(set(involved_capabilities)),
            "discovery_status": f"SUCCESS_{discovered_count}_NEW_RELATIONS"
        }

    except Exception as e:
        logger.error(f"Discovery agent failed: {e}")
        return {"discovery_error": str(e)}
