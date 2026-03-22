from typing import TypedDict, List, Dict, Any, Sequence, Annotated, Optional
import operator

def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Reducer function to merge dictionaries from concurrent nodes."""
    return {**a, **b}

class AgentState(TypedDict):
    # The ID of the tenant for data isolation
    tenant_id: str
    
    # The initial request from the user
    query: str
    
    # Decrypted OpenAI API Key provided by the user profile
    openai_api_key: str
    
    # Decrypted Tavily API Key provided by the user profile
    tavily_api_key: Optional[str]

    # OpenAI chat model id from user profile (e.g. gpt-4o) or Ollama tag when compatible
    llm_model: str

    # openai | openai_compatible (Ollama, LM Studio, vLLM, …)
    llm_provider: str

    # Base URL for OpenAI-compatible APIs (e.g. http://localhost:11434/v1); empty for OpenAI cloud
    openai_base_url: Optional[str]
    
    # Track which domains should be engaged
    required_domains: List[str]

    # JSON string: canonical domains + capabilities with single owning_domain (from Domain Steward)
    capability_registry: str
    
    # The current findings and capability updates from domains
    # Using Annotated and a reducer to handle concurrent writes from domain agents
    domain_outputs: Annotated[Dict[str, Any], merge_dicts]
    
    # Products and vendors researched
    research_results: Annotated[List[Dict[str, Any]], operator.add]
    
    # Status of the EA quality check
    quality_status: str
    quality_feedback: str
    # Technical governance notes for operators / logs (not shown in end-user UI)
    governance_admin_log: str
    
    # List of capabilities involved in this specific request
    involved_capabilities: List[str]
    
    # Final consolidated EA response
    final_response: str
    
    # Generated Mermaid visualization
    visualization: str
    
    # Internal messaging history
    messages: Annotated[List[Any], operator.add]
