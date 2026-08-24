# Benchmarks — Real Numbers, Not Marketing

Measured on reference box: Ryzen 7 5700U, 16GB RAM, Windows 11, 2026-08-24. All via FCC `127.0.0.1:8082`.

## 1. Catalog

| Metric | Value |
|---|---|
| FCC `GET /v1/models` raw entries | 1,069 |
| Unique (strip `anthropic/` prefix) | 555 |
| Genuinely-free chat models | ~230 (Gemini 51 + NIM 102 + Cloudflare 25 + Groq 13 + Ollama Cloud 7 + OpenRouter 17 `:free` + local 8) |
| Total catalog (FCC docs claim) | 358 free endpoints (our live 555 includes aliases) |

## 2. 50K-Token Stress (209KB prompt, 50K tokens — real Claude Code size)

We sent a 209KB prompt (620× “The quick brown fox…”) via `POST /v1/messages` through FCC to every `MODEL_FALLBACKS` candidate:

| Model | Result | Note |
|---|---|---|
| `cloudflare/@cf/openai/gpt-oss-120b` | **PASS** | 131K ctx, our top fallback |
| `cloudflare/@cf/openai/gpt-oss-20b` | **PASS** | |
| `cloudflare/@cf/nvidia/nemotron-3-120b` | **PASS** | |
| `cloudflare/@cf/meta/llama-4-scout-17b` | **PASS** | 10M ctx |
| `cloudflare/@cf/zai-org/glm-4.7-flash` | **PASS** | |
| `cloudflare/@cf/deepseek-ai/deepseek-r1-distill-qwen-32b` | **PASS** | |
| `cloudflare/@cf/meta/llama-3.3-70b-fp8-fast` | **FAIL 413** | Too small for agentic — excluded |
| `cloudflare/@cf/qwen/qwq-32b` | **FAIL 413** | |
| `cloudflare/@cf/moonshotai/kimi-k2.7-code` | **FAIL 403** | Gated, not free |
| `ollama/llama3.2:1b` (local) | **PASS** | 90s cold, infinite floor |
| `ollama_cloud/nemotron-3-ultra` | **PASS** | 550B MoE |

Takeaway: **Probe, don't trust the catalog.** 30% of listed free models fail at agentic size.

## 3. Headroom Cycle

```
[22:06:36] cycle ok | broken= | tokens today=142980 (7%) | headroom best: nvidia_nim 100% (0 reqs)
```

Reorder triggers only when `bestPct - worstPct >= 25` — no thrash when all at 100%.

## 4. Compression

| Tool | Input | Output | Saved |
|---|---|---|---|
| RTK (30-min session) | 118,000 tok | 23,900 tok | **80%** |
| Caveman (React debug, 2,847 tok) | 2,847 | 367 | **87%** |
| Caveman (avg, 50 tasks) | — | — | **65%** |
| Combined | — | — | **~3-5×** free tokens/day |

## 5. Install

| Command | Time | Network |
|---|---|---|
| `install.ps1 -DryRun` | ~2 sec | No |
| `install.sh --dry-run` | ~1 sec | No |
| `rig/cli.py scan --dry-run` | <1 sec | No |
| `watchdog --once --dry-run` | ~2 sec | Yes (FCC health) |

## 6. Comparison

|  | UnClaude | Free Claude Code | OmniRoute | freellmapi |
|---|---|---|---|---|
| One-command | ✅ | ✅ | ✅ | ✅ |
| Headroom-aware | ✅ (LeftPct+latency) | ❌ static | ✅ 17 strategies | ❌ static |
| Local floor | ✅ pinned last, probe-verified | ❌ | ❌ | ❌ |
| <2% research sidecar | ✅ | ❌ | ❌ | ❌ |
| Toast+paste wizard | ✅ OS corner, one paste | Dashboard only | Dashboard only | Dashboard only |
| Probe-verified | ✅ 50K stress | ❌ | ❌ | ❌ |

Run it yourself: `python rig/research/researcher.py && cat rig/research/brief.md`
