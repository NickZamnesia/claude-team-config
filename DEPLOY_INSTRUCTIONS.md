# VPS Security Monitor - Easy Setup Guide

## What Is This?

This is a security guard for your VPS server. It automatically:
- Checks your server for security problems every 6 hours
- Fixes simple issues automatically (like firewall settings)
- Sends you a Slack message when something needs attention

**You install it once, and it protects your server 24/7.**

---

## Installation (2 minutes)

### Step 1: Connect to Your VPS

Open your terminal and type (replace YOUR_VPS_IP with your server's IP address):

```
ssh root@YOUR_VPS_IP
```

Press Enter. Type your password if asked.

**You're connected when you see:** `root@something:~#`

---

### Step 2: Install Everything

Copy this ENTIRE block (all 3 lines), paste it, and press Enter:

```bash
git clone https://github.com/NickZamnesia/claude-team-config.git /tmp/setup && cd /tmp/setup/vps-security && chmod +x install.sh && ./install.sh
```

The installer will ask for a Slack webhook URL. Paste this:

```
https://hooks.slack.com/services/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
```

---

### Step 3: Add Your Project

The installer asks you to edit the config. When the editor opens, find `projects:` and change it to YOUR project:

```yaml
projects:
  - name: my-app
    path: /opt/my-app
    docker_compose: /opt/my-app/docker-compose.yml
    allowed_ports: [8001]
    database_type: postgresql
```

**To save:** Press `Ctrl + X`, then `Y`, then `Enter`

---

### Step 4: Test It

```bash
python3 /opt/vps-security/vps_security.py --test-slack
```

Check Slack - you should get a test message.

---

## You're Done! 🎉

The security monitor will now run automatically every 6 hours.

You'll get Slack messages when:
- A security issue is found
- Something was automatically fixed
- SSL certificates are expiring

---

## Common Questions

### "How do I know it's running?"

```bash
systemctl status vps-security.timer
```

Look for "active (waiting)" - that means it's scheduled and working.

### "How do I run a scan right now?"

```bash
python3 /opt/vps-security/vps_security.py --verbose
```

### "How do I see the logs?"

```bash
tail -100 /opt/vps-security/logs/security.log
```

### "I'm getting too many failed login alerts"

Your SSH port might still be on the default (22). Consider changing it:

1. Create the override file:
```bash
mkdir -p /etc/systemd/system/ssh.socket.d
nano /etc/systemd/system/ssh.socket.d/override.conf
```

2. Paste this content:
```ini
[Socket]
ListenStream=
ListenStream=0.0.0.0:22222
ListenStream=[::]:22222
```

3. Save (Ctrl+X, Y, Enter) and restart:
```bash
systemctl daemon-reload
systemctl restart ssh.socket
ufw allow 22222/tcp
ufw delete allow 22/tcp
```

4. **Important:** Your new SSH port is now 22222. Connect with:
```bash
ssh -p 22222 root@YOUR_VPS_IP
```

### "How do I update to the latest version?"

```bash
cd /opt/vps-security
git pull
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Run scan now | `python3 /opt/vps-security/vps_security.py --verbose` |
| Test Slack | `python3 /opt/vps-security/vps_security.py --test-slack` |
| View logs | `tail -100 /opt/vps-security/logs/security.log` |
| Check timer | `systemctl status vps-security.timer` |
| Edit config | `nano /opt/vps-security/config.yaml` |
| Update | `cd /opt/vps-security && git pull` |

---

## Need Help?

1. Check the logs first: `tail -100 /opt/vps-security/logs/security.log`
2. Ask in the team Slack channel
3. Contact Nick

---

*Security monitoring by Just Amazing BV*
