# Claude Team Config - Just Amazing

Shared Claude Code configuration for the Just Amazing team. Ensures consistent coding standards, security practices, and documentation across all projects.

## Quick Setup (One Click)

### Windows
1. **[Download setup-windows.bat](https://github.com/NickZamnesia/claude-team-config/raw/master/setup-windows.bat)**
2. Double-click the downloaded file
3. Done! ✅

### Mac
1. **[Download setup-mac.command](https://github.com/NickZamnesia/claude-team-config/raw/master/setup-mac.command)**
2. Double-click the downloaded file
3. If blocked: Right-click → Open → Open
4. Done! ✅

---

## What Gets Installed

| Component | Description |
|-----------|-------------|
| `settings.json` | Team hooks and recommended plugins |
| `CLAUDE.md` | Coding standards, VPS security, workflows |
| `rules/agents.md` | Multi-agent product development framework |
| Auto-update | Weekly check for configuration updates (Mondays 9 AM) |

---

## Features

### 🔒 VPS Security Guidelines
- Firewall configuration (UFW)
- Database port security
- SSH protection (fail2ban)
- Credential management

### 📝 Documentation Enforcement
- Automatic reminders to update project logs
- Active Session tracking
- Change logging requirements

### 🔧 Team Plugins
- `frontend-design` - UI/frontend development
- `figma` - Design integration
- `laravel-boost` - Laravel development

### 🔄 Auto-Updates
Configuration automatically stays in sync with team standards.

---

## Manual Update

If you need to manually sync your configuration:

**Windows:**
- Double-click "Update Claude Config" on your desktop
- Or run: `powershell -ExecutionPolicy Bypass -File ~/.claude/sync-claude-config.ps1`

**Mac:**
- Run in Terminal: `update-claude-config`
- Or: `cd ~/.claude && ./sync-claude-config.sh`

---

## File Structure

```
~/.claude/
├── settings.json          # Hooks, plugins configuration
├── CLAUDE.md              # Team standards and guidelines
├── rules/
│   └── agents.md          # Multi-agent framework
├── sync-claude-config.ps1 # Windows sync script
└── sync-claude-config.sh  # Mac/Linux sync script
```

---

## Troubleshooting

### Windows: "Windows protected your PC"
Click "More info" → "Run anyway"

### Mac: "Cannot be opened because it is from an unidentified developer"
Right-click the file → Open → Open

### Mac: "Permission denied"
```bash
chmod +x ~/Downloads/setup-mac.command
```

---

## Contributing

To update team configuration:
1. Edit files in this repository
2. Commit and push changes
3. Team members will receive updates automatically on Monday

---

## Support

Contact the team lead if you have any issues with the setup or configuration.
