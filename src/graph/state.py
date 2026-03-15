from typing import TypedDict, List, Dict, Any, Annotated
import operator

def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Reducer function to merge dictionaries from concurrent nodes."""
    return {**a, **b}

class AgentState(TypedDict):
    # The ID of the tenant for data isolation
    tenant_id: str
    
    # The initial request from the user
    query: str
    
    # Track which domains should be engaged
    required_domains: List[str]
    
    # The current findings and capability updates from domains
    # Using Annotated and a reducer to handle concurrent writes from domain agents
    domain_outputs: Annotated[Dict[str, Any], merge_dicts]
    
    # Products and vendors researched
    research_results: Annotated[List[Dict[str, Any]], operator.add]
    
    # Status of the EA quality check
    quality_status: str
    quality_feedback: str
    
    # List of capabilities involved in this specific request
    involved_capabilities: List[str]
    
    # Final consolidated EA response
    final_response: str
    
    # Generated Mermaid visualization
    visualization: str
    
    # Internal messaging history
    messages: Annotated[List[Any], operator.add]
