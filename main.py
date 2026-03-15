import os
from fastapi import FastAPI, Header, HTTPException
import uvicorn
import click
from dotenv import load_dotenv
from src.graph.workflow import graph

import logging

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from src.db.neo4j import neo4j_client

app = FastAPI(title="Enterprise Architecture Agent System API", version="0.1.0")

@app.get("/")
def read_root():
    return {"message": "Enterprise Architecture Agent System API is running."}

@app.get("/proposals")
def list_proposals(x_tenant_id: str = Header(...)):
    """List all saved proposals for the given tenant."""
    return neo4j_client.get_proposals(x_tenant_id)

@app.get("/proposals/{proposal_id}")
def get_proposal(proposal_id: str, x_tenant_id: str = Header(...)):
    """Retrieve a specific proposal by ID for the given tenant."""
    proposal = neo4j_client.get_proposal_by_id(x_tenant_id, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal

@app.post("/request")
def handle_request(query: str, x_tenant_id: str = Header(...)):
    """Process an enterprise architecture request via LangGraph with tenant context."""
    initial_state = {
        "tenant_id": x_tenant_id,
        "query": query,
        "required_domains": [],
        "domain_outputs": {},
        "research_results": [],
        "quality_status": "PENDING",
        "quality_feedback": "",
        "final_response": "",
        "messages": []
    }
    
    # Run the graph synchronously for the API example
    final_state = graph.invoke(initial_state)
    
    return {
        "status": "success", 
        "query": query, 
        "tenant_id": x_tenant_id,
        "engaged_domains": final_state.get("required_domains", []),
        "quality_check": final_state.get("quality_status"),
        "response": final_state.get("final_response")
    }

@click.group()
def cli():
    """Enterprise Architecture Agent System CLI"""
    pass

@cli.command()
@click.argument('query')
def process(query):
    """Process an enterprise architecture request via CLI."""
    click.echo(f"Received request: {query}")
    click.echo("Starting Chief EA Coordinator Analysis...")
    
    initial_state = {
        "query": query,
        "required_domains": [],
        "domain_outputs": {},
        "research_results": [],
        "quality_status": "PENDING",
        "quality_feedback": "",
        "final_response": "",
        "messages": []
    }
    
    for event in graph.stream(initial_state):
        for k, v in event.items():
            if k == "Coordinator":
                click.secho(f"Coordinator selected domains: {v.get('required_domains')}", fg="blue")
            elif k in ["Strategy", "Enterprise", "Technology", "Security", "Data", "Compliance"]:
                click.secho(f"{k} Agent finished analyzing the request.", fg="green")
            elif k == "Research":
                click.secho(f"Research Agent identified vendors/tools for requested capabilities.", fg="yellow")
            elif k == "QualityCheck":
                status = v.get("quality_status")
                color = "green" if status == "APPROVED" else "red"
                click.secho(f"Governance Check: {status}", fg=color)
            elif k == "Persistence":
                status = v.get("status") if v else "COMPLETE"
                click.secho(f"Knowledge Base: {status}", fg="cyan")
            elif k == "Synthesizer":
                click.secho("\n--- Final Final EA Response ---", fg="magenta")
                click.echo(v.get("final_response"))

@cli.command()
def serve():
    """Run the API server"""
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    cli()

