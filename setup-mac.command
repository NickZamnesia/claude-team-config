#!/bin/bash
# ============================================
# Just Amazing - Claude Team Config Installer
# For Mac Users
# ============================================

clear

echo ""
echo "  ============================================"
echo "   Just Amazing - Claude Team Config Setup"
echo "  ============================================"
echo ""
echo "  This will set up Claude Code with our team"
echo "  standards and best practices."
echo ""
echo "  What will be installed:"
echo "    - Team coding standards (CLAUDE.md)"
echo "    - Security and VPS guidelines"
echo "    - Recommended plugins"
echo "    - Auto-update (weekly check)"
echo ""
read -p "  Press Enter to continue or Ctrl+C to cancel..."

CLAUDE_DIR="$HOME/.claude"
GITHUB_RAW="https://raw.githubusercontent.com/NickZamnesia/claude-team-config/master"

echo ""
echo "  [1/5] Checking requirements..."
echo "         Mac detected: $(sw_vers -productVersion 2>/dev/null || echo 'OK')"

echo ""
echo "  [2/5] Creating directories..."

if [[ -d "$CLAUDE_DIR" ]]; then
    BACKUP_DIR="$HOME/.claude-backup-$(date +%Y%m%d-%H%M%S)"
    echo "         Directory exists, creating backup..."
    cp -r "$CLAUDE_DIR" "$BACKUP_DIR"
    echo "         Backup created at $BACKUP_DIR"
else
    mkdir -p "$CLAUDE_DIR"
    echo "         Created $CLAUDE_DIR"
fi

mkdir -p "$CLAUDE_DIR/rules"
echo "         Created rules folder"

echo ""
echo "  [3/5] Downloading team configuration..."

echo "         Downloading settings.json..."
curl -sL "$GITHUB_RAW/settings.json" -o "$CLAUDE_DIR/settings.json"

# Update settings.json to use bash hook instead of PowerShell
cat > "$CLAUDE_DIR/settings.json" << 'EOF'
{
  "enabledPlugins": {
    "frontend-design@claude-plugins-official": true,
    "figma@claude-plugins-official": true,
    "laravel-boost@claude-plugins-official": true
  },
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "if [ -f CLAUDE.md ]; then echo '[CLAUDE.md found] Remember: Update Active Session tracking after each change'; else echo '[No CLAUDE.md in this directory]'; fi"
          }
        ]
      }
    ]
  }
}
EOF

echo "         Downloading CLAUDE.md..."
curl -sL "$GITHUB_RAW/CLAUDE.md" -o "$CLAUDE_DIR/CLAUDE.md"

echo "         Downloading rules/agents.md..."
curl -sL "$GITHUB_RAW/rules/agents.md" -o "$CLAUDE_DIR/rules/agents.md"

echo "         Downloading sync script..."
curl -sL "$GITHUB_RAW/sync-claude-config.sh" -o "$CLAUDE_DIR/sync-claude-config.sh"
chmod +x "$CLAUDE_DIR/sync-claude-config.sh"

echo "         All files downloaded!"

echo ""
echo "  [4/5] Setting up weekly auto-updates..."

# Create LaunchAgent for weekly updates
LAUNCH_AGENT_DIR="$HOME/Library/LaunchAgents"
LAUNCH_AGENT_FILE="$LAUNCH_AGENT_DIR/com.justamazing.claude-config-update.plist"

mkdir -p "$LAUNCH_AGENT_DIR"

cat > "$LAUNCH_AGENT_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.justamazing.claude-config-update</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>cd $CLAUDE_DIR &amp;&amp; curl -sL $GITHUB_RAW/CLAUDE.md -o CLAUDE.md &amp;&amp; curl -sL $GITHUB_RAW/rules/agents.md -o rules/agents.md</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>1</integer>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$HOME/.claude/update.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.claude/update-error.log</string>
</dict>
</plist>
EOF

# Load the LaunchAgent
launchctl load "$LAUNCH_AGENT_FILE" 2>/dev/null || true
echo "         Weekly auto-update scheduled (Mondays 9:00 AM)"

echo ""
echo "  [5/5] Creating manual update alias..."

# Add alias to .zshrc or .bashrc
SHELL_RC="$HOME/.zshrc"
if [[ ! -f "$SHELL_RC" ]]; then
    SHELL_RC="$HOME/.bashrc"
fi

if ! grep -q "alias update-claude-config" "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"
    echo "# Claude Team Config" >> "$SHELL_RC"
    echo "alias update-claude-config='cd ~/.claude && ./sync-claude-config.sh'" >> "$SHELL_RC"
    echo "         Added 'update-claude-config' command to your shell"
else
    echo "         Update command already exists"
fi

echo ""
echo "  ============================================"
echo "   Claude Config Setup Complete!"
echo "  ============================================"
echo ""
echo "  What was installed:"
echo "    [x] Team coding standards"
echo "    [x] Security guidelines"
echo "    [x] Recommended plugins"
echo "    [x] Weekly auto-updates"
echo ""

# ============================================
# VPS SECURITY SCANNER SECTION
# ============================================
echo ""
echo "  ============================================"
echo "   VPS Security Scanner (Optional)"
echo "  ============================================"
echo ""
echo "  Do you have a VPS server that needs security monitoring?"
echo ""
echo "  This will install:"
echo "    - Automated security scans (every 6 hours)"
echo "    - Slack alerts for security issues"
echo "    - Auto-fix for safe issues (firewall, permissions)"
echo "    - fail2ban for brute force protection"
echo ""
read -p "  Install VPS security scanner? (y/n): " INSTALL_VPS

if [[ "$INSTALL_VPS" != "y" && "$INSTALL_VPS" != "Y" && "$INSTALL_VPS" != "yes" ]]; then
    echo ""
    echo "  Skipping VPS security scanner."
    echo ""
    read -p "  Press Enter to close..."
    exit 0
fi

echo ""
read -p "  Enter your VPS IP address: " VPS_IP

if [[ -z "$VPS_IP" ]]; then
    echo ""
    echo "  ERROR: VPS IP address is required!"
    read -p "  Press Enter to close..."
    exit 1
fi

echo ""
read -p "  Enter your project name (e.g., my-app): " PROJECT_NAME

if [[ -z "$PROJECT_NAME" ]]; then
    PROJECT_NAME="my-project"
fi

read -p "  Enter project path on VPS (default: /opt/$PROJECT_NAME): " PROJECT_PATH

if [[ -z "$PROJECT_PATH" ]]; then
    PROJECT_PATH="/opt/$PROJECT_NAME"
fi

echo ""
echo "  ============================================"
echo "   Deploying Security Scanner to $VPS_IP"
echo "  ============================================"
echo ""

# Create temp directory
TEMP_DIR="/tmp/vps-security-deploy"
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

echo "  [1/6] Downloading security scanner files..."

VPS_GITHUB_RAW="https://raw.githubusercontent.com/NickZamnesia/claude-team-config/master/vps-security"

curl -sL "$VPS_GITHUB_RAW/vps_security.py" -o "$TEMP_DIR/vps_security.py"
curl -sL "$VPS_GITHUB_RAW/config.yaml.template" -o "$TEMP_DIR/config.yaml"
curl -sL "$VPS_GITHUB_RAW/requirements.txt" -o "$TEMP_DIR/requirements.txt"
curl -sL "$VPS_GITHUB_RAW/install.sh" -o "$TEMP_DIR/install.sh"

if [[ ! -f "$TEMP_DIR/vps_security.py" ]]; then
    echo ""
    echo "  ERROR: Could not download security files from GitHub."
    echo "  Please check your internet connection and try again."
    read -p "  Press Enter to close..."
    exit 1
fi

echo "         Files downloaded!"

echo ""
echo "  [2/6] Detecting SSH port..."

# Try port 22 first, then 22222
SSH_PORT=22
if ssh -o ConnectTimeout=5 -o BatchMode=yes -p 22 root@$VPS_IP "echo connected" &>/dev/null; then
    SSH_PORT=22
    echo "         Using SSH port 22"
elif ssh -o ConnectTimeout=5 -o BatchMode=yes -p 22222 root@$VPS_IP "echo connected" &>/dev/null; then
    SSH_PORT=22222
    echo "         Using SSH port 22222"
else
    echo ""
    echo "  ERROR: Could not connect to VPS on port 22 or 22222."
    echo ""
    echo "  Please check:"
    echo "    1. VPS IP address is correct"
    echo "    2. Your SSH key is set up for this VPS"
    echo "    3. VPS is running and accessible"
    echo ""
    read -p "  Press Enter to close..."
    exit 1
fi

echo ""
echo "  [3/6] Copying files to VPS..."

# Create directory on VPS
ssh -p $SSH_PORT root@$VPS_IP "mkdir -p /tmp/vps-security-setup"

# Copy files
scp -P $SSH_PORT "$TEMP_DIR"/* root@$VPS_IP:/tmp/vps-security-setup/ &>/dev/null

if [[ $? -ne 0 ]]; then
    echo "         ERROR: Could not copy files to VPS"
    read -p "  Press Enter to close..."
    exit 1
fi

echo "         Files copied!"

echo ""
echo "  [4/6] Running installer on VPS..."

# Run installer
ssh -p $SSH_PORT root@$VPS_IP "cd /tmp/vps-security-setup && chmod +x install.sh && ./install.sh"

echo ""
echo "  [5/6] Configuring for your project..."

# Update config.yaml with project details
ssh -p $SSH_PORT root@$VPS_IP "sed -i 's|your-project-name|$PROJECT_NAME|g' /opt/vps-security/config.yaml && sed -i 's|/opt/your-project|$PROJECT_PATH|g' /opt/vps-security/config.yaml" 2>/dev/null

echo "         Configuration updated!"

echo ""
echo "  [6/6] Testing installation..."

# Run test scan
ssh -p $SSH_PORT root@$VPS_IP "cd /opt/vps-security && source .env 2>/dev/null && python3 vps_security.py --test-slack" 2>&1

# Check timer
if ssh -p $SSH_PORT root@$VPS_IP "systemctl is-active vps-security.timer" &>/dev/null; then
    echo "         Timer is running (scans every 6 hours)"
else
    echo "         WARNING: Timer may not be running"
fi

# Cleanup
rm -rf "$TEMP_DIR"

echo ""
echo "  ============================================"
echo "   VPS Security Scanner Installed!"
echo "  ============================================"
echo ""
echo "  Security monitor is now running on $VPS_IP"
echo ""
echo "  What's active:"
echo "    [x] Security scans every 6 hours"
echo "    [x] Slack alerts to #security-alerts"
echo "    [x] fail2ban SSH protection"
echo "    [x] Auto-fix for firewall and permissions"
echo ""
echo "  Check Slack for a test notification!"
echo ""
echo "  Useful commands (run on VPS):"
echo "    - Manual scan: python3 /opt/vps-security/vps_security.py --verbose"
echo "    - View logs:   tail -50 /opt/vps-security/logs/security.log"
echo ""
read -p "  Press Enter to close..."
