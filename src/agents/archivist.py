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

    if not tenant_id:
        logger.warning("No tenant_id found in state — proposal will NOT be archived. Ensure authenticated API calls pass tenant context.")
        return {"status": "ARCHIVE_SKIPPED_NO_TENANT"}

    if not final_response:
        logger.warning("No final response found to archive.")
        return {"status": "ARCHIVE_SKIPPED"}
    
    try:
        logger.info(f"Archiving architectural proposal to Neo4j for tenant {tenant_id}...")
        result = neo4j_client.save_proposal(tenant_id, query, final_response)
        proposal_id = result[0].get("id") if result else "unknown"
        logger.info(f"Proposal successfully archived with id={proposal_id} for tenant={tenant_id}.")
        return {"status": "PROPOSAL_ARCHIVED", "proposal_id": proposal_id}
    except Exception as e:
        logger.error(f"Failed to archive proposal: {e}")
        return {"status": "ARCHIVE_ERROR", "error": str(e)}
