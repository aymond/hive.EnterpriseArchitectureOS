"""
Authoritative vendor taxonomy for Neo4j seeding (global catalog, not tenant-scoped).

Each entry has a stable key, display_name used on tenant :Vendor nodes, optional aliases,
and optional subsidiary_of (parent key) for legal rollup.
"""

from __future__ import annotations

from typing import Any

# Keys are stable slugs; subsidiary_of references another entry's key.
VENDOR_CATALOG_ENTRIES: list[dict[str, Any]] = [
    {
        "key": "amazon_web_services",
        "display_name": "Amazon Web Services",
        "aliases": [
            "Amazon Web Services",
            "AWS",
            "Amazon Web Services (AWS)",
            "Amazon AWS",
            "AWS Cloud",
        ],
        "subsidiary_of": None,
    },
    {
        "key": "microsoft",
        "display_name": "Microsoft",
        "aliases": [
            "Microsoft",
            "Microsoft Corporation",
            "Microsoft Azure",
            "MS Azure",
            "MSFT",
            "Azure",
        ],
        "subsidiary_of": None,
    },
    {
        "key": "google_cloud",
        "display_name": "Google Cloud",
        "aliases": [
            "Google Cloud",
            "Google Cloud Platform",
            "GCP",
        ],
        "subsidiary_of": None,
    },
    {
        "key": "ibm",
        "display_name": "IBM",
        "aliases": ["IBM", "International Business Machines", "International Business Machines Corporation"],
        "subsidiary_of": None,
    },
    {
        "key": "red_hat",
        "display_name": "Red Hat",
        "aliases": ["Red Hat", "RedHat", "Red Hat Inc", "Red Hat, Inc.", "RHEL"],
        "subsidiary_of": "ibm",
    },
    {
        "key": "hashicorp",
        "display_name": "HashiCorp",
        "aliases": ["HashiCorp", "Hashi Corp", "Hashicorp"],
        "subsidiary_of": "ibm",
    },
]
