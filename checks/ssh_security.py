"""Check SSH security configuration."""

import os
import re
from typing import Dict, List, Tuple
from .base import BaseCheck, CheckResult, Severity


class SSHSecurityCheck(BaseCheck):
    """Verify SSH is configured securely."""

    name = "SSH Security"
    description = "Checks SSH configuration for security best practices"

    def run(self) -> CheckResult:
        """Check SSH configuration."""
        ssh_config = self.config.get('ssh', {})
        config_path = ssh_config.get('config_path', '/etc/ssh/sshd_config')
        requirements = ssh_config.get('requirements', {})

        if not os.path.exists(config_path):
            return self._warning_result(
                message=f"SSH config not found at {config_path}",
                details=["Cannot verify SSH security settings"]
            )

        try:
            with open(config_path, 'r') as f:
                content = f.read()
        except PermissionError:
            return self._warning_result(
                message="Cannot read SSH config (permission denied)",
                details=["Run as root to check SSH configuration"]
            )

        issues = []
        settings = self._parse_sshd_config(content)

        # Check each required setting
        for setting, required_value in requirements.items():
            actual_value = settings.get(setting.lower())

            if actual_value is None:
                # Setting not explicitly set - check defaults
                if setting.lower() == 'passwordauthentication':
                    # Default is 'yes' which is bad
                    issues.append(f"{setting} not set (defaults to 'yes' - insecure)")
                elif setting.lower() == 'permitrootlogin':
                    # Default varies by distro, but often 'yes'
                    issues.append(f"{setting} not explicitly set (may default to 'yes')")
            elif not self._value_matches(actual_value, required_value):
                issues.append(
                    f"{setting} is '{actual_value}' (should be '{required_value}')"
                )

        # Additional security checks
        additional_issues = self._check_additional_security(settings, content)
        issues.extend(additional_issues)

        if issues:
            severity = Severity.CRITICAL if any('PasswordAuthentication' in i or 'PermitRootLogin' in i for i in issues) else Severity.WARNING

            return CheckResult(
                check_name=self.name,
                severity=severity,
                message=f"SSH security issues found: {len(issues)}",
                details=issues,
                auto_fixable=True,
                fix_action="fix_ssh_config"
            )

        return self._ok_result(
            message="SSH configuration is secure",
            details=[
                "PasswordAuthentication: disabled",
                "PubkeyAuthentication: enabled",
                "PermitRootLogin: key-only or disabled"
            ]
        )

    def _parse_sshd_config(self, content: str) -> Dict[str, str]:
        """Parse sshd_config file content.

        Args:
            content: File content

        Returns:
            Dictionary of setting -> value (lowercase keys)
        """
        settings = {}

        for line in content.split('\n'):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Parse "Setting Value" format
            parts = line.split(None, 1)
            if len(parts) == 2:
                key, value = parts
                settings[key.lower()] = value.lower()

        return settings

    def _value_matches(self, actual: str, required: str) -> bool:
        """Check if actual value matches required value.

        Args:
            actual: Actual setting value
            required: Required setting value

        Returns:
            True if they match (or are equivalent)
        """
        actual = actual.lower()
        required = required.lower()

        if actual == required:
            return True

        # Handle equivalent values
        if required == 'no':
            return actual in ['no', 'false', '0']
        if required == 'yes':
            return actual in ['yes', 'true', '1']
        if required in ['prohibit-password', 'without-password']:
            return actual in ['prohibit-password', 'without-password']

        return False

    def _check_additional_security(self, settings: Dict[str, str],
                                   content: str) -> List[str]:
        """Check for additional SSH security issues.

        Args:
            settings: Parsed settings dictionary
            content: Raw config file content

        Returns:
            List of additional issues
        """
        issues = []

        # Check for empty passwords
        if settings.get('permitemptypasswords', 'no') == 'yes':
            issues.append("PermitEmptyPasswords is 'yes' (extremely insecure!)")

        # Check for protocol version (old configs might have this)
        protocol = settings.get('protocol')
        if protocol and '1' in protocol:
            issues.append("SSH Protocol 1 is enabled (deprecated and insecure)")

        # Check for weak ciphers (basic check)
        ciphers = settings.get('ciphers', '')
        weak_ciphers = ['3des', 'arcfour', 'blowfish']
        for weak in weak_ciphers:
            if weak in ciphers.lower():
                issues.append(f"Weak cipher enabled: {weak}")

        # Check MaxAuthTries
        max_auth = settings.get('maxauthtries')
        if max_auth:
            try:
                if int(max_auth) > 6:
                    issues.append(f"MaxAuthTries is {max_auth} (consider lowering to 3-6)")
            except ValueError:
                pass

        return issues
