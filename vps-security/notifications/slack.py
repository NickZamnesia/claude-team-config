"""Slack webhook notifications for security alerts."""

import os
import socket
import requests
from datetime import datetime
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Send security scan results to Slack."""

    def __init__(self, config: dict):
        """Initialize Slack notifier.

        Args:
            config: Configuration dictionary with notifications.slack settings
        """
        self.config = config
        slack_config = config.get('notifications', {}).get('slack', {})

        # Get webhook URL from config or environment
        self.webhook_url = slack_config.get('webhook_url', '')
        if self.webhook_url.startswith('${') and self.webhook_url.endswith('}'):
            # Environment variable reference
            env_var = self.webhook_url[2:-1]
            self.webhook_url = os.environ.get(env_var, '')

        self.enabled = slack_config.get('enabled', True) and bool(self.webhook_url)
        self.mention_on_critical = slack_config.get('mention_on_critical', '')
        self.include_hostname = slack_config.get('include_hostname', True)

    def send_summary(self, auto_fixed: List[Tuple], alerts: List,
                     all_ok: bool = False) -> bool:
        """Send a security scan summary to Slack.

        Args:
            auto_fixed: List of (CheckResult, RemediationResult) tuples
            alerts: List of CheckResult objects that need attention
            all_ok: Whether all checks passed

        Returns:
            True if sent successfully
        """
        if not self.enabled:
            logger.warning("Slack notifications disabled (no webhook URL)")
            return False

        try:
            blocks = self._build_message_blocks(auto_fixed, alerts, all_ok)
            return self._send_blocks(blocks)
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    def send_test_message(self) -> bool:
        """Send a test message to verify Slack integration.

        Returns:
            True if sent successfully
        """
        if not self.enabled:
            logger.warning("Slack notifications disabled (no webhook URL)")
            return False

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "VPS Security Monitor - Test Message"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Test notification from VPS Security Monitor*\n\n"
                            f"Host: `{self._get_hostname()}`\n"
                            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            f"If you see this message, Slack notifications are working correctly."
                }
            }
        ]

        return self._send_blocks(blocks)

    def _build_message_blocks(self, auto_fixed: List[Tuple], alerts: List,
                              all_ok: bool) -> List[dict]:
        """Build Slack message blocks for the summary.

        Args:
            auto_fixed: List of (CheckResult, RemediationResult) tuples
            alerts: List of CheckResult objects
            all_ok: Whether all checks passed

        Returns:
            List of Slack block objects
        """
        hostname = self._get_hostname() if self.include_hostname else None
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

        blocks = []

        # Header
        header_text = f"VPS Security Scan - {timestamp}"
        if hostname:
            header_text = f"[{hostname}] {header_text}"

        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": header_text
            }
        })

        # All OK case
        if all_ok and not auto_fixed and not alerts:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*All checks passed* - No security issues detected"
                }
            })
            return blocks

        # Critical alerts (with mention)
        from checks.base import Severity
        critical_alerts = [a for a in alerts if a.severity == Severity.CRITICAL]
        if critical_alerts:
            mention = self.mention_on_critical if critical_alerts else ""
            alert_text = f"*CRITICAL ALERTS: {len(critical_alerts)}*\n"
            alert_text += "\n".join([f"- {a.message}" for a in critical_alerts])

            if mention:
                alert_text = f"{mention}\n\n{alert_text}"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": alert_text
                }
            })

            # Add details for critical alerts
            for alert in critical_alerts:
                if alert.details:
                    detail_text = "\n".join([f"  - {d}" for d in alert.details[:5]])
                    if len(alert.details) > 5:
                        detail_text += f"\n  ... and {len(alert.details) - 5} more"
                    blocks.append({
                        "type": "context",
                        "elements": [{
                            "type": "mrkdwn",
                            "text": detail_text
                        }]
                    })

        # Auto-remediated items
        if auto_fixed:
            fix_text = f"*Auto-remediated: {len(auto_fixed)}*\n"
            fix_text += "\n".join([
                f"- {r[0].check_name}: {r[1].action}"
                for r in auto_fixed
            ])

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": fix_text
                }
            })

        # Warnings
        warning_alerts = [a for a in alerts if a.severity == Severity.WARNING]
        if warning_alerts:
            warn_text = f"*Warnings: {len(warning_alerts)}*\n"
            warn_text += "\n".join([f"- {a.message}" for a in warning_alerts])

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": warn_text
                }
            })

        # Info items
        info_alerts = [a for a in alerts if a.severity == Severity.INFO]
        if info_alerts:
            info_text = f"*Info: {len(info_alerts)}*\n"
            info_text += "\n".join([f"- {a.message}" for a in info_alerts])

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": info_text
                }
            })

        # Divider and footer
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"VPS Security Monitor | Next scan in 6 hours"
            }]
        })

        return blocks

    def _send_blocks(self, blocks: List[dict]) -> bool:
        """Send blocks to Slack webhook.

        Args:
            blocks: List of Slack block objects

        Returns:
            True if sent successfully
        """
        try:
            response = requests.post(
                self.webhook_url,
                json={"blocks": blocks},
                timeout=10
            )

            if response.status_code == 200:
                logger.info("Slack notification sent successfully")
                return True
            else:
                logger.error(f"Slack API error: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.Timeout:
            logger.error("Slack webhook request timed out")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Slack webhook request failed: {e}")
            return False

    def _get_hostname(self) -> str:
        """Get the hostname of this machine."""
        try:
            return socket.gethostname()
        except Exception:
            return "unknown"
