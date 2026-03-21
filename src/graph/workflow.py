from typing import Literal
from langgraph.graph import StateGraph, START, END
from src.graph.state import AgentState
from src.agents.coordinator import coordinator_agent, synthesis_agent
from src.agents.domain_agents import (
    strategy_agent, enterprise_agent, technology_agent, 
    security_agent, data_agent, compliance_agent
)
from src.agents.research_agent import research_agent
from src.agents.validation_agents import quality_check_agent
from src.agents.persistence import persistence_agent
from src.agents.archivist import archive_agent
from src.agents.visualizer import visualizer_agent
from src.agents.discovery import discovery_agent

# Initialize Graph
builder = StateGraph(AgentState)

# Add Nodes
builder.add_node("Coordinator", coordinator_agent)
builder.add_node("Strategy", strategy_agent)
builder.add_node("Enterprise", enterprise_agent)
builder.add_node("Technology", technology_agent)
builder.add_node("Security", security_agent)
builder.add_node("Data", data_agent)
builder.add_node("Compliance", compliance_agent)
builder.add_node("Research", research_agent)
builder.add_node("QualityCheck", quality_check_agent)
builder.add_node("Persistence", persistence_agent)
builder.add_node("Discovery", discovery_agent)
builder.add_node("Visualizer", visualizer_agent)
builder.add_node("Synthesizer", synthesis_agent)
builder.add_node("Archivist", archive_agent)

# Routing Logic
def route_to_domains(state: AgentState) -> list[str]:
    """Dynamically route to the required domain experts based on the coordinator's assessment."""
    domains: list[str] = list(state.get("required_domains", []))
    if not domains:
        # Fallback
        return ["Enterprise", "Technology"]
    
    # Filter only valid node names
    valid_nodes = ["Strategy", "Enterprise", "Technology", "Security", "Data", "Compliance"]
    return [d for d in domains if d in valid_nodes]

# Edges
builder.add_edge(START, "Coordinator")

# Conditional routing from Coordinator to selected domains
builder.add_conditional_edges(
    "Coordinator",
    route_to_domains,
    {
        "Strategy": "Strategy",
        "Enterprise": "Enterprise",
        "Technology": "Technology",
        "Security": "Security",
        "Data": "Data",
        "Compliance": "Compliance"
    }
)

# All domain agents converge on Research
builder.add_edge("Strategy", "Research")
builder.add_edge("Enterprise", "Research")
builder.add_edge("Technology", "Research")
builder.add_edge("Security", "Research")
builder.add_edge("Data", "Research")
builder.add_edge("Compliance", "Research")

# Research goes to Quality Check
builder.add_edge("Research", "QualityCheck")

# Split paths at QualityCheck
builder.add_edge("QualityCheck", "Persistence")
builder.add_edge("QualityCheck", "Synthesizer")

# Path A: Knowledge Graph & Visual Modeling
builder.add_edge("Persistence", "Discovery")
builder.add_edge("Discovery", "Visualizer")
builder.add_edge("Visualizer", END)

# Path B: Final Synthesis & Archiving
builder.add_edge("Synthesizer", "Archivist")
builder.add_edge("Archivist", END)

# Compile Graph
graph = builder.compile()
