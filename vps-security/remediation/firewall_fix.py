"""Firewall (UFW) remediation actions."""

from typing import List
from .base import BaseRemediation, RemediationResult


class FirewallRemediation(BaseRemediation):
    """Auto-fix UFW firewall issues."""

    name = "Firewall Remediation"

    def execute(self, check_result) -> RemediationResult:
        """Execute firewall remediation based on fix_action.

        Args:
            check_result: CheckResult with fix_action specified

        Returns:
            RemediationResult
        """
        fix_action = check_result.fix_action

        if fix_action == "enable_ufw":
            return self._enable_ufw()
        elif fix_action == "add_missing_rules":
            return self._add_missing_rules(check_result.raw_data.get('missing_ports', []))
        else:
            return self._failure(
                action=f"Unknown fix action: {fix_action}",
                error="Unrecognized remediation action"
            )

    def _enable_ufw(self) -> RemediationResult:
        """Enable UFW firewall safely.

        CRITICAL: Always ensures SSH (port 22) is allowed BEFORE enabling UFW
        to prevent lockout.
        """
        actions_taken = []

        # First, backup current rules
        returncode, rules_before, _ = self._execute_command("ufw status numbered")
        self.rollback_manager.record_ufw_change("enable_ufw", rules_before)

        # CRITICAL: Ensure SSH is allowed first
        self.logger.info("Ensuring SSH port 22 is allowed before enabling UFW")
        returncode, stdout, stderr = self._execute_command("ufw allow 22/tcp")
        if returncode != 0:
            return self._failure(
                action="Enable UFW",
                error=f"Failed to allow SSH port 22: {stderr}",
                details=["ABORTED: Cannot enable UFW without SSH access guaranteed"]
            )
        actions_taken.append("Allowed SSH port 22/tcp")

        # Add all configured allowed ports
        allowed_ports = self.config.get('firewall', {}).get('allowed_ports', [])
        for port in allowed_ports:
            if port == 22:
                continue  # Already added
            returncode, stdout, stderr = self._execute_command(f"ufw allow {port}/tcp")
            if returncode == 0:
                actions_taken.append(f"Allowed port {port}/tcp")
            else:
                self.logger.warning(f"Failed to allow port {port}: {stderr}")

        # Enable UFW (non-interactive)
        self.logger.info("Enabling UFW firewall")
        returncode, stdout, stderr = self._execute_command("ufw --force enable")

        if returncode != 0:
            return self._failure(
                action="Enable UFW",
                error=f"Failed to enable UFW: {stderr}",
                details=actions_taken
            )

        actions_taken.append("Enabled UFW firewall")

        # Verify UFW is now active
        returncode, stdout, stderr = self._execute_command("ufw status")
        if "Status: active" not in stdout:
            return self._failure(
                action="Enable UFW",
                error="UFW reports inactive after enable command",
                details=actions_taken
            )

        actions_taken.append("Verified UFW is active")

        self.rollback_manager.record_command(
            "ufw --force enable",
            "Enabled UFW firewall"
        )

        return self._success(
            action="Enabled UFW firewall",
            details=actions_taken,
            rollback_id=self.rollback_manager.get_session_id()
        )

    def _add_missing_rules(self, missing_ports: List[int]) -> RemediationResult:
        """Add missing port rules to UFW.

        Args:
            missing_ports: List of port numbers to allow
        """
        if not missing_ports:
            return self._success(
                action="Add missing rules",
                details=["No missing rules to add"]
            )

        # Backup current rules
        returncode, rules_before, _ = self._execute_command("ufw status numbered")
        self.rollback_manager.record_ufw_change("add_missing_rules", rules_before)

        actions_taken = []
        errors = []

        for port in missing_ports:
            returncode, stdout, stderr = self._execute_command(f"ufw allow {port}/tcp")
            if returncode == 0:
                actions_taken.append(f"Allowed port {port}/tcp")
                self.rollback_manager.record_command(
                    f"ufw allow {port}/tcp",
                    f"Added firewall rule for port {port}"
                )
            else:
                errors.append(f"Failed to allow port {port}: {stderr}")

        if errors:
            return self._failure(
                action="Add missing rules",
                error="; ".join(errors),
                details=actions_taken
            )

        return self._success(
            action=f"Added {len(actions_taken)} firewall rules",
            details=actions_taken,
            rollback_id=self.rollback_manager.get_session_id()
        )
