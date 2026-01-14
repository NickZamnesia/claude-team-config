"""Check for failed login attempts (brute force detection)."""

import re
from datetime import datetime, timedelta
from typing import List, Tuple
from collections import Counter
from .base import BaseCheck, CheckResult, Severity


class FailedLoginsCheck(BaseCheck):
    """Monitor failed SSH login attempts."""

    name = "Failed Login Attempts"
    description = "Monitors auth.log for brute force attempts"

    def run(self) -> CheckResult:
        """Check for failed login attempts in the last hour."""
        login_config = self.config.get('failed_logins', {})
        threshold = login_config.get('threshold_per_hour', 10)
        auth_log = login_config.get('auth_log', '/var/log/auth.log')
        check_fail2ban = login_config.get('check_fail2ban', True)

        # Check if fail2ban is running
        fail2ban_status = self._check_fail2ban() if check_fail2ban else None

        # Count failed logins
        failed_count, top_attackers = self._count_failed_logins(auth_log)

        details = []

        # Add fail2ban status
        if fail2ban_status is not None:
            if fail2ban_status:
                details.append("fail2ban is active and protecting SSH")
            else:
                details.append("fail2ban is NOT running - consider installing it")

        if failed_count > threshold:
            details.extend([
                f"Failed login attempts in last hour: {failed_count}",
                f"Threshold: {threshold}",
                "",
                "Top attacking IPs:",
                *[f"  {count:4d} attempts from {ip}" for ip, count in top_attackers[:5]]
            ])

            if not fail2ban_status:
                details.extend([
                    "",
                    "RECOMMENDATION: Install fail2ban to auto-block attackers",
                    "  apt install fail2ban && systemctl enable --now fail2ban"
                ])

            return self._warning_result(
                message=f"High failed login rate: {failed_count} in last hour",
                details=details,
                raw_data={
                    'failed_count': failed_count,
                    'threshold': threshold,
                    'top_attackers': top_attackers[:10]
                }
            )

        details.insert(0, f"Failed login attempts in last hour: {failed_count}")
        details.insert(1, f"Below threshold of {threshold}")

        return self._ok_result(
            message=f"Normal login attempt rate: {failed_count}/hour",
            details=details
        )

    def _count_failed_logins(self, auth_log: str) -> Tuple[int, List[Tuple[str, int]]]:
        """Count failed SSH logins in the last hour.

        Args:
            auth_log: Path to auth.log file

        Returns:
            Tuple of (total_count, [(ip, count), ...])
        """
        one_hour_ago = datetime.now() - timedelta(hours=1)

        # Use grep for efficiency on large log files
        returncode, stdout, stderr = self._execute_command(
            f"grep 'Failed password' {auth_log} 2>/dev/null | tail -1000"
        )

        if returncode != 0 or not stdout:
            # Try alternative: journalctl
            returncode, stdout, stderr = self._execute_command(
                "journalctl -u sshd --since '1 hour ago' 2>/dev/null | grep -i 'failed'"
            )

        if not stdout:
            return 0, []

        # Parse and count
        ip_pattern = re.compile(r'from\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
        ips = []

        for line in stdout.strip().split('\n'):
            if not line:
                continue

            # Try to parse timestamp to filter last hour
            # Common format: "Jan 13 14:30:00"
            try:
                # Extract IP even if we can't parse timestamp
                match = ip_pattern.search(line)
                if match:
                    ips.append(match.group(1))
            except Exception:
                continue

        # Count by IP
        ip_counts = Counter(ips)
        top_attackers = ip_counts.most_common(10)

        return len(ips), top_attackers

    def _check_fail2ban(self) -> bool:
        """Check if fail2ban is installed and running.

        Returns:
            True if running, False if not running, None if not installed
        """
        # Check if installed
        returncode, stdout, stderr = self._execute_command("which fail2ban-client")
        if returncode != 0:
            return False

        # Check if running
        returncode, stdout, stderr = self._execute_command(
            "fail2ban-client status 2>/dev/null"
        )

        return returncode == 0 and 'Number of jail' in stdout
