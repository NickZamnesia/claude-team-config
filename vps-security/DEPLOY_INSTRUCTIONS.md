# VPS Security Monitor - Easy Setup Guide

## What Is This?

This is a security guard for your VPS server. It automatically:
- Checks your server for security problems every 6 hours
- Fixes simple issues automatically (like firewall settings)
- Sends you a Slack message when something needs attention

**You install it once, and it protects your server 24/7.**

---

## Before You Start

You'll need:
- [ ] Access to your VPS (the IP address and ability to SSH in)
- [ ] Your Slack webhook URL (ask Nick if you don't have it)

---

## Installation (10 minutes)

### Step 1: Connect to Your VPS

Open your terminal (Mac/Linux) or PowerShell (Windows) and connect:

```bash
ssh root@YOUR_VPS_IP
```

Replace `YOUR_VPS_IP` with your actual server IP (like `165.232.95.6`).

You'll be asked for your password or it will use your SSH key.

**You're now connected when you see something like:** `root@your-server:~#`

---

### Step 2: Download the Security Tool

Copy and paste this entire command (it's one line):

```bash
git clone https://github.com/NickZamnesia/vps-security.git /opt/vps-security
```

**What this does:** Downloads all the security files to your server.

**You'll see something like:**
```
Cloning into '/opt/vps-security'...
remote: Enumerating objects: 42, done.
...
```

---

### Step 3: Run the Installer

Copy and paste these commands one at a time:

```bash
cd /opt/vps-security
```

```bash
chmod +x install.sh
```

```bash
./install.sh
```

**What these do:**
1. Go into the security folder
2. Make the installer runnable
3. Run the installer

---

### Step 4: Enter Your Slack Webhook

The installer will ask for your Slack webhook URL:

```
Enter Slack webhook URL:
```

Paste the webhook URL and press Enter.

**Don't have the webhook?** Ask Nick or check the team Slack channel description.

---

### Step 5: Configure Your Projects

The installer will finish and show "Installation Complete!"

Now you need to tell it about YOUR projects. Open the config file:

```bash
nano /opt/vps-security/config.yaml
```

Find the `projects:` section and change it to match your setup:

```yaml
projects:
  - name: my-project-name
    path: /opt/my-project
    docker_compose: /opt/my-project/docker-compose.yml
    allowed_ports: [8001]
    database_type: postgresql
```

**Change these values:**
- `name`: Whatever you want to call your project
- `path`: Where your project files are (usually `/opt/something`)
- `allowed_ports`: What port your app runs on
- `database_type`: `postgresql`, `mysql`, or `mongodb`

**To save and exit nano:**
1. Press `Ctrl + X`
2. Press `Y` (yes, save)
3. Press `Enter`

---

### Step 6: Test It Works

Run a manual security scan:

```bash
python3 /opt/vps-security/vps_security.py --verbose
```

You should see output showing what it checked. If everything is secure, great! If there are warnings, they'll be shown.

**Test Slack notifications:**

```bash
python3 /opt/vps-security/vps_security.py --test-slack
```

Check your Slack - you should receive a test message.

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
