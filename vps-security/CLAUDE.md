# VPS Security Monitor

## Project Info
| Field | Value |
|-------|-------|
| **Location** | `/opt/vps-security/` on VPS 165.232.95.6 |
| **Repo** | https://github.com/NickZamnesia/claude-team-config (vps-security subfolder) |
| **Schedule** | Runs every 6 hours via systemd timer |

---

## 🔴 ACTIVE SESSION
| Field | Value |
|-------|-------|
| **Date** | 2026-01-14 |
| **Working On** | Multi-webhook Slack support |
| **Changes Made** | 8 |

---

## Changes This Session
| Time | Change | Files |
|------|--------|-------|
| 21:00 | Added VPS server access info to global CLAUDE.md | `~/.CLAUDE.md` |
| 21:05 | Fixed systemd service to handle missing .env gracefully | `/etc/systemd/system/vps-security.service` |
| 21:06 | Fixed systemd service to treat exit code 1 (warnings) as success | `/etc/systemd/system/vps-security.service` |
| 21:07 | Created .env with Slack webhook URL | `/opt/vps-security/.env` |
| 21:10 | Updated config.yaml with correct firewall ports (22222, 8000, 8080) | `config.yaml` |
| 21:11 | Fixed .env format with export keyword | `/opt/vps-security/.env` |
| 21:20 | Added multi-webhook support to Slack notifier | `notifications/slack.py` |
| 21:22 | Updated .env with both Slack webhooks | `/opt/vps-security/.env` |

---

## Session History
| Date | Activity | Output |
|------|----------|--------|
| 2026-01-14 | Fixed SSH auto-fix not working, systemd service crashing, config drift from GitHub deploys, added multi-webhook Slack support | All checks passing, notifications sent to both Slack workspaces |

---

## Configuration Notes

### Slack Webhooks
Stored locally at: `C:\Users\NickAvéJustAmazingBV\.claude\secrets\slack_webhooks.env`
- SLACK_WEBHOOK_URL_1: Primary workspace (JustAmazing)
- SLACK_WEBHOOK_URL_2: Secondary workspace

### Firewall Allowed Ports
- 22222 (SSH - non-standard)
- 80 (HTTP)
- 443 (HTTPS)
- 8000 (redirect-mapper-backend)
- 8001 (redirect-mapper)
- 8080 (misc services)
- 8085 (structured-data-tool)

### Exit Codes
- 0: All checks passed
- 1: Warnings present (treated as success by systemd)
- 2: Critical issues found
