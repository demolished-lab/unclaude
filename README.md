# UnClaude — One Command, Unlimited Claude

> Free pools, headroom routing, local fallback. No `claude.ai` billing. Just `claude`.

[![CI](https://github.com/demolished-lab/unclaude/actions/workflows/ci.yml/badge.svg)](https://github.com/demolished-lab/unclaude/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#install)

**UnClaude** gives you a *feels-unlimited* Claude Code without touching `claude.ai` billing. One command auto-detects your machine (OS/RAM/disk), bootstraps a local gateway that aggregates 6+ free provider pools behind one key, and routes with quota-aware headroom. When a free tier dies, a toast pops at your corner — click *Open key page* (already logged in), paste, hit Enter. Done. A `qwen2.5:0.5b` local model catches you when the internet pools thin. Background research spends <2% of session tokens to keep routes optimal.

Inspired by [Free Claude Code](https://github.com/Alishahryar1/free-claude-code), [RTK](https://github.com/rtk-ai/rtk), [Caveman](https://github.com/JuliusBrussee/caveman) and [ECC](https://github.com/affaan-m/ECC) — but fully autonomous for any device.

---

## 60-Second Start

**Windows (PowerShell)**
```powershell
irm https://raw.githubusercontent.com/demolished-lab/unclaude/main/install.ps1 | iex
```

**macOS / Linux / WSL**
```bash
curl -fsSL https://raw.githubusercontent.com/demolished-lab/unclaude/main/install.sh | bash
```

Then just:
```bash
claude              # your rig — 6 free pools + local fallback
claude.exe          # bypass — direct Anthropic
```

If a key is needed, a corner toast appears → **Open key page** → paste → **Enter**. No docs hunting.

---

## What You Get

| Layer | What | Why |
|---|---|---|
| **Gateway** | FCC 5.13.10 at `127.0.0.1:8082` | One local key for 6 pools |
| **Providers** | Gemini · NVIDIA NIM · Groq · Cloudflare AI · OpenRouter `:free` · Ollama Cloud + local `ollama` | ~230 genuinely-free chat models, 555 total catalog |
| **Routing** | Tier primaries (`MODEL_FABLE/OPUS/SONNET/HAIKU`) → fallback chain reordered by headroom% + latency | Burns deepest pools first, re-ascends after daily reset |
| **Floor** | `ollama/llama3.2:1b` (1.3GB, 16GB RAM) — device-scaled | Infinite when remote pools thin |
| **Compression** | RTK (input, ~80%) + Caveman (output, ~65%) | 3-5x more free tokens per day |
| **Discipline** | ECC 2.2.0 — 68 agents, 286 skills | TDD/review/planning loops |
| **Watchdog** | 10-min cycle, headroom-aware, catalog heal | Toast + paste-panel, disk guard, token alarm |

---

## Architecture

```mermaid
flowchart TD
    U[claude in terminal] --> S[shim: health probe → fcc-claude]
    S --> C[RTK + Caveman + ECC]
    C --> G[FCC 127.0.0.1:8082 /v1/messages]
    G --> R{Headroom Router}
    R -->|tier primary| P1[Gemini 3.7]
    R -->|fallback 1| P2[Cloudflare gpt-oss-120b]
    R -->|fallback 2| P3[Ollama Ultra]
    R -->|fallback 3| P4[Groq gpt-oss-120b]
    R -->|fallback 4| P5[OpenRouter GLM-5.2:free]
    R -->|fallback 5| P6[NIM Nemotron]
    R -->|floor| P7[ollama/llama3.2:1b local]
    W[Watchdog 10min] -.-> R
    W -.->|toast+dialog| U
    B[Research sidecar <2%] -.->|brief.md| R
```

---

## Device Adaptive

| RAM | Daily budget | Local model |
|---|---|---|
| 8-12 GB | 1.5M tokens | `qwen2.5:0.5b` (397 MB) |
| 16 GB | 2.0M | `llama3.2:1b` (1.3 GB) |
| 32 GB+ | 2.5M | `qwen3:8b` (5.2 GB) |

Disk guard warns at <15 GB free (C: 25GB / E: 18GB on reference box).

---

## Unique Techniques (Why This Is Different)

UnClaude isn't just another gateway — it's a **headroom-aware pipely system** that treats free tiers as a distributed OS.

| # | Technique | What Others Do | What We Do | Benefit |
|---|---|---|---|---|
| **1** | **Headroom-Aware Routing** | Static fallback chain (`if 429 then next`) | Reorders `MODEL_FALLBACKS` every 10 min by `LeftPct = 100*(limit-used)/limit` + latency tie-break; pinned `ollama/*` last | Burns deepest pools first, never thrashes when all at 100% |
| **2** | **Local Pinning** | Local model treated as equal peer | `ollama/llama3.2:1b` pinned last, verified at 50K-token probe (many CF models fail at 413) | Infinite floor that *actually* digests Claude Code's 30-50K prompt |
| **3** | **<2% Research Sidecar** | Pollutes main context with “fetch the internet” | `SessionStart` hook → `rig/research/researcher.py` → `brief.md` (≤1K tok) as `CLAUDE.md` appendix, never in active turn | Token-optimized intel without dazing quality |
| **4** | **Probe-Verified Catalog** | Trust provider's model list | Stress test every `MODEL_FALLBACKS` entry at 50K tokens (209KB prompt) before routing; `llama-3.3-fp8-fast` failed at 413, `gpt-oss-120b` passed | No 413 surprises mid-session |
| **5** | **Device-Adaptive Budget** | Fixed 2M/day | `detect/device.py` → RAM/disk → 1.5M/2M/2.5M + `qwen2.5:0.5b`/`llama3.2:1b`/`qwen3:8b` | 8GB laptop and 32GB workstation both feel unlimited |
| **6** | **Toast+Paste Wizard** | Paste key into dashboard, hunt for URL | Corner toast → *Open key page* (already logged in) → paste-panel with pattern validation (`^gsk_`, `^nvapi-`) → hot-reload | Zero docs hunting, one paste |

Full deep dive: [`docs/SYSTEM_DESIGN.md`](docs/SYSTEM_DESIGN.md) · Pipeline: [`docs/PIPELINE.md`](docs/PIPELINE.md)

---

## Pipely — The Pipeline That Makes It Effortless

```
Terminal `claude` 
  → Shim (health probe → fcc-claude) 
  → RTK hook (compress tool output ~80%) 
  → Caveman (compress reply ~65%) 
  → ECC (TDD/review loops) 
  → FCC Gateway (127.0.0.1:8082) 
  → Headroom Router (tier + fallback) 
  → 6 Remote Pools + 1 Local
  → Watchdog (heal, alarm, disk) ←→ Research Sidecar (<2%)
```

Every layer is **pipely**: small, composable, verified. See [`docs/PIPELINE.md`](docs/PIPELINE.md) for per-stage latency/cost.

---

## Benchmarks (Real, Not Marketing)

Measured on reference box (Ryzen 7 5700U, 16GB, 2026-08-24):

| Probe | Result |
|---|---|
| FCC catalog | 1,069 entries → 555 unique (230 genuinely-free chat) |
| 50K-token stress (209KB prompt) | `gpt-oss-120b` ✅, `nemotron-3-120b` ✅, `llama-4-scout` ✅, `llama-3.3-fp8-fast` ❌ 413, `qwq-32b` ❌ 413 |
| Headroom cycle | `cycle ok \| broken= \| tokens today 0 (0%)` — reorders only when gap >25% |
| Compression | RTK `118K → 23K` (-80%) + Caveman `2,847 → 367` (-87%) on React debug → ~3-5× free tokens/day |
| Install | `install.ps1 -DryRun` → 2 sec, `install.sh --dry-run` → 1 sec |

Full suite: [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md)

---

## Docs

| Doc | Governs |
|---|---|
| [PRD.md](PRD.md) | What we ship (FR-1.1..FR-11.2) |
| [BLUEPRINT.md](BLUEPRINT.md) | How it's wired (routing, anomaly matrix, meta-engine) |
| [DESIGN-BRIEF.md](DESIGN-BRIEF.md) | How it looks (tokens, S-1..S-7, flows) |
| [SECURITY-AUDIT.md](SECURITY-AUDIT.md) | Gates G-1..G-7 (must pass before release) |
| [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) | Deep dive — ADRs, headroom math, trade-offs |
| [docs/PIPELINE.md](docs/PIPELINE.md) | Pipely — per-stage latency/cost, DryRun-verifiable |
| [docs/BENCHMARKS.md](docs/BENCHMARKS.md) | Real numbers — 50K stress, catalog, compression |
| [rig/](rig/) | Scaffold + watchdog + research sidecar |

---

## Verify

```bash
python -m rig.cli scan --dry-run
python -m rig.watchdog.watchdog --once --dry-run
python rig/detect/device.py
```

Dashboard: `http://127.0.0.1:8082/admin` — see which provider actually served.

---

## License

MIT — see [LICENSE](LICENSE). Provider ToS respected, no account farming.

## Acknowledgments

Built on [Free Claude Code](https://github.com/Alishahryar1/free-claude-code), [RTK](https://github.com/rtk-ai/rtk), [Caveman](https://github.com/JuliusBrussee/caveman), [ECC](https://github.com/affaan-m/ECC). Maintained by [demolished-lab](https://github.com/demolished-lab).
