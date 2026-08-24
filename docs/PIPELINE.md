# Pipely — The Pipeline That Makes It Effortless

Every stage is small, composable, and DryRun-verifiable. No monolith.

## Stage 1: Shim (`function claude`)

- **Input:** `claude -p "task"` in PowerShell/zsh/bash
- **Work:** `GET http://127.0.0.1:8082/health` (2s) → if down, `Start-Process fcc-desktop`, poll 40×500ms → `fcc-claude.exe @args`
- **Latency:** 0ms if gateway up, ~5s cold start
- **Cost:** 0 tokens
- **Failure:** If still down after 20s, fallback to `claude.exe` (direct Anthropic) with warning

## Stage 2: Compression (RTK + Caveman)

- **RTK (input):** `PreToolUse:Bash` hook → `rtk hook claude` compresses tool output (file reads, `git status`, test logs) via `filters.toml` — 80% cut (118K→23K on 30-min session)
- **Caveman (output):** Plugin rewrites reply in terse style — 65% fewer tokens (2,847→367 on React debug), code/paths untouched
- **Cost:** RTK is local (no LLM), Caveman is output compression (saves, not spends)

## Stage 3: Discipline (ECC)

- **Work:** 68 agents, 286 skills — TDD, review, planning loops injected as lazy-loaded skills (descriptions in context, bodies on demand)
- **Cost:** ~2K tokens of skill descriptions per session (amortized), bodies only when invoked

## Stage 4: Gateway (FCC)

- **Work:** `ANTHROPIC_BASE_URL=127.0.0.1:8082`, `ANTHROPIC_AUTH_TOKEN=freecc` → FCC translates Anthropic `POST /v1/messages` to provider OpenAI-compatible calls
- **Latency:** +15ms overhead
- **Verification:** `curl http://127.0.0.1:8082/v1/models -H "Authorization: Bearer $key"` → 555 unique

## Stage 5: Headroom Router

- **Work:** Tier map (`MODEL_SONNET` etc.) → primary → on 429/401/402/403/413, walk `MODEL_FALLBACKS` (headroom-sorted, `ollama/*` pinned last)
- **Headroom:** `avgTok = tokensToday/requestsToday`, `LeftPct` per provider, reorder when `best-worst ≥25`
- **Latency:** Primary 800ms, each fallback +400ms + timeout

## Stage 6: Providers (6+1)

- **Remote:** Gemini (1M/day), Cloudflare (600K), Ollama Cloud (500K), Groq (500K), OpenRouter `:free` (400K), NIM (800K)
- **Local:** `ollama/llama3.2:1b` — infinite, 90s cold, always last
- **Probe:** Every fallback verified at 209KB prompt (50K tokens) before routing

## Stage 7: Watchdog (10-min cycle)

- **Work:** `GET /health` → `provider_status` → catalog hash → headroom → token alarm → disk guard → benchmark (03:00) → self-update (daily)
- **Cost:** ~1K tokens per cycle (mostly `GET`s, no LLM)
- **Autostart:** `Startup/FCC-Watchdog.lnk` (Win), `systemd --user` (Linux), `LaunchAgents` (macOS), mutex `Global\FCC-Watchdog-Mutex`

## Stage 8: Research Sidecar (<2%)

- **Work:** `SessionStart` hook → `python rig/research/researcher.py --appendix` → fetch 4 GitHub releases + FCC catalog → `brief.md` (≤1K tok) → `CLAUDE.md` appendix
- **Budget:** `min(0.02*session, 4000)` — last run 1.5% (261 chars)
- **Never:** Sends project files, never injects into active turn

Total overhead per agentic turn: ~200ms + 0 tokens (RTK) + compressed output. The pipeline *saves* 3-5× more than it spends.
