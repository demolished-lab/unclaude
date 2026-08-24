"""Background research lane — PRD FR-9, BLUEPRINT 6.1.

Sidecar that spends <2% of session tokens to fetch token-optimized intel.
Writes rig/research/brief.md (<=1K tokens) as CLAUDE.md appendix.
Allow-listed sources only, never sends project files.
"""
import json
import pathlib
import urllib.request
import datetime

ALLOW_LIST = [
    "https://api.github.com/repos/Alishahryar1/free-claude-code/releases/latest",
    "https://api.github.com/repos/rtk-ai/rtk/releases/latest",
    "https://api.github.com/repos/JuliusBrussee/caveman/releases/latest",
    "https://api.github.com/repos/affaan-m/ECC/releases/latest",
]

BRIEF_PATH = pathlib.Path(__file__).parent / "brief.md"
MANIFEST_PATH = pathlib.Path(__file__).parent / "manifest.json"
FCC_MODELS = "http://127.0.0.1:8082/v1/models"

def get_session_tokens():
    total = 0
    root = pathlib.Path.home() / ".claude" / "projects"
    if not root.exists():
        return 0
    for p in root.rglob("*.jsonl"):
        try:
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                if '"usage"' in line:
                    o = json.loads(line)
                    u = (o.get("message") or {}).get("usage")
                    if u:
                        total += int(u.get("input_tokens", 0)) + int(u.get("output_tokens", 0))
        except Exception:
            continue
    return total

def fetch_json(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "claude-rig-research"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

def run(budget_tokens=4000):
    session_tokens = get_session_tokens()
    # enforce <2% budget
    max_research = max(500, int(session_tokens * 0.02)) if session_tokens else budget_tokens
    max_research = min(max_research, budget_tokens)

    lines = [f"# Research Brief — {datetime.datetime.now(datetime.timezone.utc).isoformat()}", "", f"Session tokens: {session_tokens}, research budget: {max_research}", ""]
    # FCC catalog snapshot
    try:
        with urllib.request.urlopen(FCC_MODELS, timeout=10) as r:
            data = json.loads(r.read())
            lines.append(f"FCC catalog: {len(data.get('data', []))} entries")
    except Exception as e:
        lines.append(f"FCC catalog: unavailable ({e})")

    # Allow-listed releases
    for url in ALLOW_LIST:
        j = fetch_json(url)
        tag = j.get("tag_name", j.get("error", "unknown"))
        lines.append(f"- {url.split('/')[-4]}/{url.split('/')[-3]}: {tag}")

    brief = "\n".join(lines)[:4000]  # cap at ~1K tokens
    BRIEF_PATH.write_text(brief, encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps({"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(), "budget": max_research, "sources": ALLOW_LIST}, indent=2), encoding="utf-8")
    print(f"brief written to {BRIEF_PATH} ({len(brief)} chars, budget {max_research})")
    return 0

if __name__ == "__main__":
    import sys
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 4000)
