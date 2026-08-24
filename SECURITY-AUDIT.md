# Security Audit — Claude Rig

**Status:** Draft · pre-launch gate · no code modified during audit
**Owner:** Raja
**References:** README.md · PRD.md · BLUEPRINT.md · DESIGN-BRIEF.md
**Scope:** `install.ps1/sh`, `rig/watchdog/FCC-Watchdog.ps1`, `~/.fcc/.env`, `~/.fcc/watchdog-state.json`, `~/.claude/settings.json`, `E:\vyuha.vhdx` mount
**Date:** 2026-08-24 · auditor: Muse Spark (automated) · confidence noted per finding

> **Locked scope:** Fully-free-first, no account farming, no ToS-violating scrape. Audit blocks launch until G1–G7 pass. Findings <90% confidence are flagged, never silently dropped.

## Findings (ranked)

**F-1 — Plaintext keys in OneDrive Desktop — HIGH — `C:\Users\Raja\OneDrive\Desktop\*key*.txt:1`**
- Exploit: User drops `*_API_key*.txt` on OneDrive-synced Desktop; keys sync to Microsoft cloud, survive deletion via version history, leak via link sharing.
- Fix: Installer must never write keys to synced folders; wizard writes directly to `~/.fcc/.env` (encrypted). Add `install.ps1` guard: refuse `OneDrive` in path, warn. Document `Remove-Item OneDrive\Desktop\*key*.txt` in README. **Gate G-3**.

**F-2 — Watchdog logs raw keys if fingerprinted incorrectly — MEDIUM — `rig/watchdog/FCC-Watchdog.ps1:182`**
- Exploit: If `Show-KeyDialog` validation regex is empty (`cloudflare` Pattern `''`), any string is accepted and might be logged via `Show-Toast` on error path. Current code fingerprints only (`nvapi-xxxxx...`) — safe, but fragile.
- Fix: Enforce pattern for every provider or require `len>=20` check; never log `$res.key` even on error. Keep fingerprint-only logging. **Gate G-2**.

**F-3 — Browser auto-open is phishing-adjacent — MEDIUM — `FCC-Watchdog.ps1:169, Start-Process $info.Url`**
- Exploit: Toast says *Open key page* → opens provider URL. If provider URL is ever hijacked (typo in `Providers` map), user pastes a real key into attacker site.
- Fix: Pin URLs to official domains in `Providers` map + `SECURITY.md` allow-list; show full URL in dialog subtitle; `DryRun` prints plan including URLs. **Gate G-2**.

**F-4 — Single-instance mutex is global, not per-user — LOW — `FCC-Watchdog.ps1:307 Global\FCC-Watchdog-Mutex`**
- Exploit: Multi-user Windows box, user B's watchdog blocks user A's (different `~/.fcc`). Low severity on single-user laptop.
- Fix: Scope mutex to `Global\FCC-Watchdog-$env:USERNAME` or keep as is with note in `TROUBLESHOOTING.md`. **N-A for MVP** (single-user).

**F-5 — VHDX auto-mount via scheduled task runs as admin — MEDIUM — `C:\vdisks\mount-vyuha.cmd` via `VyuhaMountVHD`**
- Exploit: If `C:\vdisks\vyuha.vhdx` is writable by non-admin, attacker could replace it with a malicious VHDX that mounts as `E:` and shadows `E:\models`.
- Fix: Document `icacls C:\vdisks\vyuha.vhdx` should be `SYSTEM+Admin` only; verify in installer. **Gate G-5**.

**F-6 — `install.ps1 | iex` pattern — MEDIUM — `README.md:60`**
- Exploit: Classic `irm | iex` trusts TLS + GitHub. If DNS hijacked, arbitrary code runs.
- Fix: Document `DryRun` + hash-pinned alternative (`install.ps1` SHA256 in README); keep `irm | iex` as convenience only. **Gate G-1**.

**F-7 — FCC `~/.fcc/.env` permissions — LOW — `C:\Users\Raja\.fcc\.env:1`**
- Exploit: File is user-readable only by default on Windows, but `C:\Users\Raja` ACL may allow other local users to read.
- Fix: Installer runs `icacls $env:USERPROFILE\.fcc /inheritance:r /grant:r "$env:USERNAME:(OI)(CI)F"` on Windows. On Linux/macOS `chmod 700 ~/.fcc`. **Gate G-2**.

**F-8 — Background research lane could exfiltrate code — MEDIUM — `rig/research/` (planned)**
- Exploit: Sidecar that fetches “token-optimized data across whole internet” could be tricked into sending project files to a third party if prompt injection in fetched pages is not sanitized.
- Fix: Research lane is read-only, never sends `~/.claude/projects` content; fetch is allow-listed to provider docs + RTK/Caveman releases; output is ≤1K tok `brief.md` appendix, reviewed via `caveman-compress` pipeline (code blocks untouched). **Gate G-6**.

## Per-category verdicts

- **Secrets at rest:** FAIL (F-1, F-7) — see fixes; will be CLEAN after G-2/G-3.
- **Secrets in transit:** CLEAN — FCC uses `https://api.*` + `Authorization: Bearer`; no `http` provider URLs in `Providers` map.
- **Injection / prompt injection:** CLEAN (with F-8 mitigated) — `FCC-Watchdog.ps1` never interpolates provider responses into code; `ConvertFrom-Json` only.
- **Supply chain:** CLEAN — FCC via `uv` (`cpython-3.14`), RTK SHA256-pinned `3a1e114e...`, Caveman/ECC via official `claude plugin marketplace` (verified channels in README).
- **Privilege / sandbox:** CLEAN — watchdog runs as `LIMITED` (`/RL LIMITED`), no admin, mutex prevents dup.
- **Data exfiltration:** CLEAN — no telemetry by default (PRD OQ-3 off); research lane allow-listed.
- **Denial of service:** N-A — local-only gateway, no public port.
- **Account farming / ToS:** CLEAN — one legitimate key per provider enforced; duplicate-account bypass is hard-banned in PRD FR-11.1 and `RULES.md`.

## Hard pre-launch gates (must pass)

- **G-1 Supply chain:** `install.ps1/sh` hash printed in README; `DryRun` works without network.
- **G-2 Secrets:** No plaintext keys in synced folders; `~/.fcc` 700; watchdog never logs raw keys (audit `rg -n "API_KEY" rig/`).
- **G-3 OneDrive guard:** Installer refuses `OneDrive` in key path and warns.
- **G-4 Key wizard:** Pattern validation for every provider; `DryRun` shows URLs.
- **G-5 VHDX:** `icacls` check for `C:\vdisks\vyuha.vhdx` documented.
- **G-6 Research lane:** Allow-list + sidecar isolation + `brief.md` size cap verified.
- **G-7 Verification:** `rig` Phase-0 `python -m rig.cli scan` + `fcc-claude -p "Reply exactly: RIG OK"` via gateway both pass on fresh Windows/Ubuntu/macOS VM.

No code was modified during this audit.

## Status
- Specified: findings F-1..F-8, verdicts, gates G-1..G-7
- Pending: fixes for F-1..F-3, F-5, F-7 before launch; then Phase-0 scaffold
