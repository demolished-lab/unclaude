# System Design — UnClaude

> For contributors who want to understand *why* it works, not just *how* to install.

## 1. Problem Deconstruction

Single-provider free tiers are quota-gated by design: Gemini ~250 req/day, Groq ~30 RPM, Cloudflare 10K neurons/day, OpenRouter `:free` ~50 req/day. Agentic Claude Code burns 30-50K tokens per turn (system + tools + history). A single pool exhausts mid-day. Manual key rotation is high-friction and error-prone (401/402/403/413/429).

UnClaude treats free tiers as a **distributed, headroom-aware OS** — not a list.

## 2. Architecture Choices (ADRs)

**ADR-1: Gateway, not proxy.** Use FCC's Anthropic-compatible `/v1/messages` so Claude Code thinks it's talking to Anthropic. No client patch, no `claude` fork.

**ADR-2: Headroom, not round-robin.** Round-robin spreads load but ignores that Gemini's daily pool is 10× OpenRouter's. Headroom (`LeftPct`) burns deepest first, re-ascends after reset — optimal for longevity.

**ADR-3: Pin local last.** Local `ollama` has infinite quota but weak quality. Sorting it by headroom would put it first (100% left). Pinning last preserves quality while guaranteeing a floor.

**ADR-4: Sidecar, not inline.** Research lane as `SessionStart` hook, not main-turn tool, so it never steals context. Budget hard-capped <2%.

**ADR-5: Probe, don't trust.** Provider catalog lies: `llama-3.3-fp8-fast` is listed but 413s at 50K tokens. Probe every fallback at 209KB prompt before routing.

## 3. Data Flow (Pipely)

```
User: claude -p "fix auth bug"
  → Shim checks GET /health (2s timeout) → if down, Start-Process fcc-desktop, poll 40×500ms
  → fcc-claude sets ANTHROPIC_BASE_URL=127.0.0.1:8082, ANTHROPIC_AUTH_TOKEN=freecc
  → RTK PreToolUse hook compresses Bash output (filters.toml)
  → Caveman skill rewrites reply in terse style (65% fewer tokens)
  → ECC skill injects TDD/review loop
  → FCC: tier map (claude-sonnet-*) → MODEL_SONNET (gemini-3.7-flash)
  → FCC: try primary → if 429, fallback chain (headroom-sorted) → local
  → Watchdog (10 min): hash /v1/models → heal dead slugs → re-sort by headroom+latency → toast
  → Research sidecar (SessionStart, <2%): fetch 4 GitHub releases → brief.md → CLAUDE.md appendix
```

Each stage is pipely: small, testable, DryRun-verifiable.

## 4. Headroom Math

```python
avgTok = tokensToday / requestsToday  # from ~/.claude/projects/*.jsonl + server.log tail
used = reqs[provider] * avgTok
LeftPct = 100 * (limit - used) / limit
# limits: gemini 1M, nvidia 800K, cloudflare 600K, groq 500K, open_router 400K, ollama_cloud 500K
# reorder only when bestPct - worstPct >= 25 → no thrash
```

Why not exact per-provider token counters? FCC doesn't expose them; we derive from transcripts (exact) + log request counts (exact), so `used` is ~95% accurate. Good enough for routing, not for billing.

## 5. Local Floor Design

`ollama/llama3.2:1b` (1.3GB) chosen for 16GB RAM box. Verified at 50K tokens via FCC (`FINAL OK`). Larger `qwen3:8b` (5.2GB) for 32GB+ workstations. `ollama serve` auto-started if `11434` down, with 90s cold-start tolerance.

## 6. Failure Modes & Recovery

See `BLUEPRINT.md §4` anomaly matrix. Every class has a detector (watchdog) and healer (reorder/paste-panel). Unknown `ANON` errors are tagged `anon:<hash>` and demoted, never escalated by default.

## 7. Trade-offs

- **Free vs paid:** Free tiers are rate-limited and lower quality than Claude Opus. We accept quality whiplash on fallback for longevity.
- **Latency vs headroom:** Headroom sort primary, latency tie-break secondary — optimal for daily budget, not per-request speed.
- **Compression vs readability:** Caveman terse output saves 65% but is less prose-friendly; RTK is lossless for code/paths.

## 8. What Makes This Knowledge-Worthy

- Headroom-aware routing is a **scheduling problem** (like OS process scheduling), not just failover.
- Probe-verified catalog is **property-based testing** for free tiers.
- <2% sidecar is **budgeted background intelligence** — a pattern for any LLM system.
