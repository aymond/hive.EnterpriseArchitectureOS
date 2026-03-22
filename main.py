from __future__ import annotations

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
from src.registry.capability_registry import DEFAULT_REGISTRY_PATH, load_capability_registry
from src.api.security import decrypt_key
from src.config.llm_providers import (
    LLM_PROVIDER_OPENAI_COMPATIBLE,
    normalize_llm_provider,
    validate_openai_compatible_base_url,
)
from src.config.openai_models import normalize_llm_model_for_provider

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _graph_initial_state_for_user(tenant_id: str, query: str, email: str) -> dict:
    """Resolve API keys, LLM provider, model, and base URL for LangGraph."""
    settings = neo4j_client.get_user_llm_settings(email)
    if not settings:
        raise HTTPException(status_code=404, detail="User not found")
    provider = normalize_llm_provider(settings.get("llm_provider"))
    llm_model = normalize_llm_model_for_provider(provider, settings.get("llm_model"))

    keys = neo4j_client.get_user_api_keys(email)
    encrypted_openai = keys.get("openai")
    encrypted_tavily = keys.get("tavily")

    openai_api_key = ""
    if encrypted_openai:
        openai_api_key = decrypt_key(encrypted_openai) or ""

    tavily_api_key = decrypt_key(encrypted_tavily) if encrypted_tavily else None

    openai_base_url = ""
    if provider == LLM_PROVIDER_OPENAI_COMPATIBLE:
        raw = (settings.get("openai_base_url") or "").strip()
        if not raw:
            raise HTTPException(
                status_code=400,
                detail="Configure an OpenAI-compatible base URL in your profile (e.g. http://localhost:11434/v1).",
            )
        try:
            openai_base_url = validate_openai_compatible_base_url(raw)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        if not encrypted_openai:
            raise HTTPException(
                status_code=400,
                detail="Missing OpenAI API Key. Please configure it in your account settings.",
            )
        if not openai_api_key:
            raise HTTPException(
                status_code=400,
                detail="Failed to decrypt OpenAI API Key. The system secret may have changed.",
            )

    return {
        "tenant_id": tenant_id,
        "query": query,
        "openai_api_key": openai_api_key,
        "tavily_api_key": tavily_api_key,
        "llm_model": llm_model,
        "llm_provider": provider,
        "openai_base_url": openai_base_url or None,
        "required_domains": [],
        "capability_registry": "",
        "domain_outputs": {},
        "research_results": [],
        "quality_status": "PENDING",
        "quality_feedback": "",
        "governance_admin_log": "",
        "involved_capabilities": [],
        "final_response": "",
        "visualization": "",
        "messages": [],
    }


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
def process_request(query: str, current_user: dict = Depends(get_current_user)):
    """Process an enterprise architecture request via LangGraph with authenticated tenant context."""
    tenant_id = current_user["tenant_id"]
    initial_state = _graph_initial_state_for_user(tenant_id, query, current_user["email"])
    
    # Run the graph synchronously
    final_state = graph.invoke(initial_state)
    adm = final_state.get("governance_admin_log") or ""
    if adm.strip():
        logger.info("governance_admin_log (tenant=%s): %s", tenant_id, adm.strip()[:12000])
    
    return {
        "status": "success", 
        "query": query, 
        "tenant_id": tenant_id,
        "user_email": current_user["email"],
        "engaged_domains": final_state.get("required_domains", []),
        "quality_check": final_state.get("quality_status"),
        "quality_feedback": final_state.get("quality_feedback"),
        "governance_admin_log": final_state.get("governance_admin_log", ""),
        "response": final_state.get("final_response")
    }

@app.post("/stream_request")
def handle_stream_request(query: str, current_user: dict = Depends(get_current_user)):
    """Process an enterprise architecture request and stream events via SSE."""
    tenant_id = current_user["tenant_id"]
    initial_state = _graph_initial_state_for_user(tenant_id, query, current_user["email"])
    
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
                "quality_feedback": aggregated_state.get("quality_feedback"),
                "governance_admin_log": aggregated_state.get("governance_admin_log", ""),
                "response": aggregated_state.get("final_response"),
                "visualization": aggregated_state.get("visualization")
            }
        }
        
        yield "data: " + json.dumps(final_payload) + "\n\n"
        adm = aggregated_state.get("governance_admin_log") or ""
        if adm.strip():
            logger.info("governance_admin_log (stream tenant=%s): %s", tenant_id, adm.strip()[:12000])
                
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

    provider = normalize_llm_provider(os.getenv("LLM_PROVIDER"))
    llm_model = normalize_llm_model_for_provider(provider, os.getenv("OPENAI_LLM_MODEL"))
    api_key = os.getenv("OPENAI_API_KEY") or ""
    raw_base = os.getenv("OPENAI_COMPATIBLE_BASE_URL", "")
    openai_base_url = ""
    if provider == LLM_PROVIDER_OPENAI_COMPATIBLE:
        if not raw_base.strip():
            click.echo("Set OPENAI_COMPATIBLE_BASE_URL (e.g. http://localhost:11434/v1) for OpenAI-compatible mode.", err=True)
            raise SystemExit(1)
        try:
            openai_base_url = validate_openai_compatible_base_url(raw_base)
        except ValueError as e:
            click.echo(str(e), err=True)
            raise SystemExit(1)
    elif not api_key.strip():
        click.echo("Set OPENAI_API_KEY for OpenAI cloud mode, or LLM_PROVIDER=openai_compatible with OPENAI_COMPATIBLE_BASE_URL.", err=True)
        raise SystemExit(1)

    initial_state = {
        "tenant_id": "cli_test_tenant",
        "query": query,
        "openai_api_key": api_key,
        "tavily_api_key": os.getenv("TAVILY_API_KEY"),
        "llm_model": llm_model,
        "llm_provider": provider,
        "openai_base_url": openai_base_url or None,
        "required_domains": [],
        "capability_registry": "",
        "domain_outputs": {},
        "research_results": [],
        "quality_status": "PENDING",
        "quality_feedback": "",
        "governance_admin_log": "",
        "involved_capabilities": [],
        "final_response": "",
        "visualization": "",
        "messages": [],
    }
    
    for event in graph.stream(initial_state):
        for k, v in event.items():
            if k == "Coordinator":
                click.secho(f"Coordinator selected domains: {v.get('required_domains')}", fg="blue")
            elif k == "DomainSteward":
                click.secho("Domain Steward published canonical capability registry.", fg="blue")
            elif k in ["Strategy", "Enterprise", "Technology", "Security", "Data", "Process", "Compliance"]:
                click.secho(f"{k} Agent finished analyzing the request.", fg="green")
            elif k == "Research":
                click.secho(f"Research Agent identified vendors/tools for requested capabilities.", fg="yellow")
            elif k == "GovernanceRemediation":
                click.secho("Governance Remediation: normalized domain outputs against registry.", fg="yellow")
            elif k == "QualityCheck":
                status = v.get("quality_status")
                color = "green" if status == "APPROVED" else ("yellow" if status == "APPROVED_WITH_WARNINGS" else "red")
                click.secho(f"Governance Check: {status}", fg=color)
            elif k == "Persistence":
                status = v.get("status") if v else "COMPLETE"
                click.secho(f"Knowledge Base: {status}", fg="cyan")
            elif k == "Synthesizer":
                click.secho("\n--- Final Final EA Response ---", fg="magenta")
                click.echo(v.get("final_response"))

@cli.command("sync-capability-domains")
@click.option(
    "--tenant-id",
    envvar="SYNC_TENANT_ID",
    default="default-tenant",
    show_default=True,
    help="Tenant id for Domain/Capability MERGE keys (unless a row sets tenant_id).",
)
@click.option(
    "--registry",
    "registry_path",
    type=click.Path(exists=True, dir_okay=False, path_type=str),
    default=None,
    help=f"Path to registry JSON. Default: {DEFAULT_REGISTRY_PATH}",
)
@click.option(
    "--normalize-null/--no-normalize-null",
    default=True,
    show_default=True,
    help="Set tenant_id on Capability nodes that match by name but have null tenant_id before linking.",
)
def sync_capability_domains(tenant_id: str, registry_path: str | None, normalize_null: bool):
    """Apply data/capability_registry.json (or --registry) to Neo4j: Domain HAS_CAPABILITY Capability."""
    path = registry_path or str(DEFAULT_REGISTRY_PATH)
    reg = load_capability_registry(path)
    neo4j_client.connect()
    result = neo4j_client.apply_capability_registry_domain_links(
        tenant_id,
        reg,
        normalize_null_tenant_capabilities=normalize_null,
    )
    click.echo(json.dumps(result, indent=2))
    if result.get("errors"):
        raise click.Abort()


@cli.command("seed-vendor-catalog")
def seed_vendor_catalog_cmd():
    """Load global VendorCatalogEntry / VendorCatalogAlias / SUBSIDIARY_OF into Neo4j (idempotent)."""
    neo4j_client.connect()
    result = neo4j_client.seed_vendor_catalog()
    click.echo(json.dumps(result, indent=2))


@cli.command("dedupe-vendors")
@click.option(
    "--tenant-id",
    default=None,
    help="Merge duplicate Vendor nodes for this tenant only. Omit to run for every tenant_id on Vendor nodes.",
)
def dedupe_vendors(tenant_id: str | None):
    """Merge Vendor aliases (e.g. AWS → Amazon Web Services) and reattach OFFERS; IMPLEMENTS unchanged."""
    neo4j_client.connect()
    if tenant_id:
        result = neo4j_client.dedupe_vendors_for_tenant(tenant_id)
    else:
        result = neo4j_client.dedupe_vendors_all_tenants()
    click.echo(json.dumps(result, indent=2))


@cli.command()
def serve():
    """Run the API server"""
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    cli()

