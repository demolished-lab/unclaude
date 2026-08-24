"""Watchdog — cross-platform headroom-aware FCC companion.

PRD FR-7, BLUEPRINT 6, SECURITY-AUDIT G-2/G-3.
Single instance, 10-min cycle, autostart via systemd/launchd/Startup.
"""
import argparse
import hashlib
import json
import os
import pathlib
import platform
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

FCC_BASE = "http://127.0.0.1:8082"
STATE_FILE = pathlib.Path.home() / ".fcc" / "watchdog-state.json"
TOKEN_BUDGET_DAILY = 2_000_000
TOKEN_WARN_PCT = 80
DISK_WARN_GB = 15

PROVIDERS = {
    "nvidia_nim": {"label": "NVIDIA NIM", "url": "https://build.nvidia.com/settings/api-keys", "pattern": "nvapi-"},
    "gemini": {"label": "Google Gemini", "url": "https://aistudio.google.com/apikey", "pattern": "AQ."},
    "groq": {"label": "Groq", "url": "https://console.groq.com/keys", "pattern": "gsk_"},
    "cloudflare": {"label": "Cloudflare AI", "url": "https://dash.cloudflare.com/profile/api-tokens", "pattern": ""},
    "open_router": {"label": "OpenRouter", "url": "https://openrouter.ai/settings/keys", "pattern": "sk-or-"},
    "ollama_cloud": {"label": "Ollama Cloud", "url": "https://ollama.com/settings/keys", "pattern": ""},
}
PROVIDER_TO_SETTING = {
    "nvidia_nim": "NVIDIA_NIM_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "cloudflare": "CLOUDFLARE_API_TOKEN",
    "open_router": "OPENROUTER_API_KEY",
    "ollama_cloud": "OLLAMA_API_KEY",
}
MODEL_PREFS = {
    "cloudflare": ["gpt-oss-120b", "nemotron-3-120b", "llama-4-scout", "glm-4.7-flash"],
    "ollama_cloud": ["nemotron-3-ultra", "nemotron-3-super", "gpt-oss:120b"],
    "groq": ["gpt-oss-120b", "qwen"],
    "open_router": ["glm-5.2:free", "deepseek.*:free"],
    "nvidia_nim": ["nemotron-3-super-120b", "deepseek-v4"],
    "gemini": ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash"],
}
DAILY_LIMITS = {"gemini": 1_000_000, "groq": 500_000, "cloudflare": 600_000, "open_router": 400_000, "nvidia_nim": 800_000, "ollama_cloud": 500_000}

def notify(title, msg):
    # stdlib-only, cross-platform toast with graceful fallback
    try:
        sysname = platform.system()
        if sysname == "Windows":
            # PowerShell 5.1 compatible, no XML escaping hell - use simple MessageBox fallback via print
            # Try BurntToast if available, else just print (watchdog log is the truth)
            print(f"[NOTIFY] {title}: {msg}")
            return
        elif sysname == "Darwin":
            subprocess.Popen(["osascript", "-e", f'display notification "{msg}" with title "{title}"'])
            return
        else:
            subprocess.Popen(["notify-send", title, msg])
            return
    except Exception:
        pass
    print(f"[NOTIFY] {title}: {msg}")

def fcc_get(path, timeout=20):
    with urllib.request.urlopen(FCC_BASE + path, timeout=timeout) as r:
        return json.loads(r.read())

def fcc_apply(values):
    payload = json.dumps({"values": values}).encode()
    req = urllib.request.Request(FCC_BASE + "/admin/api/config/validate", data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        v = json.loads(r.read())
    if not v.get("valid"):
        return False, v.get("errors")
    req = urllib.request.Request(FCC_BASE + "/admin/api/config/apply", data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        a = json.loads(r.read())
    return bool(a.get("applied")), []

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8-sig"))
        except Exception:
            pass
    return {"CatalogHash": "", "PendingKeys": {}, "TokenLevelNotified": 0, "OutageNotified": False}

def save_state(s):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(s, indent=2), encoding="utf-8")

def get_catalog():
    data = fcc_get("/v1/models", timeout=40)
    s = set()
    for mid in [d["id"] for d in data.get("data", [])]:
        n = mid.replace("anthropic/", "").replace("claude-3-freecc-no-thinking/", "")
        s.add(n)
    return s

def get_tokens_today():
    total = 0
    today = datetime.now(timezone.utc).date()
    # also try local date for transcripts
    root = pathlib.Path.home() / ".claude" / "projects"
    if not root.exists():
        return 0
    for p in root.rglob("*.jsonl"):
        if p.stat().st_mtime < datetime.combine(today, datetime.min.time()).timestamp():
            continue
        try:
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                if len(line) < 20:
                    continue
                o = json.loads(line)
                u = (o.get("message") or {}).get("usage")
                ts = o.get("timestamp")
                if u and ts:
                    try:
                        d = datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
                    except Exception:
                        continue
                    if d == today:
                        total += int(u.get("input_tokens", 0)) + int(u.get("output_tokens", 0))
        except Exception:
            continue
    return total

def show_key_dialog(label, url, pattern):
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.title(f"Claude Rig - {label} key needed")
        root.geometry("520x290")
        root.attributes("-topmost", True)
        tk.Label(root, text=f"{label} needs a new API key", font=("Segoe UI", 14, "bold")).pack(pady=(16, 4))
        tk.Label(root, text="Create a fresh key (already logged in) then paste below.", wraplength=480, fg="#555").pack()
        def open_url():
            import webbrowser
            webbrowser.open(url)
        tk.Button(root, text=f"Open {label} key page", bg="#2563EB", fg="white", command=open_url, height=2).pack(fill="x", padx=16, pady=12)
        var = tk.StringVar()
        tk.Entry(root, textvariable=var, font=("Consolas", 11)).pack(fill="x", padx=16)
        result = {"action": "skip", "key": ""}
        def do_save():
            k = var.get().strip()
            import re
            if pattern and k and not re.search(pattern, k):
                messagebox.showerror("Check key", f"That does not look like a valid {label} key.")
                return
            result["action"] = "save"
            result["key"] = k
            root.destroy()
        def do_skip():
            result["action"] = "skip"
            root.destroy()
        frm = tk.Frame(root)
        frm.pack(side="bottom", pady=12)
        tk.Button(frm, text="Later", command=do_skip, width=10).pack(side="left", padx=6)
        tk.Button(frm, text="Save & Apply", bg="#16A34A", fg="white", command=do_save, width=14).pack(side="left", padx=6)
        root.mainloop()
        return result
    except Exception as e:
        print(f"dialog fallback: {e}")
        return {"action": "skip", "key": ""}

def cycle_once(dry_run=False):
    state = load_state()
    try:
        cfg = fcc_get("/admin/api/config")
        if state.get("OutageNotified"):
            notify("Claude rig back online", "Gateway healthy again.")
            state["OutageNotified"] = False
    except Exception:
        if not state.get("OutageNotified"):
            notify("Claude rig gateway DOWN", "FCC unreachable on :8082")
            state["OutageNotified"] = True
            save_state(state)
        return
    broken = []
    for pid in PROVIDERS:
        st = next((x for x in cfg.get("provider_status", []) if x["provider_id"] == pid), None)
        if st and st["status"] in ("missing_key", "error", "unauthorized"):
            broken.append(pid)
    for p in broken:
        if not state.get("PendingKeys", {}).get(p):
            info = PROVIDERS[p]
            notify(f"{info['label']} key needs attention", "Popup will help you paste a fresh key.")
            if dry_run:
                print(f"[DRYRUN] would rotate {p}")
                continue
            import webbrowser
            webbrowser.open(info["url"])
            res = show_key_dialog(info["label"], info["url"], info["pattern"])
            if res["action"] == "save":
                ok, errs = fcc_apply({PROVIDER_TO_SETTING[p]: res["key"]})
                if ok:
                    notify(f"{info['label']} key replaced", "Routing restored.")
                    state.setdefault("PendingKeys", {})[p] = False
                else:
                    notify(f"{info['label']} key rejected", "; ".join(map(str, errs)))
            else:
                state.setdefault("PendingKeys", {})[p] = True
                notify("Reminder set", f"Will ask again for {info['label']}.")

    catalog = get_catalog()
    h = hashlib.sha256("|".join(sorted(catalog)).encode()).hexdigest()
    if h != state.get("CatalogHash", ""):
        # heal dead slugs
        fields = {f["key"]: f["value"] for f in cfg.get("fields", []) if f["key"].startswith("MODEL") and f["value"]}
        fb = [x for x in (fields.get("MODEL_FALLBACKS") or "").split(",") if x]
        all_slugs = list(fields.values()) + fb
        changed = False
        for slug in set(all_slugs):
            prov = slug.split("/")[0]
            if prov not in PROVIDERS:
                continue
            if slug not in catalog:
                prefs = MODEL_PREFS.get(prov, [])
                best = None
                for pref in prefs:
                    import re
                    for cand in catalog:
                        if cand.startswith(prov + "/") and re.search(pref, cand) and cand not in all_slugs:
                            best = cand
                            break
                    if best:
                        break
                if best:
                    changed = True
                    for k in list(fields.keys()):
                        if fields[k] == slug:
                            fields[k] = best
                    fb = [best if x == slug else x for x in fb]
        if changed and not dry_run:
            vals = {"MODEL_FALLBACKS": ",".join(fb)}
            vals.update({k: v for k, v in fields.items() if k.startswith("MODEL")})
            ok, _ = fcc_apply(vals)
            if ok:
                notify("Routing self-healed", "Dead model replaced.")
        elif state.get("CatalogHash"):
            notify("Free model catalog changed", "Provider lists shifted; routes still valid.")
        state["CatalogHash"] = h

    toks = get_tokens_today()
    pct = round(100 * toks / TOKEN_BUDGET_DAILY) if TOKEN_BUDGET_DAILY else 0
    if pct >= 100 and state.get("TokenLevelNotified", 0) < 100:
        notify("Daily token budget HIT", f"{toks} tokens today. Pools reset tomorrow.")
        state["TokenLevelNotified"] = 100
    elif pct >= TOKEN_WARN_PCT and state.get("TokenLevelNotified", 0) < TOKEN_WARN_PCT:
        notify("Token budget warning", f"{pct}% of today's budget used ({toks}).")
        state["TokenLevelNotified"] = TOKEN_WARN_PCT
    elif pct < 50 and state.get("TokenLevelNotified", 0) > 0:
        state["TokenLevelNotified"] = 0

    save_state(state)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] cycle ok | broken={','.join(broken)} | tokens today={toks} ({pct}%)")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--test-toast", action="store_true")
    ap.add_argument("--loop-seconds", type=int, default=600)
    args = ap.parse_args()
    if args.test_toast:
        notify("Watchdog test", "If you can read this, notifications work.")
        return
    # single-instance via lockfile
    lock = pathlib.Path.home() / ".fcc" / "watchdog.lock"
    try:
        lock.parent.mkdir(parents=True, exist_ok=True)
        fh = open(lock, "w")
        try:
            import msvcrt
            msvcrt.locking(fh.fileno(), 1, 1)
        except Exception:
            pass
    except Exception:
        print("another watchdog running")
        return
    print("FCC watchdog (Python) started.")
    while True:
        try:
            cycle_once(dry_run=args.dry_run)
        except Exception as e:
            print(f"cycle error: {e}")
        if args.once:
            break
        time.sleep(args.loop_seconds)

if __name__ == "__main__":
    main()
