"""Slack webhook notifications for security alerts."""

import os
import socket
import requests
from datetime import datetime
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Send security scan results to Slack (supports multiple webhooks)."""

    def __init__(self, config: dict):
        """Initialize Slack notifier.

        Args:
            config: Configuration dictionary with notifications.slack settings
        """
        self.config = config
        slack_config = config.get('notifications', {}).get('slack', {})

        # Support multiple webhook URLs
        self.webhook_urls = []

        # Check for single webhook (backward compatible)
        single_url = slack_config.get('webhook_url', '')
        if single_url.startswith('${') and single_url.endswith('}'):
            env_var = single_url[2:-1]
            single_url = os.environ.get(env_var, '')
        if single_url:
            self.webhook_urls.append(single_url)

        # Check for multiple webhooks from environment
        # SLACK_WEBHOOK_URL_1, SLACK_WEBHOOK_URL_2, etc.
        for i in range(1, 10):
            env_url = os.environ.get(f'SLACK_WEBHOOK_URL_{i}', '')
            if env_url and env_url not in self.webhook_urls:
                self.webhook_urls.append(env_url)

        # Also check SLACK_WEBHOOK_URLS (comma-separated)
        multi_urls = os.environ.get('SLACK_WEBHOOK_URLS', '')
        if multi_urls:
            for url in multi_urls.split(','):
                url = url.strip()
                if url and url not in self.webhook_urls:
                    self.webhook_urls.append(url)

        self.enabled = slack_config.get('enabled', True) and len(self.webhook_urls) > 0
        self.mention_on_critical = slack_config.get('mention_on_critical', '')
        self.include_hostname = slack_config.get('include_hostname', True)

        if self.webhook_urls:
            logger.info(f"Slack configured with {len(self.webhook_urls)} webhook(s)")

    def send_summary(self, auto_fixed: List[Tuple], alerts: List,
                     all_ok: bool = False) -> bool:
        """Send a security scan summary to Slack.

        Args:
            auto_fixed: List of (CheckResult, RemediationResult) tuples
            alerts: List of CheckResult objects that need attention
            all_ok: Whether all checks passed

        Returns:
            True if sent to at least one webhook successfully
        """
        if not self.enabled:
            print("Slack notifications disabled (no webhook URL)")
            logger.warning("Slack notifications disabled (no webhook URL)")
            return False

        try:
            blocks = self._build_message_blocks(auto_fixed, alerts, all_ok)
            return self._send_to_all_webhooks(blocks)
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    def send_test_message(self) -> bool:
        """Send a test message to verify Slack integration.

        Returns:
            True if sent to at least one webhook successfully
        """
        if not self.enabled:
            print("Slack notifications disabled (no webhook URL)")
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
                            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"Webhooks configured: {len(self.webhook_urls)}\n\n"
                            f"If you see this message, Slack notifications are working correctly."
                }
            }
        ]

        return self._send_to_all_webhooks(blocks)

    def _send_to_all_webhooks(self, blocks: List[dict]) -> bool:
        """Send blocks to all configured Slack webhooks.

        Args:
            blocks: List of Slack block objects

        Returns:
            True if sent to at least one webhook successfully
        """
        success_count = 0
        for i, webhook_url in enumerate(self.webhook_urls, 1):
            try:
                response = requests.post(
                    webhook_url,
                    json={"blocks": blocks},
                    timeout=10
                )

                if response.status_code == 200:
                    logger.info(f"Slack notification sent to webhook {i}/{len(self.webhook_urls)}")
                    success_count += 1
                else:
                    logger.error(f"Slack API error (webhook {i}): {response.status_code} - {response.text}")

            except requests.exceptions.Timeout:
                logger.error(f"Slack webhook {i} request timed out")
            except requests.exceptions.RequestException as e:
                logger.error(f"Slack webhook {i} request failed: {e}")

        if success_count > 0:
            logger.info(f"Slack notification sent to {success_count}/{len(self.webhook_urls)} webhooks")
            return True
        return False

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

        # Import Severity for categorizing alerts
        from checks.base import Severity
        critical_alerts = [a for a in alerts if a.severity == Severity.CRITICAL]
        warning_alerts = [a for a in alerts if a.severity == Severity.WARNING]
        info_alerts = [a for a in alerts if a.severity == Severity.INFO]

        # Show green checkmark if no critical or warning issues
        if not critical_alerts and not warning_alerts and not auto_fixed:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":white_check_mark: *All checks passed!* Your VPS security is great."
                }
            })
            # Still show info items if any
            if info_alerts:
                info_text = f"*Info: {len(info_alerts)}*\n"
                info_text += "\n".join([f"- {a.message}" for a in info_alerts])
                blocks.append({
                    "type": "context",
                    "elements": [{
                        "type": "mrkdwn",
                        "text": info_text
                    }]
                })
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                    "text": "VPS Security Monitor | Next scan in 6 hours"
                }]
            })
            return blocks

        # Critical alerts (with mention)
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
                "text": "VPS Security Monitor | Next scan in 6 hours"
            }]
        })

        return blocks

    def _get_hostname(self) -> str:
        """Get the hostname of this machine."""
        try:
            return socket.gethostname()
        except Exception:
            return "unknown"
