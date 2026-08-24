# Contributing

1. Fork, branch from `main`, keep PRs small.
2. Run checks locally:
   ```bash
   ruff check rig/ tests/
   python -m rig.cli scan --dry-run
   python -m rig.watchdog.watchdog --once --dry-run
   ```
3. No secrets in PRs. Provider keys stay in `~/.fcc/.env` (encrypted).
4. One-command install must stay `DryRun`-verifiable: `install.ps1 -DryRun` / `install.sh --dry-run`.

See `SECURITY-AUDIT.md` G-1..G-7 for pre-launch gates.
