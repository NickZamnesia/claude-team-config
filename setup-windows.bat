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
echo   Claude Config Setup Complete!
echo  ============================================
echo.
echo  What was installed:
echo    [x] Team coding standards
echo    [x] Security guidelines
echo    [x] Recommended plugins
echo    [x] Weekly auto-updates
echo.

:: ============================================
:: VPS SECURITY SCANNER SECTION
:: ============================================
echo.
echo  ============================================
echo   VPS Security Scanner (Optional)
echo  ============================================
echo.
echo  Do you have a VPS server that needs security monitoring?
echo.
echo  This will install:
echo    - Automated security scans (every 6 hours)
echo    - Slack alerts for security issues
echo    - Auto-fix for safe issues (firewall, permissions)
echo    - fail2ban for brute force protection
echo.
set /p INSTALL_VPS="  Install VPS security scanner? (y/n): "

if /i "%INSTALL_VPS%"=="y" goto :install_vps
if /i "%INSTALL_VPS%"=="yes" goto :install_vps
goto :end

:install_vps
echo.
set /p VPS_IP="  Enter your VPS IP address: "

if "%VPS_IP%"=="" (
    echo.
    echo  ERROR: VPS IP address is required!
    goto :end
)

set /p PROJECT_NAME="  Enter your project name (e.g., my-app): "

if "%PROJECT_NAME%"=="" (
    set PROJECT_NAME=my-project
)

set /p PROJECT_PATH="  Enter project path on VPS (default: /opt/%PROJECT_NAME%): "

if "%PROJECT_PATH%"=="" (
    set PROJECT_PATH=/opt/%PROJECT_NAME%
)

echo.
echo  Slack webhook URL is needed for security alerts.
echo  Ask Nick for the team webhook URL, or create your own at:
echo  https://api.slack.com/apps
echo.
set /p SLACK_WEBHOOK="  Enter Slack webhook URL: "

if "%SLACK_WEBHOOK%"=="" (
    echo.
    echo  WARNING: No webhook provided. Slack alerts will not work.
    set SLACK_WEBHOOK=YOUR_SLACK_WEBHOOK_URL
)

echo.
echo  ============================================
echo   Deploying Security Scanner to %VPS_IP%
echo  ============================================
echo.

:: Create temp directory for download
set "TEMP_DIR=%TEMP%\vps-security-deploy"
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
mkdir "%TEMP_DIR%"

echo  [1/6] Downloading security scanner files...
cd "%TEMP_DIR%"

:: Download files from GitHub
set "VPS_GITHUB_RAW=https://raw.githubusercontent.com/NickZamnesia/claude-team-config/master/vps-security"

powershell -Command "(New-Object Net.WebClient).DownloadFile('%VPS_GITHUB_RAW%/vps_security.py', '%TEMP_DIR%\vps_security.py')" 2>nul
powershell -Command "(New-Object Net.WebClient).DownloadFile('%VPS_GITHUB_RAW%/config.yaml.template', '%TEMP_DIR%\config.yaml')" 2>nul
powershell -Command "(New-Object Net.WebClient).DownloadFile('%VPS_GITHUB_RAW%/requirements.txt', '%TEMP_DIR%\requirements.txt')" 2>nul
powershell -Command "(New-Object Net.WebClient).DownloadFile('%VPS_GITHUB_RAW%/install.sh', '%TEMP_DIR%\install.sh')" 2>nul

if not exist "%TEMP_DIR%\vps_security.py" (
    echo.
    echo  ERROR: Could not download security files from GitHub.
    echo  Please check your internet connection and try again.
    goto :end
)

echo         Files downloaded!

echo.
echo  [2/6] Detecting SSH port...

:: Try port 22 first, then 22222
set SSH_PORT=22
ssh -o ConnectTimeout=5 -o BatchMode=yes -p 22 root@%VPS_IP% "echo connected" >nul 2>&1
if errorlevel 1 (
    echo         Port 22 not available, trying 22222...
    set SSH_PORT=22222
    ssh -o ConnectTimeout=5 -o BatchMode=yes -p 22222 root@%VPS_IP% "echo connected" >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  ERROR: Could not connect to VPS on port 22 or 22222.
        echo.
        echo  Please check:
        echo    1. VPS IP address is correct
        echo    2. Your SSH key is set up for this VPS
        echo    3. VPS is running and accessible
        echo.
        goto :end
    )
)
echo         Using SSH port %SSH_PORT%

echo.
echo  [3/6] Copying files to VPS...

:: Create directory on VPS
ssh -p %SSH_PORT% root@%VPS_IP% "mkdir -p /tmp/vps-security-setup" 2>nul

:: Copy files
scp -P %SSH_PORT% "%TEMP_DIR%\*" root@%VPS_IP%:/tmp/vps-security-setup/ >nul 2>&1
if errorlevel 1 (
    echo         ERROR: Could not copy files to VPS
    goto :end
)
echo         Files copied!

echo.
echo  [4/6] Running installer on VPS...

:: Run installer with Slack webhook
ssh -p %SSH_PORT% root@%VPS_IP% "cd /tmp/vps-security-setup && chmod +x install.sh && SLACK_WEBHOOK_URL='%SLACK_WEBHOOK%' ./install.sh" 2>&1

echo.
echo  [5/6] Configuring for your project...

:: Update config.yaml with project details
ssh -p %SSH_PORT% root@%VPS_IP% "sed -i 's|your-project-name|%PROJECT_NAME%|g' /opt/vps-security/config.yaml && sed -i 's|/opt/your-project|%PROJECT_PATH%|g' /opt/vps-security/config.yaml" 2>nul

echo         Configuration updated!

echo.
echo  [6/6] Testing installation...

:: Run a test scan
ssh -p %SSH_PORT% root@%VPS_IP% "cd /opt/vps-security && source .env 2>/dev/null && python3 vps_security.py --test-slack" 2>&1

:: Check timer
ssh -p %SSH_PORT% root@%VPS_IP% "systemctl is-active vps-security.timer" >nul 2>&1
if errorlevel 1 (
    echo         WARNING: Timer may not be running
) else (
    echo         Timer is running (scans every 6 hours)
)

:: Cleanup
rmdir /s /q "%TEMP_DIR%" 2>nul

echo.
echo  ============================================
echo   VPS Security Scanner Installed!
echo  ============================================
echo.
echo  Security monitor is now running on %VPS_IP%
echo.
echo  What's active:
echo    [x] Security scans every 6 hours
echo    [x] Slack alerts to #security-alerts
echo    [x] fail2ban SSH protection
echo    [x] Auto-fix for firewall and permissions
echo.
echo  Check Slack for a test notification!
echo.
echo  Useful commands (run on VPS):
echo    - Manual scan: python3 /opt/vps-security/vps_security.py --verbose
echo    - View logs:   tail -50 /opt/vps-security/logs/security.log
echo.

:end
echo  Press any key to close...
pause >nul
