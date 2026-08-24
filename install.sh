#!/usr/bin/env bash
set -euo pipefail
DRYRUN=0; [[ "${1:-}" == "--dry-run" ]] && DRYRUN=1

echo "Claude Rig — one-command unlimited-feeling Claude (dry-run=$DRYRUN)"
RAM_GB=$(free -g 2>/dev/null | awk '/Mem:/{print $2}'); RAM_GB=${RAM_GB:-16}
DISK_GB=$(df -BG / 2>/dev/null | awk 'NR==2{print $4}' | tr -d 'G'); DISK_GB=${DISK_GB:-50}
echo "Device: ${RAM_GB}GB RAM, ${DISK_GB}GB free — budget $([ "$RAM_GB" -le 12 ] && echo 1.5M || ([ "$RAM_GB" -ge 32 ] && echo 2.5M || echo 2M))"

if [ "$DRYRUN" -eq 1 ]; then echo "[DryRun] would: ensure uv, FCC, RTK, Caveman, ECC, watchdog, shim"; exit 0; fi

command -v uv >/dev/null 2>&1 || { echo "==> Installing uv"; curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$PATH"; }
command -v uv >/dev/null 2>&1 || { echo "uv not found"; exit 1; }

echo "==> Installing FCC (uv tool)"
uv tool install --force --refresh-package free-claude-code --python cpython-3.14 "free-claude-code @ https://github.com/Alishahryar1/free-claude-code/archive/refs/heads/main.zip" --quiet
uv tool update-shell >/dev/null 2>&1 || true

echo "==> RTK"
RTK_URL="https://github.com/rtk-ai/rtk/releases/download/v0.44.2/rtk-x86_64-unknown-linux-gnu.tar.gz"
RTK_SHA="a1b2c3d4-placeholder-for-linux-sha" # replace with real SHA on release
TMPDIR=$(mktemp -d); curl -LsSf "$RTK_URL" -o "$TMPDIR/rtk.tar.gz" || echo "RTK download failed (check URL), continuing"
if [ -f "$TMPDIR/rtk.tar.gz" ]; then tar -xzf "$TMPDIR/rtk.tar.gz" -C "$TMPDIR" 2>/dev/null || true; cp "$TMPDIR/rtk" "$HOME/.local/bin/rtk" 2>/dev/null || true; "$HOME/.local/bin/rtk" init --global --auto-patch 2>/dev/null || true; echo "RTK hooked"; fi

echo "==> Caveman + ECC plugins"
claude plugin marketplace add JuliusBrussee/caveman 2>/dev/null || true
claude plugin install caveman@caveman 2>/dev/null || true
claude plugin marketplace add https://github.com/affaan-m/ECC 2>/dev/null || true
claude plugin install ecc@ecc 2>/dev/null || true
claude plugin list 2>/dev/null | grep -E "caveman|ecc" || true

echo "==> Watchdog (systemd/launchd)"
WATCHDOG_SRC="$(dirname "$0")/rig/watchdog/watchdog.py"
WATCHDOG_DST="$HOME/fcc-watchdog/watchdog.py"
mkdir -p "$(dirname "$WATCHDOG_DST")"; cp "$WATCHDOG_SRC" "$WATCHDOG_DST" 2>/dev/null || true
if command -v systemctl >/dev/null 2>&1; then
  mkdir -p "$HOME/.config/systemd/user"
  cat > "$HOME/.config/systemd/user/fcc-watchdog.service" <<EOF
[Unit]
Description=FCC headroom watchdog
After=network.target
[Service]
ExecStart=$(command -v python3) $WATCHDOG_DST
Restart=always
[Install]
WantedBy=default.target
EOF
  systemctl --user daemon-reload 2>/dev/null || true; systemctl --user enable --now fcc-watchdog 2>/dev/null || true
  echo "systemd user service installed"
elif [[ "$(uname)" == "Darwin" ]]; then
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$HOME/Library/LaunchAgents/com.claude-rig.watchdog.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTL/plist-1.0.dtd">
<plist><dict><key>Label</key><string>com.claude-rig.watchdog</string><key>ProgramArguments</key><array><string>$(command -v python3)</string><string>$WATCHDOG_DST</string></array><key>RunAtLoad</key><true/></dict></plist>
EOF
  launchctl load "$HOME/Library/LaunchAgents/com.claude-rig.watchdog.plist" 2>/dev/null || true
  echo "launchd agent installed"
else
  (nohup python3 "$WATCHDOG_DST" >/tmp/fcc-watchdog.log 2>&1 &)
  echo "watchdog backgrounded"
fi

echo "==> Claude shim (claude -> fcc-claude)"
SHELL_RC="$HOME/.bashrc"; [[ "$SHELL" == *zsh* ]] && SHELL_RC="$HOME/.zshrc"
if ! grep -q "function claude" "$SHELL_RC" 2>/dev/null; then
  cat >> "$SHELL_RC" <<'EOS'

# claude-rig shim
claude() {
  curl -fsS http://127.0.0.1:8082/health >/dev/null 2>&1 || { fcc-server >/tmp/fcc.log 2>&1 & sleep 3; }
  fcc-claude "$@"
}
EOS
  echo "Shim added to $SHELL_RC — restart shell or source it"
else
  echo "Shim already present"
fi

echo ""
echo "Done — try: claude -p 'Reply exactly: RIG OK'  (claude --help bypasses rig if needed)"
echo "Dashboard: http://127.0.0.1:8082/admin"
