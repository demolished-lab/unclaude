# Design Brief — Claude Rig

**Status:** Draft · awaiting owner approval
**Owner:** Raja
**References:** README.md · PRD.md · BLUEPRINT.md · SECURITY-AUDIT.md

> **Locked scope:** Same as PRD. Design Brief wins on UI when it conflicts with other docs.

One fact this design is built around: **effortlessness = one toast + one button + one paste.** Every pixel serves that.

## 1. Principles

- **Zero-search:** user never googles “where to get Groq key.” The rig opens the right page, already logged in.
- **One-hand:** toast at corner → *Open key page* → paste → Enter. No scrolling, no settings maze.
- **Calm, not flashy:** free-pool plumbing is invisible; only anomalies surface, and then briefly.
- **Headroom-honest:** show tokens left as a quiet ring, not a scary red bar.

## 2. Visual direction + explicit ban list

**Direction:** *Matte terminal + soft glass.* Dark charcoal (#0F1115) + cool slate, single accent electric blue (#2563EB) for *Open key page*, success green (#16A34A) for *Save*. No gradients, no 3D, no mascot. Type: JetBrains Mono for code/keys, Inter for UI. Inspired by Vercel's restraint + Linear's density, but for a developer's corner toast.

**Ban list (never):**
- No neon gamer, no skeuomorphic knobs, no mascot (no “caveman” art here — that belongs to output compression, not the wizard).
- No full-screen onboarding, no multi-step wizard that can't be dismissed.
- No dark pattern nudging to paid.
- No persistent overlay that blocks the terminal.

## 3. Tokens (color / type / spacing)

- **Color:** `bg #0F1115`, `surface #1A1D24`, `border #2A2E3A`, `text #E6E8EB`, `muted #8A8F98`, `accent #2563EB`, `success #16A34A`, `warn #F59E0B`, `danger #EF4444`.
- **Type:** Inter 13/14 for UI, JetBrains Mono 12 for keys/paths. Line height 1.4.
- **Spacing:** 8-pt grid. Card 16 pad, toast 12 pad, dialog 520×290 (as in `Show-KeyDialog` XAML), corner radius 10 (toast) / 12 (dialog).
- **Motion:** 120ms ease-out for toast slide-in from bottom-right; no bounce.

## 4. Screen inventory

- **S-1 Install terminal** — the one-command `irm/curl | bash` output + `DryRun` plan preview.
- **S-2 Gateway health dot** — tiny `●` in terminal prompt or `claude --version` footer (green = FCC 200, amber = fallback active, red = gateway down).
- **S-3 Toast (corner)** — Windows `ToastText02` / macOS `NSUserNotification` / Linux `notify-send`. Two lines: title + message, auto-dismiss 8s.
- **S-4 Key dialog (popup)** — WPF (Win) / zenity (Linux) / AppleScript (macOS) — 520×290, topmost. *Open key page* (blue), `TextBox` for key, *Later* + *Save & Apply* (green).
- **S-5 Token ring (alarm)** — thin circular progress in terminal status line or `claude /status` footer: 0–80% muted, 80–100% amber, 100% red + *pools reset tomorrow*.
- **S-6 Dashboard (optional)** — `http://127.0.0.1:8082/admin` (existing FCC) — not restyled in MVP; linked from toast via “Open dashboard.”
- **S-7 Post-install check** — `claude -p "Reply exactly: RIG OK"` → `RIG OK` in terse Caveman style; proves tier routing.

No other screens in MVP. No marketing site.

## 5. User flows

**Flow A: Fresh install (happy path)**
`install.ps1` → DryRun plan printed → user confirms → `uv` pulls FCC → `fcc-desktop` → health 200 → shim writes `$PROFILE` → toast *Rig ready. Try `claude -p "hi"`* → `claude` → tier primary (Gemini 3.7) replies.

**Flow B: Key dies mid-session**
`provider_status=unauthorized` → toast `Groq key needs attention` → dialog pops (topmost) → *Open key page* → browser (already logged in) → user creates key → copy → paste into dialog → *Save & Apply* → `validate+apply` hot-reload → toast `Routing restored` → same `claude` session continues (no restart).

**Flow C: Catalog churn**
Nightly hash mismatch → `Find-BestModel` picks next `ModelPrefs` hit → `validate+apply` → toast `Routing self-healed: cloudflare: old -> new`.

**Flow D: Budget alarm**
`Get-TokensToday` crosses 80% → toast `80% of today's budget used (1.6M)`; at 100% → `Daily token budget HIT. Lean on fallbacks; pools reset tomorrow.` + ring turns red.

**Flow E: Disk low**
`Get-PSDrive C` <15GB → toast `C: 12.3GB free`; <12GB → also prune `%TEMP%` >7 days.

## 6. Per-screen layout

- **S-2 dot:** `●` + `claude-rig: gemini 3.7 (headroom best: nvidia_nim 92%)` in prompt suffix, never more than 40 chars. No interactivity.
- **S-3 toast:** `Title` 14 SemiBold, `Message` 12 Regular, two lines max, bottom-right 16px from edge, shadow `0 8 24 rgba(0,0,0,.35)`.
- **S-4 dialog:** Title 16 Bold, body 12 Regular muted, `*Open key page*` full-width 34h blue, `TextBox` 32h mono, footer right-aligned *Later* (neutral) + *Save & Apply* (green, 120w). ESC = Later, Enter = Save. Always `Topmost=True`, `WindowStartupLocation=CenterScreen`.
- **S-5 ring:** 16px diameter, 2px stroke, muted→amber→red. Tooltip on hover: `1.4M / 2M today (71%) — best headroom: nvidia_nim`.

## 7. Component library

- **Toast** — OS primitive (WinRT `ToastNotificationManager`, `notify-send`, `NSUserNotification`), no custom window.
- **KeyDialog** — WPF `Window` (Win), `zenity --entry --hide-text` (Linux), `osascript display dialog` (macOS). Single XAML string in `FCC-Watchdog.ps1:124-142`.
- **HealthDot** — shell function, no binary.
- **TokenRing** — shell prompt segment, reads `watchdog-state.json:TokenLevelNotified`.

No other components. No design system drift.

## 8. States matrix

| Component | Default | Loading | Success | Error | Empty | Disabled |
|---|---|---|---|---|---|---|
| Toast | — | — | — | — | — | auto-dismiss 8s |
| KeyDialog | empty TextBox | — | green check + `Routing restored` toast | inline MessageBox `That does not look like a valid X key.` | — | *Save* disabled until pattern match |
| HealthDot | green | amber pulse (fallback active) | — | red + `gateway DOWN` toast | — | — |
| TokenRing | 0–80% muted | — | — | 100% red | — | — |
| Install | DryRun plan | spinner | `health 200` | `validate failed` + errors printed | — | — |

Empty states never shown for toasts (they auto-dismiss).

## 9. Responsive behaviour

- Toast: bottom-right on ≥1024px, top-center on <768px (so it never hides behind terminal).
- Dialog: fixed 520×290, but if screen <600w, shrink to 90% width, keep 16 pad.
- Terminal: health dot and ring collapse to `●` only on <80 cols.

No mobile web UI in MVP (dashboard is desktop-only).

## 10. Accessibility

- Toast: OS screen reader reads Title + Message; no essential info *only* in toast (also logged to `watchdog-state.json` and terminal).
- Dialog: keyboard-only flow (Tab → TextBox → Enter), focus lands on TextBox on open (`Focus()`), `Topmost` ensures not hidden behind terminal, contrast ≥4.5:1 (blue #2563EB on white, green #16A34A on white both pass).
- Motion: toast slide 120ms, respects `prefers-reduced-motion` (skip slide, just appear).
- No color-only signals: health dot shape + text, token ring + tooltip percent, error MessageBox has text.

Every choice justified by the one fact: **effortlessness = one toast + one button + one paste.**

## Status
- Specified: principles, direction, tokens, S-1..S-7, flows A–E, layouts, components, states, responsive, a11y
- Pending: owner approval; then Security Audit
