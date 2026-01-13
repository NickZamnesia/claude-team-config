# Claude Team Config Sync Script v2
# Intelligent merge - adds missing team sections without overwriting personal content
# Run this to sync team configuration to your local ~/.claude folder

param(
    [switch]$Force,
    [switch]$DryRun,
    [switch]$Verbose
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ClaudeDir = "$env:USERPROFILE\.claude"
$BackupDir = "$env:USERPROFILE\.claude-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

# ============================================
# SECTION DEFINITIONS
# ============================================
# Team sections: Always sync from team config (overwrite if exists)
# Personal sections: Never touch, preserve user's content

$TeamSections = @(
    "HIGHEST PRIORITY: VPS Security",
    "Phase 0: Session Initialization",
    "Phase 1: Before Starting Work",
    "Phase 2: During Work",
    "Phase 3: After Each Step",
    "Phase 4: Communication & Documentation",
    "Phase 5: Session End & Context Preservation",
    "Claude Code Configuration",
    "Recovery Protocol",
    "Memory Hierarchy",
    "Project CLAUDE.md Template"
)

$PersonalSections = @(
    "ACTIVE SESSION",
    "Changes This Session",
    "Current Objective",
    "Status",
    "Key Decisions",
    "Important Files",
    "Commands",
    "Detailed Change Log",
    "END OF SESSION CHECKLIST"
)

# ============================================
# HELPER FUNCTIONS
# ============================================

function Parse-MarkdownSections {
    param([string]$Content)

    $sections = @{}
    $currentSection = "_HEADER_"
    $currentContent = @()

    $lines = $Content -split "`n"

    foreach ($line in $lines) {
        if ($line -match "^##\s+(.+)$") {
            # Save previous section
            if ($currentContent.Count -gt 0) {
                $sections[$currentSection] = ($currentContent -join "`n").TrimEnd()
            }
            # Start new section
            $currentSection = $matches[1].Trim()
            $currentContent = @($line)
        } else {
            $currentContent += $line
        }
    }

    # Save last section
    if ($currentContent.Count -gt 0) {
        $sections[$currentSection] = ($currentContent -join "`n").TrimEnd()
    }

    return $sections
}

function Is-TeamSection {
    param([string]$SectionName)

    foreach ($team in $TeamSections) {
        if ($SectionName -like "*$team*") {
            return $true
        }
    }
    return $false
}

function Is-PersonalSection {
    param([string]$SectionName)

    foreach ($personal in $PersonalSections) {
        if ($SectionName -like "*$personal*") {
            return $true
        }
    }
    return $false
}

function Merge-ClaudeMd {
    param(
        [string]$TeamContent,
        [string]$LocalContent
    )

    $teamSections = Parse-MarkdownSections -Content $TeamContent
    $localSections = Parse-MarkdownSections -Content $LocalContent

    $result = @()
    $processedSections = @()
    $changes = @{
        Added = @()
        Updated = @()
        Preserved = @()
    }

    # Start with header from team (title, intro)
    if ($teamSections.ContainsKey("_HEADER_")) {
        $result += $teamSections["_HEADER_"]
        $result += ""
    }

    # Process team sections first (in order they appear in team config)
    foreach ($sectionName in $teamSections.Keys) {
        if ($sectionName -eq "_HEADER_") { continue }

        if (Is-TeamSection -SectionName $sectionName) {
            # This is a team section - use team version
            $result += ""
            $result += "---"
            $result += ""
            $result += $teamSections[$sectionName]
            $processedSections += $sectionName

            if ($localSections.ContainsKey($sectionName)) {
                $changes.Updated += $sectionName
            } else {
                $changes.Added += $sectionName
            }
        }
    }

    # Now add personal sections from local (preserve them)
    foreach ($sectionName in $localSections.Keys) {
        if ($sectionName -eq "_HEADER_") { continue }
        if ($processedSections -contains $sectionName) { continue }

        if (Is-PersonalSection -SectionName $sectionName) {
            # Personal section - preserve from local
            $result += ""
            $result += "---"
            $result += ""
            $result += $localSections[$sectionName]
            $processedSections += $sectionName
            $changes.Preserved += $sectionName
        } elseif (-not (Is-TeamSection -SectionName $sectionName)) {
            # Unknown section (user's custom) - preserve it
            $result += ""
            $result += "---"
            $result += ""
            $result += $localSections[$sectionName]
            $processedSections += $sectionName
            $changes.Preserved += "$sectionName (custom)"
        }
    }

    return @{
        Content = ($result -join "`n")
        Changes = $changes
    }
}

# ============================================
# MAIN SCRIPT
# ============================================

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Claude Team Config Sync v2" -ForegroundColor Cyan
Write-Host "  (Intelligent Merge)" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check if source files exist
if (!(Test-Path "$ScriptDir\settings.json")) {
    Write-Host "ERROR: settings.json not found in $ScriptDir" -ForegroundColor Red
    Write-Host "Make sure you're running this from the claude-team-config folder" -ForegroundColor Yellow
    exit 1
}

# Create backup of existing config
if (Test-Path $ClaudeDir) {
    Write-Host "Creating backup at $BackupDir..." -ForegroundColor Yellow
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

Write-Host ""
Write-Host "--- Syncing Files ---" -ForegroundColor White
Write-Host ""

# ============================================
# 1. SYNC SETTINGS.JSON (merge hooks + preserve user settings)
# ============================================
$settingsSource = "$ScriptDir\settings.json"
$settingsDest = "$ClaudeDir\settings.json"

Write-Host "[1/3] settings.json" -ForegroundColor Cyan

if (Test-Path $settingsDest) {
    Write-Host "  Merging: team hooks + your personal settings..." -ForegroundColor Gray

    if (!$DryRun) {
        $teamConfig = Get-Content $settingsSource | ConvertFrom-Json
        $userConfig = Get-Content $settingsDest | ConvertFrom-Json

        # Start with team config (gets the hooks)
        $merged = $teamConfig

        # Preserve user's plugins
        if ($userConfig.enabledPlugins) {
            $merged | Add-Member -NotePropertyName "enabledPlugins" -NotePropertyValue $userConfig.enabledPlugins -Force
        }

        # Preserve user's thinking setting
        if ($null -ne $userConfig.alwaysThinkingEnabled) {
            $merged | Add-Member -NotePropertyName "alwaysThinkingEnabled" -NotePropertyValue $userConfig.alwaysThinkingEnabled -Force
        }

        # Write merged config
        $merged | ConvertTo-Json -Depth 10 | Set-Content $settingsDest
    }
    Write-Host "  MERGED: hooks updated, plugins preserved" -ForegroundColor Green
} else {
    Write-Host "  Copying (new installation)..." -ForegroundColor Gray
    if (!$DryRun) {
        Copy-Item $settingsSource $settingsDest
    }
    Write-Host "  COPIED" -ForegroundColor Green
}

# ============================================
# 2. SYNC CLAUDE.MD (intelligent section merge)
# ============================================
$claudeSource = "$ScriptDir\CLAUDE.md"
$claudeDest = "$ClaudeDir\CLAUDE.md"

Write-Host ""
Write-Host "[2/3] CLAUDE.md" -ForegroundColor Cyan

if ((Test-Path $claudeSource) -and (Test-Path $claudeDest)) {
    Write-Host "  Performing intelligent merge..." -ForegroundColor Gray

    $teamContent = Get-Content $claudeSource -Raw
    $localContent = Get-Content $claudeDest -Raw

    $mergeResult = Merge-ClaudeMd -TeamContent $teamContent -LocalContent $localContent

    if (!$DryRun) {
        $mergeResult.Content | Set-Content $claudeDest -NoNewline
    }

    Write-Host "  MERGED:" -ForegroundColor Green
    if ($mergeResult.Changes.Added.Count -gt 0) {
        Write-Host "    + Added: $($mergeResult.Changes.Added -join ', ')" -ForegroundColor Green
    }
    if ($mergeResult.Changes.Updated.Count -gt 0) {
        Write-Host "    ~ Updated: $($mergeResult.Changes.Updated -join ', ')" -ForegroundColor Yellow
    }
    if ($mergeResult.Changes.Preserved.Count -gt 0) {
        Write-Host "    = Preserved: $($mergeResult.Changes.Preserved -join ', ')" -ForegroundColor Cyan
    }
} elseif (Test-Path $claudeSource) {
    Write-Host "  Copying (new installation)..." -ForegroundColor Gray
    if (!$DryRun) {
        Copy-Item $claudeSource $claudeDest
    }
    Write-Host "  COPIED" -ForegroundColor Green
} else {
    Write-Host "  SKIP: No team CLAUDE.md found" -ForegroundColor Yellow
}

# ============================================
# 3. SYNC RULES (direct copy - these are team-only)
# ============================================
Write-Host ""
Write-Host "[3/3] rules/agents.md" -ForegroundColor Cyan

$rulesSource = "$ScriptDir\rules\agents.md"
$rulesDest = "$ClaudeDir\rules\agents.md"

if (Test-Path $rulesSource) {
    if (!$DryRun) {
        Copy-Item $rulesSource $rulesDest -Force
    }
    Write-Host "  COPIED (team rules)" -ForegroundColor Green
} else {
    Write-Host "  SKIP: No team rules found" -ForegroundColor Yellow
}

# ============================================
# SUMMARY
# ============================================
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Sync Complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "What was synced:" -ForegroundColor White
Write-Host "  - Team hooks (documentation enforcement)" -ForegroundColor Gray
Write-Host "  - Team plugins (frontend-design, figma, laravel-boost)" -ForegroundColor Gray
Write-Host "  - Team CLAUDE.md sections (VPS security, workflows, etc.)" -ForegroundColor Gray
Write-Host "  - Team rules (multi-agent framework)" -ForegroundColor Gray
Write-Host ""
Write-Host "What was preserved:" -ForegroundColor White
Write-Host "  - Your personal plugins" -ForegroundColor Gray
Write-Host "  - Your Active Session tracking" -ForegroundColor Gray
Write-Host "  - Your project-specific notes" -ForegroundColor Gray
Write-Host "  - Your custom sections" -ForegroundColor Gray
Write-Host ""
Write-Host "Backup location: $BackupDir" -ForegroundColor Yellow
Write-Host ""

if ($DryRun) {
    Write-Host "(DRY RUN - no files were actually modified)" -ForegroundColor Yellow
    Write-Host "Run without -DryRun to apply changes" -ForegroundColor Yellow
}
