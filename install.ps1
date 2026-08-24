param([switch]$DryRun, [switch]$Yes)
Set-StrictMode -Version Latest; $ErrorActionPreference = "Stop"
function Write-Step { param([string]$m) Write-Host "`n==> $m" -ForegroundColor Cyan }
function Test-Cmd { param([string]$n) $null -ne (Get-Command $n -ErrorAction SilentlyContinue) }
Write-Host "Claude Rig - one-command unlimited-feeling Claude (DryRun=$DryRun)" -ForegroundColor Green
$ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue).TotalPhysicalMemory / 1GB)
if (-not $ramGB) { $ramGB = 16 }
$diskC = [math]::Round((Get-PSDrive C -ErrorAction SilentlyContinue).Free / 1GB)
$diskE = try { [math]::Round((Get-PSDrive E -ErrorAction SilentlyContinue).Free / 1GB) } catch { $null }
$budget = if ($ramGB -le 12) { "1.5M" } elseif ($ramGB -ge 32) { "2.5M" } else { "2M" }
$localModel = if ($ramGB -le 12) { "qwen2.5:0.5b" } elseif ($ramGB -ge 32) { "qwen3:8b" } else { "llama3.2:1b" }
Write-Host "Device: ${ramGB}GB RAM, C:${diskC}GB free$(if($diskE){" E:${diskE}GB"}) - budget $budget + $localModel local"
if ($DryRun) { Write-Host "[DryRun] would: ensure uv, install FCC, RTK, Caveman, ECC, watchdog, shim"; exit 0 }
if (-not (Test-Cmd "uv")) {
    Write-Step "Installing uv"
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}
if (-not (Test-Cmd "uv")) { throw "uv not found after install" }
Write-Step "Installing FCC (uv tool)"
$pyReq = "cpython-3.14.0-windows-x86_64-none"
uv tool install --force --refresh-package free-claude-code --python $pyReq "free-claude-code @ https://github.com/Alishahryar1/free-claude-code/archive/refs/heads/main.zip" --quiet
uv tool update-shell | Out-Null
Write-Step "RTK (SHA-pinned)"
$rtkUrl = "https://github.com/rtk-ai/rtk/releases/download/v0.44.2/rtk-x86_64-pc-windows-msvc.zip"
$rtkSha = "3a1e114edce9080f8a10663e9c87488363a82f14a5ca8aab2ad416817f89d47c"
$tmp = Join-Path $env:TEMP "claude-rig-rtk"; New-Item -ItemType Directory -Force -Path $tmp | Out-Null
$zip = Join-Path $tmp "rtk.zip"; Invoke-RestMethod $rtkUrl -OutFile $zip
$sha = [BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([IO.File]::ReadAllBytes($zip))).Replace("-","").ToLower()
if ($sha -ne $rtkSha) { throw "RTK SHA mismatch $sha" }
Expand-Archive $zip -DestinationPath "$tmp/x" -Force
Copy-Item "$tmp/x/rtk.exe" "$env:USERPROFILE\.local\bin\rtk.exe" -Force
& "$env:USERPROFILE\.local\bin\rtk.exe" init --global --auto-patch | Out-Null
Write-Host "RTK hooked"
Write-Step "Caveman + ECC plugins"
claude plugin marketplace add JuliusBrussee/caveman 2>&1 | Out-Null
claude plugin install caveman@caveman 2>&1 | Out-Null
claude plugin marketplace add https://github.com/affaan-m/ECC 2>&1 | Out-Null
claude plugin install ecc@ecc 2>&1 | Out-Null
Write-Host "Plugins installed"
Write-Step "Watchdog (headroom-aware, Python cross-platform)"
$pyWdSrc = Join-Path $PSScriptRoot "rig\watchdog\watchdog.py"
$pyWdDst = "$env:USERPROFILE\fcc-watchdog\watchdog.py"
if (Test-Path $pyWdSrc) { New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\fcc-watchdog" | Out-Null; Copy-Item $pyWdSrc $pyWdDst -Force }
# Prefer Python watchdog, fallback to PowerShell
$wdToRun = if (Test-Path $pyWdDst) { $pyWdDst } else { Join-Path $PSScriptRoot "rig\watchdog\FCC-Watchdog.ps1" }
$startup = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\FCC-Watchdog.lnk"
if (-not (Test-Path $startup)) {
    $ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut($startup)
    if ($wdToRun -like "*.py") {
        $sc.TargetPath = "python.exe"; $sc.Arguments = "`"$wdToRun`""
    } else {
        $sc.TargetPath = "powershell.exe"; $sc.Arguments = '-WindowStyle Hidden -ExecutionPolicy Bypass -STA -File "'+$wdToRun+'"'
    }
    $sc.Save(); Write-Host "Watchdog autostart: $startup"
}
if ($wdToRun -like "*.py") { Start-Process python.exe -ArgumentList "`"$wdToRun`"" -WindowStyle Hidden -ErrorAction SilentlyContinue } else { Start-Process powershell.exe -ArgumentList '-WindowStyle Hidden -ExecutionPolicy Bypass -STA -File "'+$wdToRun+'"' -WindowStyle Hidden -ErrorAction SilentlyContinue }
Write-Host "Watchdog running"
Write-Step "Claude shim (claude -> fcc-claude)"
$profilePath = $PROFILE; if (-not (Test-Path $profilePath)) { New-Item -ItemType File -Force -Path $profilePath | Out-Null }
$hasShim = $false; try { $hasShim = Select-String -Path $profilePath -Pattern 'function claude' -Quiet -ErrorAction SilentlyContinue } catch {}
if ($hasShim) {
    Write-Host "Shim already present"
} else {
    $shimLines = @(
        '# claude-rig shim - auto-starts FCC gateway',
        'function claude {',
        '    try { $null = Invoke-WebRequest http://127.0.0.1:8082/health -UseBasicParsing -TimeoutSec 2 } catch {',
        '        Start-Process "$env:USERPROFILE\.local\bin\fcc-desktop.exe" -WindowStyle Hidden',
        '        foreach ($i in 1..40) { Start-Sleep -Milliseconds 500; try { $null=Invoke-WebRequest http://127.0.0.1:8082/health -UseBasicParsing -TimeoutSec 2; break } catch {} }',
        '    }',
        '    & "$env:USERPROFILE\.local\bin\fcc-claude.exe" @args',
        '}'
    )
    $shimLines | Add-Content -Path $profilePath -Encoding UTF8
    Write-Host "Shim added to $profilePath - restart terminal"
}
Write-Host "`nDone - try: claude -p 'Reply exactly: RIG OK'  (claude.exe bypasses rig)" -ForegroundColor Green
Write-Host "Dashboard: http://127.0.0.1:8082/admin  |  Docs: PRD.md BLUEPRINT.md"
