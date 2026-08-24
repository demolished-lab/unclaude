import pathlib
import subprocess
import sys

def test_device_detect():
    from rig.detect.device import detect
    d = detect()
    assert "ram_gb" in d and d["ram_gb"] > 0
    assert "budget" in d

def test_cli_scan_dry():
    r = subprocess.run([sys.executable, "-m", "rig.cli", "scan", "--dry-run"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "dry-run" in r.stdout.lower()

def test_watchdog_dry():
    r = subprocess.run([sys.executable, "-m", "rig.watchdog.watchdog", "--once", "--dry-run"], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0
    assert "cycle ok" in r.stdout.lower() or "dryrun" in r.stdout.lower()

def test_researcher_budget():
    from rig.research.researcher import get_session_tokens
    t = get_session_tokens()
    assert isinstance(t, int)
    assert t >= 0
