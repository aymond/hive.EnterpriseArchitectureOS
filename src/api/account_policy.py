"""Normalization and validation for account identifiers and passwords."""

from __future__ import annotations

import re

MAX_FULL_NAME_LEN = 200
MIN_PASSWORD_LEN = 12


def normalize_account_email(email: str) -> str:
    """Lowercase and strip for stable login and uniqueness (RFC 5321 local-part case sensitivity ignored for UX)."""
    return email.strip().lower()


def sanitize_full_name(name: str) -> str:
    s = name.strip()
    if len(s) > MAX_FULL_NAME_LEN:
        s = s[:MAX_FULL_NAME_LEN]
    return s


def validate_password_policy(password: str) -> None:
    """
    Enforce minimum strength for new passwords and registration.
    Raises ValueError with a short message suitable for API detail.
    """
    if not isinstance(password, str):
        raise ValueError("Password is required.")
    if len(password) < MIN_PASSWORD_LEN:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LEN} characters.")
    if not re.search(r"[A-Za-z]", password):
        raise ValueError("Password must contain at least one letter.")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit.")
