#!/bin/bash
#
# VPS Security Monitor - Installation Script
# ==========================================
#
# This script installs the VPS Security Monitor on Ubuntu/Debian servers.
# Run as root on your VPS after copying all files.
#
# Usage:
#   chmod +x install.sh
#   ./install.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================================="
echo "  VPS Security Monitor - Installation"
echo "=============================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: Please run as root${NC}"
    echo "Usage: sudo ./install.sh"
    exit 1
fi

# Detect script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/vps-security"

echo "Source directory: ${SCRIPT_DIR}"
echo "Install directory: ${INSTALL_DIR}"
echo ""

# Step 1: Create installation directory
echo -e "${YELLOW}[1/8] Creating directory structure...${NC}"
mkdir -p "${INSTALL_DIR}"/{checks,remediation,notifications,logs,backups,systemd}

# Step 2: Copy files
echo -e "${YELLOW}[2/8] Copying files...${NC}"
cp "${SCRIPT_DIR}"/*.py "${INSTALL_DIR}/" 2>/dev/null || true
cp "${SCRIPT_DIR}"/*.yaml "${INSTALL_DIR}/"
cp "${SCRIPT_DIR}"/*.txt "${INSTALL_DIR}/" 2>/dev/null || true
cp "${SCRIPT_DIR}"/checks/*.py "${INSTALL_DIR}/checks/"
cp "${SCRIPT_DIR}"/remediation/*.py "${INSTALL_DIR}/remediation/"
cp "${SCRIPT_DIR}"/notifications/*.py "${INSTALL_DIR}/notifications/"
cp "${SCRIPT_DIR}"/systemd/*.service "${SCRIPT_DIR}"/systemd/*.timer "${INSTALL_DIR}/systemd/"

# Step 3: Create .env file with Slack webhook
echo -e "${YELLOW}[3/8] Configuring Slack webhook...${NC}"
if [ -f "${INSTALL_DIR}/.env" ]; then
    echo "  .env file already exists, keeping existing configuration"
else
    # Check if SLACK_WEBHOOK_URL is passed as environment variable
    if [ -z "$SLACK_WEBHOOK_URL" ]; then
        echo ""
        echo -e "${YELLOW}  Slack webhook URL is required for security alerts.${NC}"
        echo "  Get it from: https://api.slack.com/apps → Your App → Incoming Webhooks"
        echo ""
        read -p "  Enter Slack webhook URL: " SLACK_WEBHOOK_URL
    fi

    if [ -z "$SLACK_WEBHOOK_URL" ]; then
        echo -e "${RED}  WARNING: No webhook URL provided. Slack notifications will not work.${NC}"
        SLACK_WEBHOOK_URL="YOUR_SLACK_WEBHOOK_URL"
    fi

    cat > "${INSTALL_DIR}/.env" << EOF
# VPS Security Monitor - Environment Variables
# Get webhook URL from: https://api.slack.com/apps
SLACK_WEBHOOK_URL=$SLACK_WEBHOOK_URL
EOF
    chmod 600 "${INSTALL_DIR}/.env"
    echo "  Created .env with Slack webhook"
fi

# Step 4: Install Python dependencies
echo -e "${YELLOW}[4/8] Installing Python dependencies...${NC}"
if command -v apt &> /dev/null; then
    # Debian/Ubuntu - prefer system packages (PEP 668 compliant)
    apt update -qq
    apt install -y -qq python3-yaml python3-requests
    echo "  Installed python3-yaml, python3-requests via apt"
else
    # Fallback to pip
    pip3 install -q pyyaml requests
    echo "  Installed via pip"
fi

# Step 5: Install systemd service and timer
echo -e "${YELLOW}[5/8] Installing systemd service and timer...${NC}"
cp "${INSTALL_DIR}/systemd/vps-security.service" /etc/systemd/system/
cp "${INSTALL_DIR}/systemd/vps-security.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable vps-security.timer
systemctl start vps-security.timer
echo "  Timer enabled and started"

# Step 6: Install and configure fail2ban
echo -e "${YELLOW}[6/8] Installing fail2ban...${NC}"
if ! command -v fail2ban-client &> /dev/null; then
    apt install -y -qq fail2ban
    echo "  fail2ban installed"
fi

# Detect SSH port (check systemd socket override first)
SSH_PORT=22
if [ -f /etc/systemd/system/ssh.socket.d/override.conf ]; then
    SSH_PORT=$(grep "ListenStream=" /etc/systemd/system/ssh.socket.d/override.conf | grep -oP '\d+' | head -1)
elif grep -q "^Port " /etc/ssh/sshd_config 2>/dev/null; then
    SSH_PORT=$(grep "^Port " /etc/ssh/sshd_config | awk '{print $2}')
fi

# Configure fail2ban with aggressive settings
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
# 24 hour ban
bantime = 24h
# 10 minute window for counting failures
findtime = 10m
# 3 failed attempts = ban
maxretry = 3
# Use aggressive ban action
banaction = iptables-multiport

[sshd]
enabled = true
port = ${SSH_PORT}
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 24h
EOF

systemctl enable fail2ban
systemctl restart fail2ban
echo "  fail2ban configured (port ${SSH_PORT}, 3 attempts = 24h ban)"

# Step 7: Harden SSH (alert only, don't auto-change)
echo -e "${YELLOW}[7/8] Checking SSH security...${NC}"
SSH_ISSUES=0

if grep -q "^PermitRootLogin yes" /etc/ssh/sshd_config 2>/dev/null; then
    echo -e "  ${RED}WARNING: PermitRootLogin is 'yes' - recommend changing to 'prohibit-password'${NC}"
    SSH_ISSUES=$((SSH_ISSUES+1))
fi

if ! grep -q "^PasswordAuthentication no" /etc/ssh/sshd_config 2>/dev/null; then
    echo -e "  ${RED}WARNING: PasswordAuthentication should be 'no' - use key-based auth only${NC}"
    SSH_ISSUES=$((SSH_ISSUES+1))
fi

if [ ${SSH_ISSUES} -eq 0 ]; then
    echo "  SSH configuration looks secure"
else
    echo ""
    echo -e "  ${YELLOW}To fix SSH issues, add to /etc/ssh/sshd_config:${NC}"
    echo "    PermitRootLogin prohibit-password"
    echo "    PasswordAuthentication no"
    echo "    PubkeyAuthentication yes"
    echo "  Then run: systemctl restart sshd"
fi

# Step 8: Set permissions
echo -e "${YELLOW}[8/8] Setting file permissions...${NC}"
chmod 600 "${INSTALL_DIR}/.env"
chmod 755 "${INSTALL_DIR}"/*.py
chmod 755 "${INSTALL_DIR}"/checks/*.py
chmod 755 "${INSTALL_DIR}"/remediation/*.py
chmod 755 "${INSTALL_DIR}"/notifications/*.py
echo "  Permissions set"

# Create empty log file
touch "${INSTALL_DIR}/logs/security.log"

echo ""
echo -e "${GREEN}=============================================="
echo "  Installation Complete!"
echo "==============================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Edit config.yaml to add your projects:"
echo "   nano ${INSTALL_DIR}/config.yaml"
echo ""
echo "2. Run a manual scan to verify:"
echo "   python3 ${INSTALL_DIR}/vps_security.py --verbose"
echo ""
echo "3. Test Slack notification:"
echo "   python3 ${INSTALL_DIR}/vps_security.py --test-slack"
echo ""
echo "4. Check timer status:"
echo "   systemctl list-timers | grep vps-security"
echo ""
echo "Automatic scans run every 6 hours."
echo "Logs: ${INSTALL_DIR}/logs/security.log"
echo ""
