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

        fail2ban_status = self._check_fail2ban() if check_fail2ban else None
        failed_count, top_attackers = self._count_failed_logins(auth_log)

        details = []
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
            return self._warning_result(
                message=f"High failed login rate: {failed_count} in last hour",
                details=details
            )

        details.insert(0, f"Failed login attempts in last hour: {failed_count}")
        details.insert(1, f"Below threshold of {threshold}")
        return self._ok_result(
            message=f"Normal login attempt rate: {failed_count}/hour",
            details=details
        )

    def _count_failed_logins(self, auth_log: str) -> Tuple[int, List[Tuple[str, int]]]:
        """Count failed SSH logins in the last hour."""
        one_hour_ago = datetime.now() - timedelta(hours=1)

        # Use journalctl with time filtering (most reliable)
        returncode, stdout, stderr = self._execute_command(
            "journalctl -u ssh -u sshd --since '1 hour ago' --no-pager 2>/dev/null | grep -i 'failed password'"
        )

        if returncode != 0 or not stdout.strip():
            stdout = self._filter_auth_log_by_time(auth_log, one_hour_ago)

        if not stdout:
            return 0, []

        ip_pattern = re.compile(r'from\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
        ips = []
        for line in stdout.strip().split('\n'):
            if not line:
                continue
            match = ip_pattern.search(line)
            if match:
                ips.append(match.group(1))

        ip_counts = Counter(ips)
        return len(ips), ip_counts.most_common(10)

    def _filter_auth_log_by_time(self, auth_log: str, cutoff: datetime) -> str:
        """Filter auth.log to only include entries after cutoff time."""
        returncode, stdout, stderr = self._execute_command(
            f"tail -2000 {auth_log} 2>/dev/null | grep 'Failed password'"
        )
        if returncode != 0 or not stdout:
            return ""

        filtered = []
        iso_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})')

        for line in stdout.strip().split('\n'):
            if not line:
                continue
            iso_match = iso_pattern.match(line)
            if iso_match:
                try:
                    ts = datetime.fromisoformat(iso_match.group(1))
                    if ts >= cutoff:
                        filtered.append(line)
                except ValueError:
                    pass
        return '\n'.join(filtered)

    def _check_fail2ban(self) -> bool:
        """Check if fail2ban is running."""
        returncode, stdout, stderr = self._execute_command("which fail2ban-client")
        if returncode != 0:
            return False
        returncode, stdout, stderr = self._execute_command("fail2ban-client status 2>/dev/null")
        return returncode == 0 and 'Number of jail' in stdout
