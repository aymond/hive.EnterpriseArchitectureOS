from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = REPO_ROOT / "data" / "capability_registry.json"


def load_capability_registry(path: str | Path | None = None) -> dict:
    """Load registry JSON (same shape as Domain Steward: domains + capabilities)."""
    p = Path(path) if path is not None else DEFAULT_REGISTRY_PATH
    with open(p, encoding="utf-8") as f:
        return json.load(f)
