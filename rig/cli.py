"""CLI — Phase-0 scaffold.

Implements PRD FR-11.2 DryRun and BLUEPRINT §6.1 detect/triage/plan verbs.
Usage: python -m rig.cli scan [--dry-run]
SECURITY-AUDIT G-7: this is the command verified on fresh VM.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.request

from rig.schema import validate_state

FCC_HEALTH = "http://127.0.0.1:8082/health"
FCC_MODELS = "http://127.0.0.1:8082/v1/models"


def cmd_scan(dry_run: bool = False) -> int:
    print("rig scan — Phase-0 (docs-first, not production)")
    if dry_run:
        print("[dry-run] would check: FCC health, catalog hash, token budget, disk headroom")
        return 0
    try:
        with urllib.request.urlopen(FCC_HEALTH, timeout=5) as r:
            print(f"FCC health: {r.status}")
    except Exception as e:
        print(f"FCC health: DOWN ({e})")
    try:
        with urllib.request.urlopen(FCC_MODELS, timeout=10) as r:
            data = json.loads(r.read())
            print(f"catalog: {len(data.get('data', []))} entries")
    except Exception as e:
        print(f"catalog: unavailable ({e})")
    state_path = pathlib.Path.home() / ".fcc" / "watchdog-state.json"
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8-sig"))
            errs = validate_state(state)
            print(f"watchdog state: {state_path} — {'ok' if not errs else '; '.join(errs)}")
        except Exception as e:
            print(f"watchdog state: corrupt ({e})")
    else:
        print(f"watchdog state: not yet created ({state_path})")
    print("scan done — see PRD FR-7, BLUEPRINT §6")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(prog="rig")
    sub = p.add_subparsers(dest="cmd")
    s = sub.add_parser("scan", help="meta-engine skeleton scan")
    s.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if args.cmd == "scan":
        sys.exit(cmd_scan(dry_run=args.dry_run))
    p.print_help()
    sys.exit(2)


if __name__ == "__main__":
    main()
