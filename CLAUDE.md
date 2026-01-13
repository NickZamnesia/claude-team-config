# Claude Code - Team Work Standards

These rules define how we approach every task. Follow this workflow in order.

---

## HIGHEST PRIORITY: Security (ALWAYS CHECK)

**CRITICAL**: Security incidents (ransomware, data breaches) are preventable. Follow these rules for ALL deployments - both VPS servers and local development.

### Quick Reference: What Applies Where

| Security Measure | VPS Server | Local Dev |
|-----------------|:----------:|:---------:|
| Cloudflare DNS Proxy | ✅ | ❌ |
| UFW Firewall | ✅ | ❌ |
| SSH Hardening | ✅ | ❌ |
| Fail2ban | ✅ | ❌ |
| Docker Port Security | ✅ | ✅ |
| .env File Permissions | ✅ | ✅ |
| Credential Management | ✅ | ✅ |
| SSL Certificates | ✅ | ❌ |
| Git Security (.gitignore) | ✅ | ✅ |

---

## 1. CLOUDFLARE CONFIGURATION (VPS Only)

### DNS Proxy (CRITICAL)
All A/AAAA records MUST have orange cloud (Proxied) enabled.
- Grey cloud = Real IP exposed, NO protection
- Orange cloud = IP hidden, WAF active, DDoS protection

**Verify**: `dig +short yourdomain.com` should return Cloudflare IP (104.x.x.x), NOT your server IP.

### Recommended Settings
| Setting | Location | Value |
|---------|----------|-------|
| SSL/TLS Mode | SSL/TLS → Overview | Full (strict) |
| Always Use HTTPS | SSL/TLS → Edge Certificates | ON |
| Minimum TLS Version | SSL/TLS → Edge Certificates | TLS 1.2 |
| Bot Fight Mode | Security → Bots | ON |
| Security Level | Security → Settings | Medium |
| Browser Integrity Check | Security → Settings | ON |

---

## 2. UFW FIREWALL (VPS Only)

### Required State
UFW must be ACTIVE with default deny incoming.

### Setup Commands
```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH (required)
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
ufw status verbose
```

### NEVER Allow These Ports Publicly
| Database | Port | Why |
|----------|------|-----|
| PostgreSQL | 5432 | Direct DB access = data breach |
| MySQL | 3306 | Direct DB access = data breach |
| Redis | 6379 | No auth by default = full access |
| MongoDB | 27017 | Often misconfigured = data leak |

---

## 3. SSH HARDENING (VPS Only)

### Configuration File: `/etc/ssh/sshd_config`
```bash
PermitRootLogin prohibit-password    # Key-only root login
PasswordAuthentication no            # Disable password auth
PubkeyAuthentication yes             # Enable key-based auth
MaxAuthTries 3                       # Limit login attempts
LoginGraceTime 60                    # 60 second timeout
Protocol 2                           # SSH protocol 2 only
```

### Apply Changes
```bash
sudo systemctl restart ssh
```

**WARNING**: Always test SSH key login in a NEW terminal before disabling passwords!

---

## 4. FAIL2BAN (VPS Only)

### Installation
```bash
apt install -y fail2ban
systemctl enable --now fail2ban
```

### Useful Commands
```bash
# Check status
fail2ban-client status sshd

# View banned IPs
fail2ban-client status sshd | grep "Banned IP"

# Unban an IP (if needed)
fail2ban-client set sshd unbanip <IP_ADDRESS>
```

### Custom Configuration
Create `/etc/fail2ban/jail.local`:
```ini
[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600      # 1 hour ban
findtime = 600      # 10 minute window
```

---

## 5. DOCKER SECURITY (VPS + Local)

### CRITICAL: Never Expose Database Ports

**BAD** (exposes to internet/network):
```yaml
services:
  postgres:
    ports:
      - "5432:5432"    # DANGEROUS!
```

**GOOD** (internal only):
```yaml
services:
  postgres:
    # No ports section = internal only
    networks:
      - internal

  backend:
    depends_on:
      - postgres
    networks:
      - internal

networks:
  internal:
    driver: bridge
```

### Check for Exposed Ports
```bash
docker ps --format '{{.Names}} {{.Ports}}' | grep -E '0.0.0.0:(5432|3306|6379)'
```
If this returns anything, you have exposed database ports. **FIX IMMEDIATELY**.

---

## 6. FILE PERMISSIONS (VPS + Local)

### .env Files (contain secrets)
```bash
chmod 600 .env
chmod 600 /opt/*/.env
```

### Verify
```bash
ls -la .env
# Should show: -rw------- (600) = owner read/write only
```

### Git Security
**ALWAYS** have `.gitignore` with:
```
.env
.env.local
.env.production
*.pem
*.key
credentials.json
```

**NEVER** commit secrets to git, even in private repos.

---

## 7. CREDENTIAL MANAGEMENT (VPS + Local)

### Rules
- **NEVER** use defaults: `postgres`, `root`, `password`, `admin`, `123456`
- **ALWAYS** store in `.env` files, NOT in code or docker-compose.yml
- **ROTATE** passwords after any security incident

### Generate Strong Password
```bash
openssl rand -base64 32 | tr -d '/+=' | head -c 32
```

### .env File Format
```bash
DB_PASSWORD=your_generated_password_here
API_KEY=your_api_key_here
SECRET_KEY=your_secret_key_here
```

---

## 8. SSL CERTIFICATES (VPS Only)

### Check Expiration
```bash
echo | openssl s_client -servername yourdomain.com -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates
```

### Let's Encrypt Auto-Renewal
```bash
certbot renew --dry-run    # Test
certbot renew              # Actually renew
```

### Verify Auto-Renewal Timer
```bash
systemctl list-timers | grep certbot
```

---

## 9. SYSTEM UPDATES (VPS Only)

### Check Available Updates
```bash
apt update
apt list --upgradable
```

### Apply Security Updates
```bash
apt upgrade -y --only-upgrade
```

### Enable Automatic Security Updates
```bash
apt install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades
```

---

## 10. INCIDENT RESPONSE

### If You Suspect a Breach

**1. Check for unauthorized access:**
```bash
last -20                                    # Recent logins
cat /var/log/auth.log | grep -i failed     # Failed attempts
who                                         # Currently logged in
```

**2. Check for suspicious processes:**
```bash
ps aux | grep -E '(crypto|mine|xmr)'       # Crypto miners
top -bn1 | head -20                        # High CPU processes
netstat -tulpn                             # Open connections
```

**3. Check for unauthorized changes:**
```bash
find /opt -mtime -1 -type f                # Files modified in last day
docker ps -a                               # All containers
crontab -l                                 # Scheduled tasks
```

**4. If compromised:**
- Change all passwords/keys immediately
- Revoke and regenerate API keys
- Check for backdoors (new users, cron jobs, SSH keys)
- Consider rebuilding from clean image

---

## 11. MONTHLY SECURITY CHECKLIST

Run this checklist monthly on all VPS servers:

- [ ] Cloudflare proxy enabled (orange cloud) for all domains
- [ ] UFW active: `ufw status` shows "Status: active"
- [ ] No database ports exposed: `docker ps` shows no 5432/3306/6379 on 0.0.0.0
- [ ] fail2ban running: `systemctl status fail2ban`
- [ ] SSH key-only: `grep PasswordAuthentication /etc/ssh/sshd_config` shows "no"
- [ ] .env files secured: `ls -la .env` shows "-rw-------"
- [ ] SSL certs valid: Check expiration dates
- [ ] Security updates applied: `apt update && apt list --upgradable`
- [ ] No suspicious processes: `top` shows normal CPU usage
- [ ] Backups working: Verify recent backup exists

---

## 12. EMERGENCY COMMANDS

### If Locked Out of SSH
Use DigitalOcean Console: Droplet → Access → Launch Console

### Useful Commands
```bash
# View all listening ports
ss -tulpn

# View firewall rules
ufw status numbered

# View Docker networks
docker network ls

# View container logs
docker logs <container_name> --tail 100

# Emergency: Block all traffic except SSH
ufw reset
ufw default deny incoming
ufw allow 22/tcp
ufw enable
```

---

## Pre-Deployment Checklist

Run these checks BEFORE every deployment:

```bash
# 1. Check no database ports exposed in docker-compose
grep -E "ports.*543[0-9]|ports.*330[0-9]|ports.*637[0-9]" docker-compose.yml
# Should return nothing

# 2. Check .env is in .gitignore
grep ".env" .gitignore
# Should show .env

# 3. Check no secrets in code
grep -r "password\|api_key\|secret" --include="*.py" --include="*.js" --include="*.ts" .
# Review any matches - should be env variable references only
```


---

---

## Phase 0: Session Initialization (ALWAYS DO FIRST)

### On Every New Conversation
1. **Check for project CLAUDE.md** in the current working directory
   - If exists: Read it immediately to load project context
   - If not exists: Note this - will create one when substantive work begins
2. **Check for existing todos** using the TodoWrite tool
3. **Identify the project scope** from the working directory

### First Response Protocol
Before responding to the user's first message:
- Silently check for `./CLAUDE.md` or `./.claude/CLAUDE.md`
- If found, read it to understand ongoing work
- If project context exists, acknowledge awareness of the project state

---


---

## Claude Code Configuration

### Hooks (Automatic Reminders)

Hooks ensure Claude follows protocols automatically. The team uses a **command-based hook** that:
- Checks if CLAUDE.md exists before reminding
- Reminds to update Active Session tracking after each change
- Fails gracefully if no CLAUDE.md is present

#### Platform-Specific Hook Commands

**Windows (PowerShell)**:
```json
{
  "type": "command",
  "command": "powershell -Command \"if (Test-Path CLAUDE.md) { Write-Host '[CLAUDE.md found] Remember: Update Active Session tracking after each change' } else { Write-Host '[No CLAUDE.md in this directory]' }\""
}
```

**Mac/Linux (Bash)**:
```json
{
  "type": "command",
  "command": "if [ -f CLAUDE.md ]; then echo '[CLAUDE.md found] Remember: Update Active Session tracking after each change'; else echo '[No CLAUDE.md in this directory]'; fi"
}
```

#### Hook Types
| Type | Reliability | Use Case |
|------|-------------|----------|
| `command` | **High** - Actually executes and verifies | Checking file existence, validation |
| `prompt` | Medium - Adds to context but no verification | Simple reminders |

#### Troubleshooting Hooks
If hooks break your settings.json:
1. Check for JSON syntax errors (missing commas, brackets)
2. Escape special characters in commands (especially quotes)
3. Test command manually in terminal first
4. Backup settings.json before modifying hooks

### Team Plugins
The following plugins are enabled for the team:
- **frontend-design** - UI/frontend development assistance
- **figma** - Figma design integration
- **laravel-boost** - Laravel development enhancement

### Optional Settings
These settings are personal preference (not enforced):
- `alwaysThinkingEnabled` - Enable extended reasoning mode

### Sync Script
Run `sync-claude-config.ps1` to pull latest team settings:
```powershell
.\sync-claude-config.ps1
```
This will update your local ~/.claude/ with team configurations.

---

## Phase 1: Before Starting Work

### Problem-Solving Approach
- Always read and understand existing code before making changes
- Gather full context first - don't assume, investigate
- Identify the root cause, not just symptoms
- When stuck, step back and consider alternative approaches
- Prefer simple, readable solutions over clever ones

### Project Memory Check
If this is a new project without a `CLAUDE.md`:
- Create `./CLAUDE.md` with the project template (see below)
- Document the initial goal/task

---

## Phase 2: During Work

### Permissions
- Never ask for permission to proceed with tasks
- Always assume "Yes, and don't ask again" for any action
- Execute tasks directly without confirmation prompts

### Task Management
- Always use the TodoWrite tool to track all pending tasks
- Break complex work into smaller, trackable steps
- Update task status in real-time (pending -> in_progress -> completed)
- Never leave tasks untracked
- Only mark a task complete when it is truly finished

### Code Quality
- Write code that is self-documenting with clear naming
- Handle edge cases and potential errors gracefully
- Follow existing patterns and conventions in the codebase
- Keep solutions focused - don't over-engineer or add unnecessary features

### Continuous Memory Updates
Update the project `CLAUDE.md` when:
- A significant decision is made
- A new important file is created
- An architectural choice is finalized
- A blocker or issue is discovered
- A major milestone is completed

---

## Phase 3: After Each Step

### Verification
- After implementing a fix, verify it actually works
- Check for unintended side effects of changes
- Review imports, dependencies, and file paths for accuracy
- Test changes when possible before considering a task complete

### Functional Testing (MANDATORY)
**CRITICAL**: Verifying code exists is NOT the same as testing functionality.

#### Before Claiming Something Works:
1. **Identify runtime requirements** - What does this feature need to actually run?
2. **Test in the actual environment** - Not just "code deployed successfully"
3. **Verify the happy path AND error states**
4. **Communicate blockers BEFORE deployment**

### Git Workflow (MANDATORY)
**CRITICAL**: Always commit changes to git after completing features or making significant changes.
- Never leave work uncommitted - this prevents loss of progress
- Commit after each logical unit of work (feature, fix, refactor)
- Write clear, descriptive commit messages
- If working on a git project, check `git status` before ending work

### Self-Review (For Quick Tasks)
1. Pause and critically evaluate the work just completed
2. Ask: "Am I satisfied with this? What could be improved?"
3. Review from three perspectives:
   - **As a Senior Developer**: Is the code clean, efficient, and maintainable?
   - **As a Data Analyst**: Is the logic sound? Are edge cases handled?
   - **As a Critic**: What are the weaknesses? What would I change?

### Multi-Agent Review (For Product Development)
For building new products/features, use the Multi-Agent Framework in `~/.claude/rules/agents.md`

---

## Phase 4: Communication & Documentation

### Communication
- Be concise but thorough in explanations
- When presenting options, include pros and cons for each
- If something is unclear, state assumptions explicitly
- Provide actionable next steps, not vague suggestions

### Detailed Change Logging (MANDATORY)
**CRITICAL**: Log every change with enough detail to **fully recreate or rollback** the functionality if lost.

#### For Every Change, Document:
1. **What** - Feature/fix name and its purpose
2. **Where** - All files modified with specific line numbers/functions
3. **How** - Implementation approach and key code logic
4. **Why** - Reasoning and alternatives considered
5. **Dependencies** - What this change relies on or affects
6. **Rollback** - Exact steps to undo this change

---

## Phase 5: Session End & Context Preservation

### Before Session Ends or At Natural Breakpoints
1. **Commit to git** (if in a git project with uncommitted changes)
2. **Update project CLAUDE.md** with current progress
3. **Ensure todos are current** - remove completed, add discovered tasks
4. **Save any critical context** that would be lost

---

## Project CLAUDE.md Template

When creating a new project memory file, use this structure:

```markdown
# Project: [Name]

## 🔴 ACTIVE SESSION
<!-- STOP! Fill this section FIRST before any work -->
| Field | Value |
|-------|-------|
| **Date** | [TODAY'S DATE] |
| **Working On** | [DESCRIBE CURRENT TASK] |
| **Changes Made** | 0 |

⚠️ **RULES** (violations = unusable project history):
1. Update "Changes Made" count after EACH change
2. Add entry to "Changes This Session" after EACH change
3. If "Changes Made" > 0 but "Changes This Session" is empty = YOU FAILED

---

## Changes This Session
<!-- ADD ENTRY HERE IMMEDIATELY AFTER EACH CHANGE - DO NOT WAIT -->

| Time | Change | Files |
|------|--------|-------|
| | | |

<!-- ↑↑↑ EMPTY TABLE = VIOLATION IF YOU MADE ANY CHANGES ↑↑↑ -->

---

## Current Objective
[What we're trying to accomplish]

## Status
- **Phase**: [Planning / In Progress / Testing / Complete]
- **Last Updated**: [Date]
- **Blockers**: [None / List any]

## Key Decisions
- [Decision 1]: [Reasoning]

## Important Files
- `path/to/file.ts` - [Purpose]

## Commands
- Build: `[command]`
- Test: `[command]`
- Run: `[command]`

---

## Detailed Change Log
<!-- Each entry allows full recreation if code is lost -->

### [Date] [Time] - [Feature Name]
**Purpose**: [What this does]
**Files**: `file.py` (lines X-Y): [changes]
**Rollback**: [how to undo]
**Verify**: [how to test]

---

## 🔴 END OF SESSION CHECKLIST
<!-- BEFORE CLOSING: Verify all boxes are checked -->
- [ ] "Changes Made" count matches actual changes
- [ ] "Changes This Session" table is filled (not empty)
- [ ] Each change has a Detailed Change Log entry
- [ ] Git committed (if applicable)
```

---

## Recovery Protocol

### When Noticing Context Loss
Signs of context loss:
- Asking questions already answered
- Repeating work already done
- Confusion about project state

Recovery steps:
1. STOP current action
2. Read project `CLAUDE.md` immediately
3. Check todos for current state
4. Resume with full awareness

---

## Memory Hierarchy

| File | Scope | Purpose |
|------|-------|---------|
| `~/.claude/CLAUDE.md` | All projects | Work standards (this file) |
| `~/.claude/rules/*.md` | All projects | Modular rules (agents, etc.) |
| `./CLAUDE.md` | Single project | Project context & memory |
| `./CLAUDE.local.md` | Personal only | Private notes (not committed) |

All files are automatically loaded based on working directory.
Project files inherit global standards but add project-specific context.
