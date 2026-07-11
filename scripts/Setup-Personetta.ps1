<#
.SYNOPSIS
    Install the personetta CLI from PyPI and make it work from any directory.

.DESCRIPTION
    One-command setup for Windows:
      1. Verifies Python 3.11+ is available.
      2. Installs (or upgrades) personetta — via pipx when present, otherwise
         `pip install --user`.
      3. Ensures Python's user Scripts folder is on your PATH so the
         `personetta` command works globally.
      4. Optionally adds a short `pn` alias to your PowerShell profile.
      5. Verifies the install.

    Idempotent — safe to run multiple times.

.PARAMETER SkipProfile
    Don't add the `pn` alias to your PowerShell profile.

.PARAMETER SkipPathCheck
    Skip checking/fixing PATH configuration.

.EXAMPLE
    .\scripts\Setup-Personetta.ps1
#>
param(
    [switch]$SkipProfile,
    [switch]$SkipPathCheck
)

$ErrorActionPreference = 'Stop'

Write-Host "=== Personetta Setup ===" -ForegroundColor Cyan

# --- 1. Python check --------------------------------------------------------
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "Python not found in PATH." -ForegroundColor Red
    Write-Host "Install Python 3.11+ from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "(check 'Add Python to PATH' during installation), then re-run this script."
    exit 1
}
$versionOk = & python -c "import sys; print(int(sys.version_info >= (3, 11)))" 2>$null
if ($versionOk -ne '1') {
    Write-Host "Personetta requires Python 3.11+ (found: $(& python --version 2>&1))." -ForegroundColor Red
    exit 1
}
Write-Host "Python OK: $(& python --version 2>&1)" -ForegroundColor Green

# --- 2. Install from PyPI ---------------------------------------------------
$pipx = Get-Command pipx -ErrorAction SilentlyContinue
if ($pipx) {
    Write-Host "Installing personetta via pipx..." -ForegroundColor Cyan
    pipx install --force personetta
} else {
    Write-Host "Installing personetta via pip (user install)..." -ForegroundColor Cyan
    & python -m pip install --user --upgrade personetta
    if ($LASTEXITCODE -ne 0) { throw "pip install failed." }
}
Write-Host "Package installed." -ForegroundColor Green

# --- 3. Ensure the Scripts folder is on PATH --------------------------------
if (-not $SkipPathCheck -and -not $pipx) {
    $userSite = & python -c "import site, os; print(os.path.dirname(site.getusersitepackages()))" 2>$null
    $scriptsDir = if ($userSite) { Join-Path $userSite 'Scripts' } else { $null }
    if (-not $scriptsDir -or -not (Test-Path $scriptsDir)) {
        $scriptsDir = & python -c "import sysconfig; print(sysconfig.get_path('scripts'))" 2>$null
    }

    if ($scriptsDir -and (Test-Path $scriptsDir)) {
        $userPath = [Environment]::GetEnvironmentVariable('PATH', 'User')
        $entries = ($userPath -split ';') | ForEach-Object { $_.TrimEnd('\') }
        if ($entries -notcontains $scriptsDir.TrimEnd('\')) {
            Write-Host "Adding to PATH: $scriptsDir" -ForegroundColor Cyan
            [Environment]::SetEnvironmentVariable('PATH', ($userPath.TrimEnd(';') + ';' + $scriptsDir), 'User')
            $env:PATH = $env:PATH.TrimEnd(';') + ';' + $scriptsDir
            Write-Host "Added. Restart other terminals to pick it up." -ForegroundColor Green
        } else {
            Write-Host "Scripts directory already on PATH." -ForegroundColor Green
        }
    } else {
        Write-Host "Could not locate Python's Scripts directory; if 'personetta' is not found, add it to PATH manually." -ForegroundColor Yellow
    }
}

# --- 4. Optional profile alias ----------------------------------------------
if (-not $SkipProfile) {
    if (-not (Test-Path $PROFILE)) {
        New-Item -ItemType File -Path $PROFILE -Force | Out-Null
    }
    $profileContent = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue
    if ($profileContent -notmatch 'Set-Alias.+\bpn\b') {
        Add-Content -Path $PROFILE -Value "`n# Personetta CLI short alias (added by Setup-Personetta.ps1)`nSet-Alias -Name pn -Value personetta -ErrorAction SilentlyContinue"
        Write-Host "Added 'pn' alias to your PowerShell profile." -ForegroundColor Green
    } else {
        Write-Host "'pn' alias already configured." -ForegroundColor Green
    }
}

# --- 5. Verify ---------------------------------------------------------------
Write-Host "`nVerifying install..." -ForegroundColor Cyan
$cli = Get-Command personetta -ErrorAction SilentlyContinue
if ($cli) {
    personetta --version
    personetta verify
} else {
    Write-Host "The 'personetta' command is not visible in THIS session yet." -ForegroundColor Yellow
    Write-Host "Restart your terminal, then run: personetta verify"
    Write-Host "(The module form always works: python -m generator.cli.main --version)"
}

Write-Host "`nDone. Try: personetta list" -ForegroundColor Cyan
