---
name: ultimate-power
description: Background optimizer — thinks how to get ultimate free power source without hurting quality. Sidecar only, <2% of session tokens, never dazes main turn.
allowed-tools: Read, Write, Bash
---

# Ultimate Power — Background Optimizer

**Purpose:** Make Claude think, in background, how to get the ultimate free power source without dazing output quality. PRD locked scope: <2% of session tokens, sidecar only.

**When to use:** Every session, as a sidecar subagent. Never in the main turn's context.

**How it works:**
1. Sidecar reads `rig/research/brief.md` (compact, <=1K tokens) — not the full internet.
2. Thinks: "Given current free pools (Gemini, GROQ, Cloudflare, etc.), headroom, and device RAM/disk, what's the next cheapest free token source I can tap without hurting this task?"
3. Writes a one-line suggestion to `rig/research/suggestion.txt` (e.g., "Try ollama/qwen2.5:0.5b for this subtask — 3K tokens saved") — main agent may read it next turn if helpful, or ignore.

**Budget:** Hard cap <2% of session tokens. If session is 50K tokens, this skill gets <=1K. Exceeding throttles next cycle.

**Quality guard:** Output is never injected into the active turn's context window. It's an appendix to `CLAUDE.md`, read only at session start.

**Example prompt for the sidecar:**
> You are the power optimizer. Session tokens so far: {{tokens}}. Research brief: {{brief}}. Suggest one concrete free-tier optimization for the next subtask that saves tokens without hurting quality. Keep it under 30 words.

**Integration:** `rig/research/researcher.py` fetches the brief; this skill reasons over it.
