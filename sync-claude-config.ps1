# Claude Team Config Sync Script
# Run this to sync team configuration to your local ~/.claude folder
# This does NOT touch your project-level CLAUDE.md files - only global config

param(
    [switch]$Force,
    [switch]$DryRun
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ClaudeDir = "$env:USERPROFILE\.claude"
$BackupDir = "$env:USERPROFILE\.claude-backup"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Claude Team Config Sync" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check if source files exist
if (!(Test-Path "$ScriptDir\settings.json")) {
    Write-Host "ERROR: settings.json not found in $ScriptDir" -ForegroundColor Red
    exit 1
}

# Create backup of existing config (first time only, unless -Force)
if ((Test-Path $ClaudeDir) -and !(Test-Path $BackupDir)) {
    Write-Host "Creating backup of existing config at $BackupDir..." -ForegroundColor Yellow
    if (!$DryRun) {
        Copy-Item $ClaudeDir $BackupDir -Recurse
    }
    Write-Host "  Backup created." -ForegroundColor Green
}

# Create .claude directory if it doesn't exist
if (!(Test-Path $ClaudeDir)) {
    Write-Host "Creating $ClaudeDir..." -ForegroundColor Yellow
    if (!$DryRun) {
        New-Item -ItemType Directory -Path $ClaudeDir | Out-Null
    }
}

# Create rules subdirectory if it doesn't exist
if (!(Test-Path "$ClaudeDir\rules")) {
    Write-Host "Creating $ClaudeDir\rules..." -ForegroundColor Yellow
    if (!$DryRun) {
        New-Item -ItemType Directory -Path "$ClaudeDir\rules" | Out-Null
    }
}

# Files to sync (team config only)
$filesToSync = @(
    @{ Source = "settings.json"; Dest = "settings.json"; Merge = $true },
    @{ Source = "CLAUDE.md"; Dest = "CLAUDE.md"; Merge = $false },
    @{ Source = "rules\agents.md"; Dest = "rules\agents.md"; Merge = $false }
)

foreach ($file in $filesToSync) {
    $sourcePath = Join-Path $ScriptDir $file.Source
    $destPath = Join-Path $ClaudeDir $file.Dest

    if (Test-Path $sourcePath) {
        if ($file.Merge -and (Test-Path $destPath)) {
            # For settings.json, merge hooks while preserving user's plugins
            Write-Host "Merging $($file.Source) (preserving your plugins)..." -ForegroundColor Cyan

            if (!$DryRun) {
                $teamConfig = Get-Content $sourcePath | ConvertFrom-Json
                $userConfig = Get-Content $destPath | ConvertFrom-Json

                # Preserve user's plugins and other settings
                if ($userConfig.enabledPlugins) {
                    $teamConfig | Add-Member -NotePropertyName "enabledPlugins" -NotePropertyValue $userConfig.enabledPlugins -Force
                }
                if ($userConfig.alwaysThinkingEnabled) {
                    $teamConfig | Add-Member -NotePropertyName "alwaysThinkingEnabled" -NotePropertyValue $userConfig.alwaysThinkingEnabled -Force
                }

                # Write merged config
                $teamConfig | ConvertTo-Json -Depth 10 | Set-Content $destPath
            }
            Write-Host "  Merged: hooks from team + your personal settings" -ForegroundColor Green
        } else {
            # Direct copy
            Write-Host "Syncing $($file.Source)..." -ForegroundColor Cyan
            if (!$DryRun) {
                Copy-Item $sourcePath $destPath -Force
            }
            Write-Host "  Copied." -ForegroundColor Green
        }
    } else {
        Write-Host "SKIP: $($file.Source) not found in team config" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Sync Complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "What was synced:" -ForegroundColor White
Write-Host "  - hooks (documentation enforcement)" -ForegroundColor Gray
Write-Host "  - CLAUDE.md (team work standards)" -ForegroundColor Gray
Write-Host "  - rules/agents.md (multi-agent framework)" -ForegroundColor Gray
Write-Host ""
Write-Host "What was NOT touched:" -ForegroundColor White
Write-Host "  - Your project-level CLAUDE.md files" -ForegroundColor Gray
Write-Host "  - Your personal plugin settings" -ForegroundColor Gray
Write-Host ""

if ($DryRun) {
    Write-Host "(DRY RUN - no files were actually modified)" -ForegroundColor Yellow
}
