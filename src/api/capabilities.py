"""Tenant-scoped capability catalog (registry ∪ Neo4j graph)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from src.api.auth import get_current_user
from src.services.capability_catalog import (
    build_tenant_capability_catalog,
    get_capabilities_for_domain_slug,
    resolve_capability_in_domain,
    slugify_segment,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


@router.get("/domains")
def list_capability_domains(current_user: dict = Depends(get_current_user)):
    tenant_id = current_user["tenant_id"]
    try:
        cat = build_tenant_capability_catalog(tenant_id)
        return {"domains": cat["domains"]}
    except Exception as e:
        logger.exception("capability domains list failed tenant=%s", tenant_id)
        raise HTTPException(status_code=503, detail=f"Failed to load capability catalog: {e}") from e


@router.get("/domains/{domain_slug}")
def get_domain_capabilities(domain_slug: str, current_user: dict = Depends(get_current_user)):
    tenant_id = current_user["tenant_id"]
    try:
        block = get_capabilities_for_domain_slug(tenant_id, domain_slug)
    except Exception as e:
        logger.exception("domain capabilities failed tenant=%s slug=%s", tenant_id, domain_slug)
        raise HTTPException(status_code=503, detail=f"Failed to load domain capabilities: {e}") from e
    if not block:
        raise HTTPException(status_code=404, detail="Domain not found")
    return block


@router.get("/domains/{domain_slug}/capabilities/{capability_slug}")
def get_capability_detail(
    domain_slug: str, capability_slug: str, current_user: dict = Depends(get_current_user)
):
    tenant_id = current_user["tenant_id"]
    try:
        row = resolve_capability_in_domain(tenant_id, domain_slug, capability_slug)
    except Exception as e:
        logger.exception(
            "capability detail failed tenant=%s domain=%s cap=%s",
            tenant_id,
            domain_slug,
            capability_slug,
        )
        raise HTTPException(status_code=503, detail=f"Failed to load capability: {e}") from e
    if not row:
        raise HTTPException(status_code=404, detail="Capability not found")
    cap = row["capability"]
    dom = row["domain"]
    return {
        "domain": dom,
        "capability": {
            "name": cap["name"],
            "slug": slugify_segment(cap["name"]),
            "description": cap.get("description") or "",
            "parent_name": cap.get("parent_name"),
            "sources": cap.get("sources") or [],
        },
    }
