import logging
from src.graph.state import AgentState
from src.db.neo4j import neo4j_client

logger = logging.getLogger(__name__)

def archive_agent(state: AgentState):
    """
    Archive Agent - Responsible for storing the final synthesized proposal 
    into the Neo4j Proposal Repository.
    """
    
    tenant_id = state.get("tenant_id")
    final_response = state.get("final_response")
    query = state.get("query")
    
    if not final_response:
        logger.warning("No final response found to archive.")
        return {"status": "ARCHIVE_SKIPPED"}
    
    try:
        logger.info(f"Archiving architectural proposal to Neo4j for tenant {tenant_id}...")
        neo4j_client.save_proposal(tenant_id, query, final_response)
        logger.info("Proposal successfully archived.")
        return {"status": "PROPOSAL_ARCHIVED"}
    except Exception as e:
        logger.error(f"Failed to archive proposal: {e}")
        return {"status": "ARCHIVE_ERROR", "error": str(e)}
