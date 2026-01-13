# Claude Code Team Configuration

Shared Claude Code configuration for the Just Amazing team. This ensures consistent documentation practices and work standards across all team members.

## What's Included

| File | Purpose |
|------|---------|
| `settings.json` | Hooks that enforce documentation (auto-injected on every prompt) |
| `CLAUDE.md` | Team work standards (security, testing, documentation) |
| `rules/agents.md` | Multi-agent framework for product development |

## What's NOT Included

- **Project CLAUDE.md files** - These stay in each project and are personal/project-specific
- **Personal plugins** - Your enabled plugins are preserved during sync

## Setup (First Time)

### Step 1: Clone this repository

```powershell
# If using git
git clone https://github.com/YourOrg/claude-team-config.git
cd claude-team-config

# Or if using OneDrive shared folder, just navigate to it
cd "OneDrive - Just Amazing\Shared\claude-team-config"
```

### Step 2: Run the sync script

```powershell
# Preview what will change (dry run)
.\sync-claude-config.ps1 -DryRun

# Actually sync
.\sync-claude-config.ps1
```

### Step 3: Restart Claude Code

Close and reopen any Claude Code sessions to pick up the new hooks.

## Updating

When the team config is updated:

```powershell
# If using git
cd claude-team-config
git pull

# Then run sync
.\sync-claude-config.ps1
```

If using OneDrive, files sync automatically. Just run the sync script when notified of updates.

## How the Documentation Enforcement Works

The `settings.json` contains a hook that runs on **every message** you send to Claude Code:

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "matcher": "",
      "hooks": [{
        "type": "prompt",
        "prompt": "MANDATORY DOCUMENTATION CHECK: Before responding, you MUST check if there is a CLAUDE.md file..."
      }]
    }]
  }
}
```

This ensures Claude:
1. Checks for a project CLAUDE.md on every conversation
2. Fills in the ACTIVE SESSION section before working
3. Updates the "Changes Made" counter after each change
4. Logs changes to the "Changes This Session" table

## Creating Project CLAUDE.md Files

When starting a new project, create a `CLAUDE.md` in the project root using the template from the team `CLAUDE.md` file. The template includes:

- Active Session tracking (date, task, change counter)
- Changes This Session table
- Detailed Change Log section
- End of Session checklist

## Troubleshooting

### Hooks not working?
1. Make sure `~/.claude/settings.json` exists and contains the hooks
2. Restart Claude Code completely (close all sessions)
3. Run `.\sync-claude-config.ps1` again

### Lost personal settings?
Your original config is backed up at `~/.claude-backup/` (created on first sync).

### Merge conflicts?
The sync script preserves your personal `enabledPlugins`. If you have custom hooks, they may be overwritten - back them up first.

## Contributing

To update team standards:
1. Edit the files in this repository
2. Commit and push (or just save if using OneDrive)
3. Notify team to run sync script
