#!/bin/bash
#
# VPS Security Monitor - Deployment Script
# =========================================
#
# This script deploys the security monitor to your VPS.
#
# Usage:
#   ./deploy.sh <VPS_IP> [SLACK_WEBHOOK_URL]
#
# Example:
#   ./deploy.sh 165.232.95.6 https://hooks.slack.com/services/xxx/yyy/zzz
#

set -e

VPS_IP="${1:-165.232.95.6}"
SLACK_WEBHOOK="${2:-}"
REMOTE_DIR="/opt/vps-security"

echo "=============================================="
echo "VPS Security Monitor - Deployment"
echo "=============================================="
echo ""
echo "Target: root@${VPS_IP}"
echo "Remote directory: ${REMOTE_DIR}"
echo ""

# Check SSH connection
echo "Checking SSH connection..."
if ! ssh -o ConnectTimeout=5 root@${VPS_IP} "echo 'SSH OK'" > /dev/null 2>&1; then
    echo "ERROR: Cannot connect to root@${VPS_IP}"
    echo "Make sure you have SSH access configured."
    exit 1
fi

echo "SSH connection OK"
echo ""

# Create remote directory structure
echo "Creating directory structure on VPS..."
ssh root@${VPS_IP} "mkdir -p ${REMOTE_DIR}/{checks,remediation,notifications,logs,backups,systemd}"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Copy files to VPS
echo "Copying files to VPS..."
scp -r "${SCRIPT_DIR}"/*.py "${SCRIPT_DIR}"/*.yaml "${SCRIPT_DIR}"/*.txt root@${VPS_IP}:${REMOTE_DIR}/
scp -r "${SCRIPT_DIR}"/checks/*.py root@${VPS_IP}:${REMOTE_DIR}/checks/
scp -r "${SCRIPT_DIR}"/remediation/*.py root@${VPS_IP}:${REMOTE_DIR}/remediation/
scp -r "${SCRIPT_DIR}"/notifications/*.py root@${VPS_IP}:${REMOTE_DIR}/notifications/
scp -r "${SCRIPT_DIR}"/systemd/*.service "${SCRIPT_DIR}"/systemd/*.timer root@${VPS_IP}:${REMOTE_DIR}/systemd/

# Create .env file with Slack webhook
if [ -n "${SLACK_WEBHOOK}" ]; then
    echo "Creating .env file with Slack webhook..."
    ssh root@${VPS_IP} "echo 'SLACK_WEBHOOK_URL=${SLACK_WEBHOOK}' > ${REMOTE_DIR}/.env && chmod 600 ${REMOTE_DIR}/.env"
else
    echo ""
    echo "WARNING: No Slack webhook URL provided."
    echo "Create ${REMOTE_DIR}/.env manually with:"
    echo "  SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz"
    echo ""
fi

# Install Python dependencies
echo "Installing Python dependencies..."
ssh root@${VPS_IP} "pip3 install -q pyyaml requests"

# Install systemd service and timer
echo "Installing systemd service and timer..."
ssh root@${VPS_IP} "
    cp ${REMOTE_DIR}/systemd/vps-security.service /etc/systemd/system/
    cp ${REMOTE_DIR}/systemd/vps-security.timer /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable vps-security.timer
    systemctl start vps-security.timer
"

# Verify installation
echo ""
echo "=============================================="
echo "Deployment Complete!"
echo "=============================================="
echo ""
echo "Verifying installation..."
echo ""

# Check timer status
echo "Timer status:"
ssh root@${VPS_IP} "systemctl status vps-security.timer --no-pager" || true

echo ""
echo "Next scheduled runs:"
ssh root@${VPS_IP} "systemctl list-timers | grep vps-security" || true

echo ""
echo "=============================================="
echo "Quick Commands"
echo "=============================================="
echo ""
echo "Run a manual scan:"
echo "  ssh root@${VPS_IP} 'python3 ${REMOTE_DIR}/vps_security.py --verbose'"
echo ""
echo "Test Slack notifications:"
echo "  ssh root@${VPS_IP} 'python3 ${REMOTE_DIR}/vps_security.py --test-slack'"
echo ""
echo "View logs:"
echo "  ssh root@${VPS_IP} 'tail -50 ${REMOTE_DIR}/logs/security.log'"
echo ""
echo "Check timer status:"
echo "  ssh root@${VPS_IP} 'systemctl status vps-security.timer'"
echo ""
