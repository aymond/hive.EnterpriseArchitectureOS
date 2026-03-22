"""Canonical vendor display names to avoid duplicate Vendor nodes (AWS vs Amazon Web Services, etc.)."""

from __future__ import annotations

import json
import re

from src.db.vendor_catalog_data import VENDOR_CATALOG_ENTRIES


def _norm_key(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[\s._\-]+", " ", s)
    return s.strip()


def normalize_vendor_input(name: str) -> str:
    """Normalized string for catalog / alias lookup (shared with Neo4j VendorCatalogAlias.normalized)."""
    return _norm_key(name)


def _alias_map_from_catalog() -> dict[str, str]:
    """Same alias → display_name edges as Neo4j seeding; used when DB lookup is unavailable."""
    m: dict[str, str] = {}
    for entry in VENDOR_CATALOG_ENTRIES:
        display = entry["display_name"]
        if not isinstance(display, str) or not display.strip():
            continue
        names = [display]
        for al in entry.get("aliases") or []:
            if isinstance(al, str) and al.strip():
                names.append(al.strip())
        for a in names:
            m[_norm_key(a)] = display.strip()
    return m


_ALIAS_TO_CANONICAL: dict[str, str] = _alias_map_from_catalog()


def canonical_vendor_name(name: str) -> str:
    """Return the canonical Vendor.name for Neo4j; unknown names pass through stripped."""
    if not isinstance(name, str) or not name.strip():
        return name if isinstance(name, str) else ""
    key = _norm_key(name)
    return _ALIAS_TO_CANONICAL.get(key, name.strip())


def vendor_naming_hint_for_prompts() -> str:
    """Short instruction for LLM prompts (research + persistence)."""
    return (
        "Use canonical vendor company names already used in the knowledge graph when applicable: "
        "prefer 'Amazon Web Services' over 'AWS'; prefer 'Microsoft' over 'Microsoft Azure' as the vendor entity "
        "(Azure offerings are products). Subsidiaries such as Red Hat or HashiCorp are valid vendor names when they "
        "sell software; the graph records a legal SUBSIDIARY_OF rollup to the parent (e.g. IBM). "
        "Do not create parallel Vendor nodes for the same company under spelling variants."
    )


def capability_names_from_registry_json(registry_json: str) -> list[str]:
    """Names from Domain Steward registry JSON for vendor context queries."""
    try:
        reg = json.loads(registry_json or "{}")
        out: list[str] = []
        for c in reg.get("capabilities", []):
            if not isinstance(c, dict):
                continue
            n = c.get("name")
            if isinstance(n, str) and n.strip():
                out.append(n.strip())
        return out
    except (json.JSONDecodeError, TypeError):
        return []
