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
echo "   Setup Complete!"
echo "  ============================================"
echo ""
echo "  What was installed:"
echo "    [x] Team coding standards"
echo "    [x] Security guidelines"
echo "    [x] Recommended plugins"
echo "    [x] Weekly auto-updates"
echo ""
echo "  You can now use Claude Code with our team"
echo "  configuration. Just start a new conversation!"
echo ""
echo "  Need to manually update? Run:"
echo "    update-claude-config"
echo "  (after opening a new terminal)"
echo ""
read -p "  Press Enter to close..."
