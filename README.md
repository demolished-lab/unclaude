# Claude Rig — One-Command Unlimited Claude

**Status:** Draft — docs-first foundation · Phase 0 pending approval
**Owner:** Raja (@Raja) · Product to ship as public GitHub repo
**References:** PRD.md · BLUEPRINT.md · DESIGN-BRIEF.md · SECURITY-AUDIT.md · `rig/` (Phase-0 scaffold)
**License:** MIT (repo), provider ToS respected (no account farming)

> **Locked scope:** Fully-free-first GitHub product. One command → auto-detects machine (OS/RAM/disk/GPU) → bootstraps Free Claude Code gateway + RTK + Caveman + ECC → wires 6+ free provider pools behind one local key → quota-aware headroom routing → local Ollama fallback as infinite floor. Paid keys are strictly opt-in (user pastes, never required). Every anomaly — free-list churn, 401/402/403/413/429, gateway down, disk low, model deprecation — is handled autonomously via corner toast + one-click browser + paste-panel; rest is hands-free. Background research runs on a tiny fraction of session tokens, never dazing output quality, dynamically fetching token-optimized data across the internet.

## What this is

Claude Rig gives any developer a *feels-unlimited* Claude Code without touching `claude.ai` billing. You run one command in a fresh terminal, approve a few OS pop-ups (paste free API keys when asked), and `claude` just works — task-tier routing picks the strongest free model for the job, fallbacks burn the deepest free pools first, and a local model catches you when the internet pools thin. A background research lane spends <2% of session tokens to continuously discover better free routes and token-optimization intel.

This repo's rig (your current `C:\Users\Raja` setup) stays untouched. `claude-rig` is a separate, production-grade product that *learns from* that rig.

## Document map

| Doc | Governs | Precedence |
|---|---|---|
| `README.md` (this) | Entry + working contract | — |
| `PRD.md` | *What* we ship (FR-x.y + AC) | Wins on requirements |
| `BLUEPRINT.md` | *How* it's wired (layers, routing, anomaly matrix, meta-engine) | Wins on wiring |
| `DESIGN-BRIEF.md` | *How it looks/feels* (every pixel, tokens, flows) | Wins on UI |
| `SECURITY-AUDIT.md` | *What must be true before launch* (gates G1–G7) | Blocks launch |
| `rig/` | Phase-0 scaffold (stdlib-only, meta-engine skeleton) | Must match docs |

Cross-links are bidirectional; PRD ↔ Blueprint ↔ Design Brief contradictions are resolved by precedence above.

## Working contract

- **Docs before code.** No feature ships unless PRD says so. Doc change ⇒ deliberate, acknowledged.
- **Docs are truth.** Code matches docs, never reverse.
- **No silent changes.** Guardrails never quietly loosened.
- **Nothing unattended that can hurt.** No auto-account creation, no multi-account bypass, no scraping that violates provider ToS, no crypto.
- **Free-first, paid-opt-in.** Free tiers are the product; paid keys are a user choice, never a dark pattern.

## Locked decisions

- Fully-free product; paid keys are optional, user-supplied, encrypted at rest, never required for basic power.
- One-command install: `install.ps1` (Windows) / `install.sh` (macOS/Linux/WSL) → device detection → gateway + watchdog + `claude` shim.
- Effortless UX: OS corner toast → *Open key page* (already logged in) → paste into panel → Enter — no searching, no docs hunting.
- Background research lane: dynamic, internet-wide, token-optimized, <2% of session budget, never degrades output.
- Local infinite floor (Ollama `llama3.2:1b` / `qwen2.5:0.5b` class) as final fallback when remote pools exhaust.
- 6 verified free pools at launch: Gemini, NVIDIA NIM, Groq, Cloudflare AI, OpenRouter `:free`, Ollama Cloud (+ Cerebras/GitHub Models when user opts in).

## Open questions

- OQ-1: Default daily token budget — 2M fixed or device-scaled (RAM/disk)? **Default:** 2M, auto-scales +20% per 8GB RAM above 16GB (see PRD OQ-1).
- OQ-2: Provider daily limits — hard-code estimates vs live probe calibration? **Default:** hard-coded estimates + nightly latency probe as tie-breaker (BLUEPRINT §3.2).
- OQ-3: Telemetry — opt-in anonymous headroom stats to improve free-model ranking? **Default:** off, consent-gated (PRD FR-9.3).
- OQ-4: Corporate proxy / offline-first — support air-gapped local-only mode? **Default:** v2.
- OQ-5: Windows toast vs in-TUI prompt — OS toast is primary (visible when Claude not running); should we also mirror inside Claude Code TUI? **Default:** OS primary, TUI mirror v2.

## Current status

- Specified: this README + PRD + Blueprint + Design Brief + Security Audit (in progress)
- Scaffolded (Phase 0): `rig/` — meta-engine skeleton (detect→triage→plan→rehearse→apply→verify→learn) with open-ended ANON taxonomy
- Pending: owner approval of OQ-1..OQ-5; then `install.sh/ps1` + cross-platform watchdog (`rig/watchdog/`)
- Open questions: OQ-1..OQ-5 above

## 60-second promise (after install)

```powershell
# Windows
irm https://raw.githubusercontent.com/<you>/claude-rig/main/install.ps1 | iex
# macOS/Linux/WSL
curl -fsSL https://raw.githubusercontent.com/<you>/claude-rig/main/install.sh | bash

# then just
claude
# → if a key is needed: toast pops → click "Open key page" → paste → Enter → done
# → `claude.exe` still bypasses to direct Anthropic
```
