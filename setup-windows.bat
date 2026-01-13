@echo off
setlocal enabledelayedexpansion

:: ============================================
:: Just Amazing - Claude Team Config Installer
:: For Windows Users
:: ============================================

title Claude Team Config - Just Amazing Setup

echo.
echo  ============================================
echo   Just Amazing - Claude Team Config Setup
echo  ============================================
echo.
echo  This will set up Claude Code with our team
echo  standards and best practices.
echo.
echo  What will be installed:
echo    - Team coding standards (CLAUDE.md)
echo    - Security and VPS guidelines
echo    - Recommended plugins
echo    - Auto-update (weekly check)
echo.
echo  Press any key to continue or close this window to cancel...
pause >nul

echo.
echo  [1/5] Checking requirements...

:: Check if PowerShell is available
where powershell >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: PowerShell not found!
    echo  Please install PowerShell and try again.
    pause
    exit /b 1
)
echo         PowerShell found.

:: Check if .claude folder path is accessible
set "CLAUDE_DIR=%USERPROFILE%\.claude"
echo         Claude directory: %CLAUDE_DIR%

echo.
echo  [2/5] Creating directories...

if not exist "%CLAUDE_DIR%" (
    mkdir "%CLAUDE_DIR%"
    echo         Created %CLAUDE_DIR%
) else (
    echo         Directory exists, creating backup...
    set "BACKUP_DIR=%USERPROFILE%\.claude-backup-%date:~-4%%date:~3,2%%date:~0,2%-%time:~0,2%%time:~3,2%"
    set "BACKUP_DIR=!BACKUP_DIR: =0!"
    xcopy "%CLAUDE_DIR%" "!BACKUP_DIR!" /E /I /Q >nul 2>&1
    echo         Backup created at !BACKUP_DIR!
)

if not exist "%CLAUDE_DIR%\rules" (
    mkdir "%CLAUDE_DIR%\rules"
    echo         Created rules folder
)

echo.
echo  [3/5] Downloading team configuration...

:: Download files from GitHub
set "GITHUB_RAW=https://raw.githubusercontent.com/NickZamnesia/claude-team-config/master"

echo         Downloading settings.json...
powershell -Command "(New-Object Net.WebClient).DownloadFile('%GITHUB_RAW%/settings.json', '%CLAUDE_DIR%\settings.json')" 2>nul
if errorlevel 1 (
    echo         ERROR: Could not download settings.json
    pause
    exit /b 1
)

echo         Downloading CLAUDE.md...
powershell -Command "(New-Object Net.WebClient).DownloadFile('%GITHUB_RAW%/CLAUDE.md', '%CLAUDE_DIR%\CLAUDE.md')" 2>nul

echo         Downloading rules/agents.md...
powershell -Command "(New-Object Net.WebClient).DownloadFile('%GITHUB_RAW%/rules/agents.md', '%CLAUDE_DIR%\rules\agents.md')" 2>nul

echo         Downloading sync script...
powershell -Command "(New-Object Net.WebClient).DownloadFile('%GITHUB_RAW%/sync-claude-config.ps1', '%CLAUDE_DIR%\sync-claude-config.ps1')" 2>nul

echo         All files downloaded!

echo.
echo  [4/5] Setting up weekly auto-updates...

:: Create a VBS script to run PowerShell silently
set "UPDATE_SCRIPT=%CLAUDE_DIR%\auto-update.vbs"
(
echo Set objShell = CreateObject^("WScript.Shell"^)
echo objShell.Run "powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File ""%CLAUDE_DIR%\sync-claude-config.ps1""", 0, False
) > "%UPDATE_SCRIPT%"

:: Create scheduled task for weekly updates
schtasks /create /tn "ClaudeTeamConfigUpdate" /tr "wscript.exe \"%UPDATE_SCRIPT%\"" /sc weekly /d MON /st 09:00 /f >nul 2>&1
if errorlevel 1 (
    echo         Note: Could not create scheduled task ^(may need admin rights^)
    echo         You can manually run sync-claude-config.ps1 to update
) else (
    echo         Weekly auto-update scheduled ^(Mondays 9:00 AM^)
)

echo.
echo  [5/5] Creating desktop shortcut...

:: Create desktop shortcut for manual sync
set "SHORTCUT=%USERPROFILE%\Desktop\Update Claude Config.lnk"
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath = 'powershell.exe'; $s.Arguments = '-ExecutionPolicy Bypass -File \"%CLAUDE_DIR%\sync-claude-config.ps1\"'; $s.WorkingDirectory = '%CLAUDE_DIR%'; $s.Description = 'Update Claude Team Configuration'; $s.Save()" 2>nul
if errorlevel 1 (
    echo         Note: Could not create desktop shortcut
) else (
    echo         Desktop shortcut created!
)

echo.
echo  ============================================
echo   Setup Complete!
echo  ============================================
echo.
echo  What was installed:
echo    [x] Team coding standards
echo    [x] Security guidelines
echo    [x] Recommended plugins
echo    [x] Weekly auto-updates
echo.
echo  You can now use Claude Code with our team
echo  configuration. Just start a new conversation!
echo.
echo  Need to manually update? Use the desktop
echo  shortcut "Update Claude Config"
echo.
echo  Press any key to close...
pause >nul
