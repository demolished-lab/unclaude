# PRD — Claude Rig

**Status:** Draft · awaiting owner approval (OQ-1..OQ-5)
**Owner:** Raja
**References:** README.md · BLUEPRINT.md · DESIGN-BRIEF.md · SECURITY-AUDIT.md

> **Locked scope:** Ship a MIT GitHub repo that, with one terminal command, gives any Windows/macOS/Linux user a feels-unlimited Claude Code: auto-detects machine, bootstraps a local gateway aggregating 6+ free provider pools behind one key, quota-aware headroom routing with local Ollama floor, OS toast + one-click browser + paste-panel for any key/model anomaly, and a <2% background research lane that dynamically fetches token-optimized intel across the internet without dazing output quality. Fully-free by default; paid keys are strictly opt-in. Max power, zero effort, no quality compromise — every anomaly class (including unknown ones via ANON taxonomy) is handled generatively.

## 1. Problem statement

Claude Code is powerful but quota-gated: single-provider free tiers exhaust mid-day on agentic workloads (30–50K tokens per turn, 100–300K/hr). Users juggle 5–10 provider dashboards, manually rotate keys, and hit 401/402/403/413/429 walls with no guidance. Existing gateways (FCC, OmniRoute, freellmapi) solve aggregation but still require manual key/model babysitting, don't adapt to device headroom (8GB laptop vs 64GB workstation), don't self-heal when free lists churn, and waste tokens on verbose tool output. The result: power is paywalled or high-friction.

## 2. Target user + personas

- **Primary: Solo builder / indie hacker** (you). Wants to ship, not babysit quotas. Windows 11 primary, but repo must work on macOS/Linux/WSL. Values free-first, will optionally paste a paid key if it unlocks headroom.
- **Persona B: Student on 8GB laptop** — needs smallest local model, aggressive compression, survives on free pools only.
- **Persona C: Team lead on 32GB+ workstation** — wants to share the rig; needs larger local model, higher daily budget, team-wide watch.

Out of scope for MVP: enterprise SSO, multi-seat billing, air-gapped government.

## 3. Goals and non-goals

**Goals (MVP)**
- One-command install → `claude` just works on fresh Windows 11 / macOS 14+ / Ubuntu 22.04+ without touching `claude.ai`.
- Feels unlimited for solo daily use: 6+ free pools + headroom-aware routing + local floor; survives a provider's free-list churn or key death without manual search.
- Effortless anomaly UX: toast at corner → *Open key page* (already logged in) → paste → Enter.
- Token discipline: background research ≤2% of session tokens; RTK + Caveman on by default.
- Device-adaptive: RAM/disk/OS → budget + local model choice.

**Non-goals (MVP)**
- Multi-account farming, scraping that violates ToS, crypto, faking human. Hard ban.
- Replacing Claude Code's UX; we are the routing/compression/discipline layer *under* it.
- Paid-only features; paid keys never required.

## 4. User stories

- US-1: As a fresh user, I run `irm ... | iex` and, after at most 3 paste-panel approvals, `claude -p "build X"` works.
- US-2: As a daily user, I never think about which free provider is live; fallbacks happen silently and re-ascend after daily reset.
- US-3: When my Gemini key dies at 3pm, a toast pops, I click *Open*, paste a new key, hit Enter, and the same `claude` session continues — no restart hunt.
- US-4: When `cloudflare/gpt-oss-120b` is deprecated overnight, my next session auto-heals to `gpt-oss-20b` and I get a *Routing self-healed* toast.
- US-5: As an 8GB laptop user, the installer picks `llama3.2:1b` local fallback, not `qwen3-14B`, and warns if C: <15GB.

## 5. Feature list

**MVP**
- F-1 One-command installer (`install.ps1`/`install.sh`) — device detect → FCC `uv` bootstrap → gateway + `fcc-desktop` + shim.
- F-2 Provider pool — 6 verified free: Gemini, NIM, Groq, Cloudflare, OpenRouter `:free`, Ollama Cloud; optional Cerebras/GitHub Models on user opt-in.
- F-3 Model catalog — hashed `/v1/models`, normalized slugs, nightly refresh.
- F-4 Best-free picker — per-provider preference regex, verified by `413`-aware probe at 50K-token size.
- F-5 Routing — tier primaries (`MODEL_FABLE/OPUS/SONNET/HAIKU`) + `MODEL_FALLBACKS` reordered by headroom% + latency.
- F-6 Local infinite floor — `ollama/llama3.2:1b` (or `qwen2.5:0.5b` on <12GB) as pinned last fallback, auto-starts `ollama serve` if needed.
- F-7 Watchdog — 10-min cycle: gateway health, broken-key detection, catalog heal, headroom reorder, token alarm, disk guard, self-update daily.
- F-8 Key wizard — toast + WPF/zenity dialog with *Open key page* → validate pattern → `validate+apply` hot-reload.
- F-9 Background research lane — <2% token budget, dynamic internet fetch for token-optimized routes/data.
- F-10 Compression — RTK global hook + Caveman plugin, on by default.

**v2**
- F-11 OAuth device-code for Kimi/Qwen (hands-free, no paste).
- F-12 TUI mirror of toasts inside Claude Code status line.
- F-13 Team share: export/import `~/.fcc/.env` (encrypted) + `watchdog-state.json`.

**Later**
- Air-gapped local-only mode, enterprise proxy.

## 6. Detailed functional requirements

### F-1 Installer
- **FR-1.1** One-command install completes on fresh Windows 11 (PS 5.1), macOS 14 (zsh), Ubuntu 22.04 (bash) without manual `claude.ai` steps. **AC:** `install.ps1 -DryRun` prints plan; real run ends with `fcc-server --version` + `health 200`. **⚠** Must not overwrite existing `~/.claude/settings.json` without backup.
- **FR-1.2** Device detection sets `TokenBudgetDaily` and local model choice. **AC:** 8–12GB RAM → 1.5M budget + `qwen2.5:0.5b`; 16GB → 2M + `llama3.2:1b`; 32GB+ → 2.5M + `qwen3:8b`. Disk: E: VHDX growth check, C: warn <15GB.
- **FR-1.3** Shim `function claude` in `$PROFILE` auto-starts gateway if down and routes to `fcc-claude`; `claude.exe` bypasses. **AC:** `Get-Command claude` → Function after install.

### F-2/3/4 Catalog
- **FR-2.1** `GET /v1/models` normalized (strip `anthropic/` prefix) and hashed (SHA256 of sorted slugs). **AC:** hash stored in `watchdog-state.json`; change triggers heal.
- **FR-4.1** Per-provider `ModelPrefs` regex picks best free model; probe at 50K-token size must pass (`200`), not `413`. **AC:** `cf_bigcontext` probe suite passes for every `MODEL_FALLBACKS` entry.

### F-5 Routing
- **FR-5.1** Tier mapping: `claude-opus-*`→`MODEL_OPUS`, `claude-sonnet-*`→`MODEL_SONNET`, etc., else `MODEL`. **AC:** `POST /v1/messages` with `model: claude-sonnet-4-...` hits primary (verified via `generativelanguage.googleapis.com` in logs).
- **FR-5.2** `MODEL_FALLBACKS` is comma-separated, headroom-sorted (desc `LeftPct`, tie-break latency), but `ollama/*` always pinned last. Reorder only when `bestPct - worstPct >= 25`. **AC:** dry-run logs reorder plan, real apply shows toast.
- **FR-5.3** Headroom: `avgTokensPerRequest = tokensToday / requestsToday` (from `~/.claude/projects/*.jsonl` + `server.log` tail 400), `used = reqs * avg`, `LeftPct = 100*(limit-used)/limit`. Limits in `ProviderDailyLimits` (Gemini 1M, NIM 800K, Groq 500K, Cloudflare 600K, OpenRouter 400K, Ollama Cloud 500K). **⚠** Heuristic; must not reorder on noise.
- **FR-5.4** Local floor `ollama/llama3.2:1b` verified at 50K-token size; `ollama serve` auto-started if `11434` down.

### F-7 Watchdog
- **FR-7.1** Cycle every 600s (configurable), single-instance mutex `Global\FCC-Watchdog-Mutex`, autostart via `Startup/FCC-Watchdog.lnk` (no admin `schtasks`).
- **FR-7.2** Broken-key detection: `provider_status` in `missing_key/error/unauthorized` → `Start-KeyRotation` (toast + browser + dialog). **AC:** DryRun prints `would rotate for X`.
- **FR-7.3** Catalog heal: if slug in routing missing from catalog, replace with `Find-BestModel` (respecting prefs, not already in use). **AC:** toast `Routing self-healed: prov: old -> new`.
- **FR-7.4** Token alarm: `Get-TokensToday` sums `usage.input_tokens+output_tokens` for today; toast at 80% and 100% of `TokenBudgetDaily`.
- **FR-7.5** Disk guard: `Get-PSDrive C,E` free <15GB → toast; C: <12GB → prune `%TEMP%` >7 days.
- **FR-7.6** Benchmark: nightly 03:00 probe of 7 best models (20 tok `ping`, 30s timeout) → `BenchmarkScores` ms map.
- **FR-7.7** Self-update: daily `GET api.github.com/repos/.../releases/latest` vs `fcc-server --version`; toast if behind.

### F-8 Key wizard
- **FR-8.1** Toast `Provider needs attention` + WPF (Windows) / zenity (Linux) / AppleScript (macOS) dialog: *Open key page* button → `Start-Process $url` (user already logged in), `TextBox` with pattern validation (`^nvapi-`, `^gsk_`, `^sk-or-`, `^AQ\.`), *Save & Apply* → `validate+apply` hot-reload. **AC:** invalid pattern shows MessageBox and blocks save.
- **FR-8.2** Pending keys re-asked next cycle until fixed; `DryRun` never opens dialog.

### F-9 Background research
- **FR-9.1** ≤2% of session tokens (enforced: `researchTokens / sessionTokens < 0.02`). **AC:** logged per session; violation → throttle next cycle.
- **FR-9.2** Dynamic internet fetch: every N sessions, fetch token-optimization intel (provider docs, model catalogs, RTK/Caveman release notes) via `webfetch`/FCC itself; ranking is live, not hard-coded. **AC:** `rig/research/manifest.json` updated with source URLs and timestamps.
- **FR-9.3** Quality never dazes: research runs as sidecar subagent, not in main context; output is a compact `rig/research/brief.md` (≤1K tokens) injected only as `CLAUDE.md` appendix. **⚠** Must not inject into active turn's context window.

### F-10 Compression
- **FR-10.1** RTK 0.44.2 SHA-pinned install to `~/.local/bin`, `rtk init --global --auto-patch`, `CLAUDE.md` refs `@RTK.md`. **AC:** `rtk --version` + `settings.json` hook present after install.

### Cross-cutting
- **FR-11.1** Fully-free default; paid keys are `nullable` and never required. **⚠** No dark pattern nudging to paid.
- **FR-11.2** `DryRun` flag prints plan for every mutating operation.

## 7. Data model sketch

- `~/.fcc/.env` (managed, `FCC_CONFIG_SCHEMA=1`): `MODEL*`, `*_API_KEY`, `CLOUDFLARE_ACCOUNT_ID` (encrypted at rest by FCC).
- `~/.fcc/watchdog-state.json`: `{ CatalogHash, PendingKeys{}, TokenLevelNotified, OutageNotified, BenchmarkScores{}, LastBenchmark, LastUpdateCheck, LatestRelease }`.
- `~/.claude/projects/**/*.jsonl`: source of truth for token counts (per `usage`).
- `~/.fcc/logs/server.log`: JSON lines, provider URL → headroom estimation.

## 8. Edge cases

- Free list churn overnight → heal replaces dead slug at next 10-min cycle; in-flight request may 404 once before heal.
- 429 burst → retries (5) then fallback; headroom reorder demotes spiking provider next cycle.
- 413 payload too large → model excluded from `ModelPrefs`; probe suite would have caught it pre-routing.
- Disk E: missing after reboot (VHDX not mounted) → `E:` check fails silently; local floor degrades to remote-only, toast `E: not mounted`.
- User clicks *Later* on key dialog → `PendingKeys[prov]=true`, re-asked next cycle.
- Offline → gateway health fails → toast `gateway DOWN`, no busy-loop.

## 9. Success metrics

- Install success: fresh VM, one command → `claude -p "hi"` via FCC in <5 min, ≤3 paste approvals.
- Feels unlimited: 8-hour agentic day on free pools without manual intervention (fallback chain absorbs ≥2 provider exhaustions).
- Token discipline: research ≤2% of session tokens (p50), RTK+Caveman cut ≥60% vs baseline (measured by `rtk gain` + before/after).
- Heal latency: dead model replaced within 1 cycle (≤10 min) of catalog change.
- Device adapt: 8GB laptop picks ≤2GB local model; 32GB picks ≥8B; C: warn fires before <10GB.

## 10. Open questions

- OQ-1: Daily budget — fixed 2M or RAM-scaled +20%/8GB? **Rec:** RAM-scaled (spec'd in FR-1.2).
- OQ-2: Provider limits — hard-coded vs live probe? **Rec:** hard-coded + benchmark tie-breaker.
- OQ-3: Telemetry opt-in to improve free-model ranking? **Rec:** off, consent-gated, v2.
- OQ-4: Air-gapped local-only mode? **Rec:** v2.
- OQ-5: Also mirror toasts inside Claude TUI? **Rec:** OS primary, TUI mirror v2.

## Status
- Specified: this PRD (FR-1.1..FR-11.2) + success metrics
- Scaffolded: `rig/` skeleton pending
- Pending: owner approval of OQ-1..OQ-5; then Blueprint
