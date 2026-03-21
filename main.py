import json
import logging
import os
import time

import click
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from src.api.auth import router as auth_router, get_current_user
from src.db.neo4j import neo4j_client
from src.graph.workflow import graph

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Enterprise Architecture Agent System API", version="0.1.0")

# CORS — set ALLOWED_ORIGINS in .env to your OCI VM public IP or domain
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost,http://localhost:3000")
allowed_origins = [o.strip() for o in _raw_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the Authentication Router
app.include_router(auth_router)

@app.get("/")
def read_root():
    return {"message": "Enterprise Architecture Agent System API is running."}

@app.get("/health")
def health_check():
    """Check backend and Neo4j connectivity."""
    try:
        neo4j_client.connect()
        # Run a lightweight ping query
        neo4j_client.query("RETURN 1 AS ok")
        return {"status": "ok", "neo4j": "connected"}
    except Exception as e:
        logger.warning(f"Health check: Neo4j unreachable — {e}")
        return {"status": "degraded", "neo4j": "disconnected", "detail": str(e)}

@app.get("/proposals")
def list_proposals(current_user: dict = Depends(get_current_user)):
    """List all saved proposals for the authenticated tenant."""
    tenant_id = current_user["tenant_id"]
    try:
        return neo4j_client.get_proposals(tenant_id)
    except Exception as e:
        logger.error(f"Failed to list proposals for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to retrieve proposals from knowledge base: {e}")

@app.get("/proposals/{proposal_id}")
def get_proposal(proposal_id: str, current_user: dict = Depends(get_current_user)):
    """Retrieve a specific proposal by ID for the authenticated tenant."""
    tenant_id = current_user["tenant_id"]
    try:
        proposal = neo4j_client.get_proposal_by_id(tenant_id, proposal_id)
    except Exception as e:
        logger.error(f"Failed to retrieve proposal {proposal_id} for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to retrieve proposal from knowledge base: {e}")
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal

@app.post("/request")
def handle_request(query: str, current_user: dict = Depends(get_current_user)):
    """Process an enterprise architecture request via LangGraph with authenticated tenant context."""
    tenant_id = current_user["tenant_id"]
    initial_state = {
        "tenant_id": tenant_id,
        "query": query,
        "required_domains": [],
        "domain_outputs": {},
        "research_results": [],
        "quality_status": "PENDING",
        "quality_feedback": "",
        "final_response": "",
        "messages": []
    }
    
    # Run the graph synchronously
    final_state = graph.invoke(initial_state)
    
    return {
        "status": "success", 
        "query": query, 
        "tenant_id": tenant_id,
        "user_email": current_user["email"],
        "engaged_domains": final_state.get("required_domains", []),
        "quality_check": final_state.get("quality_status"),
        "response": final_state.get("final_response")
    }

@app.post("/stream_request")
def handle_stream_request(query: str, current_user: dict = Depends(get_current_user)):
    """Process an enterprise architecture request and stream events via SSE."""
    tenant_id = current_user["tenant_id"]
    initial_state = {
        "tenant_id": tenant_id,
        "query": query,
        "required_domains": [],
        "domain_outputs": {},
        "research_results": [],
        "quality_status": "PENDING",
        "quality_feedback": "",
        "final_response": "",
        "messages": []
    }
    
    def event_generator():
        start_time = time.time()
        last_time = start_time
        
        aggregated_state = {}
        
        for event in graph.stream(initial_state):
            current_time = time.time()
            duration_ms = int((current_time - last_time) * 1000)
            
            for k, v in event.items():
                if isinstance(v, dict):
                    aggregated_state.update(v)
                    
                payload = {"node": k, "status": "completed", "duration_ms": duration_ms}
                # Use string concatenation to avoid regex or templating backslash escaping bugs
                yield "data: " + json.dumps(payload) + "\n\n"
                
            last_time = current_time
            
        # Stream has fully finished. Send the final composite response
        total_duration = int((time.time() - start_time) * 1000)
        final_payload = {
            "node": "AgentOrchestrator",
            "status": "final",
            "total_duration_ms": total_duration,
            "data": {
                "status": "success", 
                "query": query, 
                "tenant_id": tenant_id,
                "user_email": current_user["email"],
                "engaged_domains": aggregated_state.get("required_domains", []),
                "quality_check": aggregated_state.get("quality_status"),
                "response": aggregated_state.get("final_response"),
                "visualization": aggregated_state.get("visualization")
            }
        }
        
        yield "data: " + json.dumps(final_payload) + "\n\n"
                
    return StreamingResponse(event_generator(), media_type="text/event-stream")

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

