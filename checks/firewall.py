"""Check UFW firewall status and rules."""

import re
from typing import Set, List, Tuple
from .base import BaseCheck, CheckResult, Severity


class FirewallCheck(BaseCheck):
    """Verify UFW firewall is active with correct rules."""

    name = "UFW Firewall"
    description = "Checks if UFW is active and only allows necessary ports"

    def run(self) -> CheckResult:
        """Check UFW status and rules."""
        # Check if UFW is installed
        returncode, stdout, stderr = self._execute_command("which ufw")
        if returncode != 0:
            return self._critical_result(
                message="CRITICAL: UFW firewall is not installed!",
                details=[
                    "Server has no firewall protection",
                    "Install with: apt install ufw"
                ],
                auto_fixable=False,
                fix_action="install_ufw"
            )

        # Check UFW status
        returncode, stdout, stderr = self._execute_command("ufw status verbose")

        if "Status: inactive" in stdout:
            return self._critical_result(
                message="CRITICAL: UFW firewall is DISABLED!",
                details=[
                    "Server has no active firewall protection",
                    "All ports are potentially exposed to the internet",
                    "",
                    "This will be auto-fixed by enabling UFW with configured rules"
                ],
                auto_fixable=True,
                fix_action="enable_ufw",
                raw_data={'ufw_status': stdout}
            )

        # Parse current rules
        allowed_ports = self._parse_ufw_rules(stdout)
        expected_ports = set(self.config.get('firewall', {}).get('allowed_ports', []))
        dangerous_ports = set(self.config.get('firewall', {}).get('dangerous_ports', []))

        # Check for dangerous ports being allowed
        exposed_dangerous = allowed_ports & dangerous_ports
        if exposed_dangerous:
            return self._critical_result(
                message=f"CRITICAL: Dangerous ports allowed through firewall!",
                details=[
                    f"These database ports are allowed: {sorted(exposed_dangerous)}",
                    "",
                    "These ports should NEVER be allowed through the firewall.",
                    "Remove with: ufw delete allow <port>"
                ],
                auto_fixable=False,  # Don't auto-delete rules
                fix_action="remove_dangerous_rules",
                raw_data={
                    'exposed_dangerous': list(exposed_dangerous),
                    'ufw_status': stdout
                }
            )

        # Check for unexpected allowed ports
        unexpected = allowed_ports - expected_ports - {22}  # Always allow SSH
        if unexpected:
            return self._warning_result(
                message=f"Unexpected ports allowed through firewall",
                details=[
                    f"Ports not in config but allowed: {sorted(unexpected)}",
                    "",
                    "Review these rules and remove if not needed:",
                    *[f"  ufw delete allow {p}" for p in sorted(unexpected)]
                ],
                auto_fixable=False,
                raw_data={
                    'unexpected_ports': list(unexpected),
                    'ufw_status': stdout
                }
            )

        # Check for missing expected ports
        missing = expected_ports - allowed_ports
        if missing:
            return self._warning_result(
                message=f"Some expected ports not in firewall rules",
                details=[
                    f"Missing port rules: {sorted(missing)}",
                    "",
                    "These ports should be allowed but aren't:",
                    *[f"  ufw allow {p}/tcp" for p in sorted(missing)]
                ],
                auto_fixable=True,
                fix_action="add_missing_rules",
                raw_data={
                    'missing_ports': list(missing),
                    'ufw_status': stdout
                }
            )

        # All good
        return self._ok_result(
            message="UFW firewall active with correct rules",
            details=[
                f"Status: Active",
                f"Allowed ports: {sorted(allowed_ports)}",
                f"No dangerous database ports exposed"
            ]
        )

    def _parse_ufw_rules(self, ufw_output: str) -> Set[int]:
        """Parse UFW status output to extract allowed ports.

        Args:
            ufw_output: Output from 'ufw status verbose'

        Returns:
            Set of allowed port numbers
        """
        allowed_ports = set()

        for line in ufw_output.split('\n'):
            # Skip non-rule lines
            if 'ALLOW' not in line:
                continue

            # Parse lines like:
            # 22/tcp                     ALLOW IN    Anywhere
            # 80                         ALLOW IN    Anywhere
            # 443/tcp (v6)               ALLOW IN    Anywhere (v6)

            # Extract port number from the start of the line
            match = re.match(r'^(\d+)(?:/tcp|/udp)?', line.strip())
            if match:
                port = int(match.group(1))
                allowed_ports.add(port)

        return allowed_ports

    def get_current_rules(self) -> str:
        """Get current UFW rules for backup purposes."""
        returncode, stdout, stderr = self._execute_command("ufw status numbered")
        return stdout
