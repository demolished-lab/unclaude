# Blueprint — Claude Rig

**Status:** Draft · awaiting owner approval
**Owner:** Raja
**References:** README.md · PRD.md · DESIGN-BRIEF.md · SECURITY-AUDIT.md

> **Locked scope:** Same as PRD. Blueprint wins on wiring when PRD and Blueprint conflict.

## 1. Architecture layers + repo-to-layer map

```
┌─ User terminal (PowerShell/zsh/bash) ──────────────────────┐
│  shim: function claude → health probe → fcc-claude        │  install.ps1 / install.sh
├─ Compression (input→output) ───────────────────────────────┤
│  RTK hook (global) → Caveman plugin → ECC skills           │  ~/.claude/settings.json, plugins/
├─ Gateway ──────────────────────────────────────────────────┤
│  FCC 5.13.10 · 127.0.0.1:8082 · /v1/messages · /v1/models   │  uv tool free-claude-code
├─ Routing ──────────────────────────────────────────────────┤
│  Tier map (MODEL_*) + MODEL_FALLBACKS (headroom+latency)   │  ~/.fcc/.env  →  FCC-Watchdog.ps1
├─ Providers (6+1 pools) ────────────────────────────────────┤
│  gemini · nvidia_nim · groq · cloudflare · open_router     │  provider_status + /v1/models
│  ollama_cloud · ollama (local floor)                       │
├─ Watchdog (meta-engine) ───────────────────────────────────┤
│  cycle 600s · mutex · autostart · heal · headroom · alarm  │  fcc-watchdog/FCC-Watchdog.ps1
├─ Background research lane ─────────────────────────────────┤
│  <2% sidecar → rig/research/brief.md                       │  rig/research/
└─ Persistence ──────────────────────────────────────────────┘
   ~/.fcc/.env (encrypted) · ~/.fcc/watchdog-state.json       · state
   ~/.claude/projects/*.jsonl (token source)                 · usage
   E:\models, E:\venv\vyuha, C:\vdisks\vyuha.vhdx             · local
```

Repo map (new `claude-rig` repo, not the live `C:\Users\Raja` rig):
```
claude-rig/
  install.ps1 / install.sh          → F-1
  rig/watchdog/FCC-Watchdog.ps1     → F-7
  rig/research/brief.md + manifest  → F-9
  rig/detect/ , triage/ , plan/     → meta-engine §6
  tests/ , .github/workflows/ci.yml
  docs/ (this set, copied as source of truth)
```

## 2. AI Resource OS / routing

- **Gateway:** FCC exposes Anthropic `POST /v1/messages` and `GET /v1/models`. Claude Code sets `ANTHROPIC_BASE_URL=http://127.0.0.1:8082`, `ANTHROPIC_AUTH_TOKEN=freecc`.
- **Tier map:** `claude-opus-*`→`MODEL_OPUS`, `claude-sonnet-*`→`MODEL_SONNET`, `claude-haiku-*`→`MODEL_HAIKU`, `fable`→`MODEL_FABLE`, else `MODEL`. Verified via `server.log: generativelanguage.googleapis.com`.
- **Fallback chain:** `MODEL_FALLBACKS` comma-separated, headroom-sorted (desc `LeftPct`, tie-break `BenchmarkScores` ms), but `ollama/*` pinned last. Reorder only when `bestPct - worstPct ≥ 25` (avoids thrash).
- **Headroom calc:** `avgTok = tokensToday / requestsToday` (transcripts + `server.log` tail 400), `used = reqs * avgTok`, `LeftPct = 100*(limit-used)/limit`. Limits: `ProviderDailyLimits` §PRD FR-5.3.
- **Local floor:** `ollama/llama3.2:1b` (1.3GB, 90s cold via FCC but `LOCAL OK` verified) → infinite, last resort. `ollama serve` auto-started if `11434` down.
- **Budget alarm:** `Get-TokensToday` sums today's `usage.*_tokens` from `~/.claude/projects/*.jsonl`; toast at 80/100% of `TokenBudgetDaily` (device-scaled).

## 3. Use cases by lane

- **Lane A: Fresh install** — `install.ps1 -DryRun` → plan → `install.ps1` → device detect → `uv tool install free-claude-code` → `fcc-desktop` → health 200 → shim → `claude -p "hi"` via FCC.
- **Lane B: Daily coding** — `claude` → tier primary → on 429/401/402/403/413 fallback down chain, re-ascend next request after daily reset.
- **Lane C: Catalog churn** — provider deprecates `gpt-oss-120b` overnight → next cycle hash mismatch → `Find-BestModel` picks next `ModelPrefs` hit → `validate+apply` → toast.
- **Lane D: Key death mid-session** — `provider_status=unauthorized` → toast → dialog → browser → paste → hot-reload → session continues.
- **Lane E: Background research** — sidecar every N sessions, ≤2% budget, fetches provider docs/model catalogs/RTK notes across internet, writes compact `brief.md` (≤1K tok) as `CLAUDE.md` appendix.

## 4. Anomaly matrix (every failure class)

| Class | Example | Detection | Mitigation | Enforcing layer |
|---|---|---|---|---|
| 401/403 | revoked Gemini key | `provider_status` | toast+dialog → browser → paste → apply | watchdog |
| 402 | Cerebras billing, OpenRouter credit 0 | same | same; plus `402` not added to chain if free tier now paid-gated | PRD FR-11.1 |
| 413 | `llama-3.3-fp8-fast` payload too large | `cf_bigcontext.py` probe at 50K tok | exclude from `ModelPrefs`, heal to `gpt-oss-120b` | F-4 probe |
| 429 | Gemini 5 RPM burst | `server.log: 429` + retry 5 → fallback | fallback + headroom demotion next cycle | routing |
| 410 | `llama-3.1-8b` deprecated | catalog hash | heal | watchdog |
| Gateway down | `fcc-server` crash | `GET /health` fail | toast, shim auto-starts `fcc-desktop` | shim+watchdog |
| Disk low | C: 12GB, E: VHDX growth | `Get-PSDrive` <15GB | toast + prune `%TEMP%` | watchdog |
| Catalog shift | new `gemini-3.8` appears | hash change, no slot dead | info toast `catalog changed` | watchdog |
| Unknown (ANON) | novel 5xx shape | open-ended taxonomy §6.4 | generative triage, never escalate by default | meta-engine |

All anomalies are **generatively handled**, not escalated, unless `PendingKeys` re-ask limit exceeded (3 cycles).

## 5. Guardrails

- Free-first: paid keys never required; `DryRun` prints plan for every mutation.
- No account farming: one legitimate account/key per provider; duplicate-account bypass is hard-banned (PRD FR-11.1).
- No scraping that violates ToS: catalog via official `/v1/models`; provider docs via official `freellmapi.co`/`build.nvidia.com` etc.
- Single-instance mutex, startup via `Startup/*.lnk` (no admin `schtasks`).
- Secrets: FCC encrypts `~/.fcc/.env` at rest; watchdog never logs raw keys (fingerprints only: `nvapi-xxxxx...`).
- Budget: research lane hard-capped `<2%`; violation throttles next cycle.

## 6. Meta-engine (the caveat auto-handler)

The rig's *caveat engine* is the watchdog's autonomic loop — a **detect → triage → plan → rehearse → apply → verify → learn** pipeline that runs every cycle without human in the loop, handling even unknown errors.

**6.1 Roles:**
- `rig/detect/` — `Invoke-FccGet /health`, `provider_status`, `Get-NormalizedCatalog`, `Get-TokensToday`, `Get-DiskHeadroom`.
- `rig/triage/` — classify into `missing_key | rate_limit | payload_too_large | deprecated | gateway_down | disk_low | catalog_shift | anon`.
- `rig/plan/` — `Find-BestModel`, `Get-ProviderHeadroom`, `Optimize-RoutingForHeadroom`.
- `rig/rehearse/` — `DryRun` path: validate via `/admin/api/config/validate` without apply; probe new model at 50K tok.
- `rig/apply/` — `validate+apply` hot-reload + `Show-Toast`.
- `rig/verify/` — re-`GET /health`, re-`GET provider_status`, and a `POST /v1/messages` ping on touched provider.
- `rig/learn/` — append to `watchdog-state.json` (`BenchmarkScores`, `CatalogHash`, `TokenLevelNotified`) and `rig/research/manifest.json`.

**6.2 Authority:**
- `ecc ito find` style: watchdog never reserves paid capacity, never creates accounts, never bypasses limits. It only reorders using *already-authorized* free pools.

**6.3 ANON taxonomy (open-ended):**
Every error not in the matrix is tagged `anon:<hash>` with `cause_types` from `server.log` (`HTTPStatusError`, `PermissionDeniedError`, etc.) and handled generatively: isolate provider, demote in headroom, try next fallback, toast `anomaly auto-handled (anon:xxx) — will re-heal next cycle`. No escalation by default; after 3 consecutive anon failures on same provider, mark `PendingKeys[prov]=true` and surface the same paste-panel flow — user just pastes a fresh key, same UX.

## Status
- Specified: layers, routing, anomaly matrix, guardrails, meta-engine §6
- Scaffolded: `rig/` skeleton pending (detect/triage/plan modules)
- Pending: owner approval; then Design Brief
