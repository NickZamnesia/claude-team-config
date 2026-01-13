# Claude Code - Team Work Standards

These rules define how we approach every task. Follow this workflow in order.

---

## HIGHEST PRIORITY: VPS Security (ALWAYS CHECK)

**CRITICAL**: Security incidents (ransomware, data breaches) are preventable. Follow these rules for ALL VPS deployments.

### Layer 1: Network Security (MANDATORY)

#### Firewall (UFW)
```bash
# Enable on first VPS setup
ufw enable
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
# Add app-specific ports as needed (e.g., 8001 for redirect-mapper)
ufw status verbose
```

#### Database Ports - NEVER EXPOSE
| Database | Port | docker-compose.yml |
|----------|------|-------------------|
| PostgreSQL | 5432 | NO `ports:` section |
| MySQL | 3306 | NO `ports:` section |
| Redis | 6379 | NO `ports:` section |

**BAD**: `ports: - "5432:5432"` (exposes to internet)
**GOOD**: No ports section (internal Docker network only)

### Layer 2: Web Application Firewall (RECOMMENDED)

Install SafeLine WAF to protect web apps from SQL injection, XSS, brute-force:
```bash
# Install SafeLine on VPS
bash -c "$(curl -fsSLk https://waf.chaitin.com/release/latest/setup.sh)"
# Access dashboard at https://YOUR_VPS_IP:9443
# Route traffic: Internet → SafeLine → nginx → your apps
```

### Layer 3: SSH Protection (RECOMMENDED)

Install fail2ban to block brute-force SSH attacks:
```bash
apt install fail2ban -y
systemctl enable fail2ban
systemctl start fail2ban
# Check status: fail2ban-client status sshd
```

### Layer 4: Credentials

**Strong passwords only**:
```bash
# Generate secure password
openssl rand -base64 32 | tr -d '/+=' | head -c 32
```

**Rules**:
- NEVER use defaults: `postgres`, `root`, `password`, `admin`
- Store in `.env` files, NOT in docker-compose.yml or code
- Rotate passwords after any security incident

### Pre-Deployment Checklist

Run these checks BEFORE every deployment:
```bash
# 1. Check no database ports exposed
grep -E "ports.*543[0-9]|ports.*330[0-9]|ports.*637[0-9]" docker-compose.yml
# Should return nothing

# 2. Check firewall is active
ssh root@SERVER "ufw status"

# 3. Check no databases publicly accessible
ssh root@SERVER "docker ps --format '{{.Names}} {{.Ports}}' | grep -E 'postgres|mysql|redis'"
# Should show no 0.0.0.0 bindings
```

### New VPS Setup Checklist

When setting up a NEW VPS:
- [ ] Update system: `apt update && apt upgrade -y`
- [ ] Enable UFW firewall with only necessary ports
- [ ] Install fail2ban for SSH protection
- [ ] Install SafeLine WAF (if hosting web apps)
- [ ] Create non-root user for daily operations
- [ ] Disable root password login (SSH keys only)
- [ ] Set up automated backups

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
