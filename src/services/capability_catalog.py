"""Union of static capability registry and tenant Neo4j graph for catalog UI."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Optional

from src.db.neo4j import neo4j_client
from src.registry.capability_registry import load_capability_registry


def slugify_segment(name: str) -> str:
    s = (name or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "item"


def resolve_domain_name(domain_slug: str, domain_names: list[str]) -> Optional[str]:
    target = domain_slug.strip().lower()
    for n in domain_names:
        if slugify_segment(n) == target:
            return n
    return None


def _registry_domains_and_caps(reg: dict) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    dom_meta: dict[str, dict] = {}
    for d in reg.get("domains") or []:
        if not isinstance(d, dict):
            continue
        n = d.get("name")
        if isinstance(n, str) and n.strip():
            dom_meta[n.strip()] = {"purpose": (d.get("purpose") or "") if isinstance(d.get("purpose"), str) else ""}

    caps_by_domain: dict[str, list[dict]] = defaultdict(list)
    for c in reg.get("capabilities") or []:
        if not isinstance(c, dict):
            continue
        name, od = c.get("name"), c.get("owning_domain")
        if not isinstance(name, str) or not name.strip():
            continue
        if not isinstance(od, str) or not od.strip():
            continue
        desc = c.get("description") if isinstance(c.get("description"), str) else ""
        parent = c.get("parent_capability_name")
        pstr = parent.strip() if isinstance(parent, str) and parent.strip() else None
        caps_by_domain[od.strip()].append(
            {
                "name": name.strip(),
                "description": desc,
                "parent_name": pstr,
                "source": "registry",
            }
        )
    return dom_meta, dict(caps_by_domain)


def build_tenant_capability_catalog(tenant_id: str) -> dict[str, Any]:
    reg = load_capability_registry()
    reg_meta, reg_caps = _registry_domains_and_caps(reg)

    graph_rows = neo4j_client.get_capabilities_with_domains_for_tenant(tenant_id)
    graph_by_domain: dict[str, list[dict]] = defaultdict(list)
    for row in graph_rows or []:
        d = row.get("domain")
        if not isinstance(d, str) or not d.strip():
            continue
        graph_by_domain[d.strip()].append(
            {
                "name": row.get("name"),
                "description": (row.get("description") or "") if row.get("description") is not None else "",
                "parent_name": row.get("parent_name"),
                "source": "graph",
            }
        )

    all_names = sorted(set(reg_meta.keys()) | set(reg_caps.keys()) | set(graph_by_domain.keys()))

    domains_out: list[dict[str, Any]] = []
    for name in all_names:
        slug = slugify_segment(name)
        purpose = reg_meta.get(name, {}).get("purpose", "")
        merged = _merge_capabilities(
            reg_caps.get(name, []),
            graph_by_domain.get(name, []),
        )
        domains_out.append(
            {
                "name": name,
                "slug": slug,
                "purpose": purpose,
                "capability_count": len(merged),
            }
        )

    return {
        "domains": domains_out,
        "_all_domain_names": all_names,
        "_reg_caps": reg_caps,
        "_graph_by_domain": dict(graph_by_domain),
    }


def _merge_capabilities(reg_list: list[dict], graph_list: list[dict]) -> list[dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for item in reg_list:
        n = item["name"]
        if n not in by_name:
            order.append(n)
        by_name[n] = {
            "name": n,
            "description": item.get("description") or "",
            "parent_name": item.get("parent_name"),
            "sources": ["registry"],
        }

    for item in graph_list:
        n = item.get("name")
        if not isinstance(n, str) or not n.strip():
            continue
        n = n.strip()
        desc = item.get("description") or ""
        parent = item.get("parent_name")
        if n in by_name:
            entry = by_name[n]
            if desc:
                entry["description"] = desc
            if parent:
                entry["parent_name"] = parent
            if "graph" not in entry["sources"]:
                entry["sources"].append("graph")
        else:
            order.append(n)
            by_name[n] = {
                "name": n,
                "description": desc,
                "parent_name": parent if isinstance(parent, str) else None,
                "sources": ["graph"],
            }

    return [by_name[k] for k in order if k in by_name]


def get_capabilities_for_domain_slug(tenant_id: str, domain_slug: str) -> Optional[dict[str, Any]]:
    catalog = build_tenant_capability_catalog(tenant_id)
    names = catalog["_all_domain_names"]
    resolved = resolve_domain_name(domain_slug, names)
    if not resolved:
        return None
    reg_caps = catalog["_reg_caps"]
    graph_by_domain = catalog["_graph_by_domain"]
    merged = _merge_capabilities(reg_caps.get(resolved, []), graph_by_domain.get(resolved, []))
    caps_out = [{**c, "slug": slugify_segment(c["name"])} for c in merged]
    purpose = ""
    for d in catalog["domains"]:
        if d["name"] == resolved:
            purpose = d.get("purpose") or ""
            break
    return {
        "domain": {"name": resolved, "slug": slugify_segment(resolved), "purpose": purpose},
        "capabilities": caps_out,
    }


def resolve_capability_in_domain(
    tenant_id: str, domain_slug: str, capability_slug: str
) -> Optional[dict[str, Any]]:
    block = get_capabilities_for_domain_slug(tenant_id, domain_slug)
    if not block:
        return None
    dname = block["domain"]["name"]
    for cap in block["capabilities"]:
        if slugify_segment(cap["name"]) == capability_slug.strip().lower():
            return {"domain": block["domain"], "capability": cap}
    return None
