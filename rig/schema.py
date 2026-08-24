"""Schema — Phase-0 scaffold.

PRD §7 Data model, BLUEPRINT §1 persistence.
Validates watchdog-state.json shape without external deps.
"""
from __future__ import annotations

REQUIRED_STATE_KEYS = {"CatalogHash", "PendingKeys", "TokenLevelNotified", "OutageNotified"}


def validate_state(state: dict) -> list[str]:
    errs: list[str] = []
    for k in REQUIRED_STATE_KEYS:
        if k not in state:
            errs.append(f"missing {k}")
    return errs
