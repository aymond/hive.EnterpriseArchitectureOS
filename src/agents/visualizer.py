import logging
from src.graph.state import AgentState
from src.db.neo4j import neo4j_client

logger = logging.getLogger(__name__)

def sanitize_id(name: str) -> str:
    """Sanitize capability name to be a valid Mermaid ID (alphanumeric and underscores)."""
    return "".join(c if c.isalnum() or c == '_' else '_' for c in name)

def escape_label(name: str) -> str:
    """Escape double quotes in labels for Mermaid."""
    return name.replace('"', '#quot;')

def visualizer_agent(state: AgentState):
    """
    Visualizer Agent - Generates a Mermaid.js diagram representing the 
    capability hierarchy and its dependencies from Neo4j.
    """
    
    involved_capabilities = state.get("involved_capabilities", [])
    tenant_id = state.get("tenant_id")
    
    if not involved_capabilities:
        logger.warning("No capabilities identified for visualization.")
        return {"visualization": ""}
    
    try:
        logger.info(f"Generating visualization for capabilities: {involved_capabilities} for tenant {tenant_id}")
        hierarchy = neo4j_client.get_capability_hierarchy(tenant_id, involved_capabilities)
        
        if not hierarchy:
            return {"visualization": ""}
            
        # Build Mermaid Top-Down Diagram
        mermaid_lines = ["graph TD"]
        
        # Track connections to avoid duplicates
        connections = set()
        defined_nodes = set()
        
        for record in hierarchy:
            parent = record.get("parent")
            cap = record.get("capability")
            child = record.get("child")
            
            cap_id = sanitize_id(cap)
            cap_label = escape_label(cap)
            
            if parent:
                p_id = sanitize_id(parent)
                p_label = escape_label(parent)
                conn = f'    {p_id}["{p_label}"] --> {cap_id}["{cap_label}"]'
                if conn not in connections:
                    mermaid_lines.append(conn)
                    connections.add(conn)
                    defined_nodes.add(p_id)
                    defined_nodes.add(cap_id)
            
            if child:
                c_id = sanitize_id(child)
                c_label = escape_label(child)
                conn = f'    {cap_id}["{cap_label}"] --> {c_id}["{c_label}"]'
                if conn not in connections:
                    mermaid_lines.append(conn)
                    connections.add(conn)
                    defined_nodes.add(cap_id)
                    defined_nodes.add(c_id)
            
            # Ensure the node itself is defined if it has no connections
            if cap_id not in defined_nodes:
                mermaid_lines.append(f'    {cap_id}["{cap_label}"]')
                defined_nodes.add(cap_id)

        mermaid = "```mermaid\n" + "\n".join(mermaid_lines) + "\n```"
        
        logger.info("Successfully generated Mermaid visualization.")
        return {"visualization": mermaid}
        
    except Exception as e:
        logger.error(f"Failed to generate visualization: {e}")
        return {"visualization": "", "visualizer_error": str(e)}
