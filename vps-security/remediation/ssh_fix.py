"""SSH security auto-remediation module."""

import os
import re
from datetime import datetime
from .base import BaseRemediation, RemediationResult


class SSHRemediation(BaseRemediation):
    """Auto-fix SSH security configuration issues."""

    name = "SSH Security Fix"

    SECURE_SETTINGS = {
        'PermitRootLogin': 'prohibit-password',
        'PasswordAuthentication': 'no',
        'PubkeyAuthentication': 'yes',
        'PermitEmptyPasswords': 'no',
    }

    def execute(self, check_result) -> RemediationResult:
        """Fix SSH security configuration."""
        ssh_config = self.config.get('ssh', {})
        config_path = ssh_config.get('config_path', '/etc/ssh/sshd_config')

        if not os.path.exists(config_path):
            return self._failure("Fix SSH config", f"SSH config not found: {config_path}")

        try:
            with open(config_path, 'r') as f:
                original_content = f.read()

            backup_id = self.rollback_manager.backup_file(config_path)
            self.logger.info(f"Backed up SSH config to {backup_id}")

            fixed_settings = []
            new_content = original_content

            for setting, secure_value in self.SECURE_SETTINGS.items():
                new_content, was_fixed = self._fix_setting(new_content, setting, secure_value)
                if was_fixed:
                    fixed_settings.append(f"{setting} = {secure_value}")

            if not fixed_settings:
                return self._success("SSH config check", ["SSH configuration already secure"], backup_id)

            with open(config_path, 'w') as f:
                f.write(new_content)

            self.logger.info(f"Updated SSH config with {len(fixed_settings)} changes")

            # Validate config before restart
            returncode, stdout, stderr = self._execute_command("sshd -t")
            if returncode != 0:
                self.logger.error(f"SSH config validation failed: {stderr}")
                with open(config_path, 'w') as f:
                    f.write(original_content)
                return self._failure("Fix SSH config", f"Config validation failed, rolled back: {stderr}", fixed_settings)

            # Restart SSH service
            success, msg = self._restart_ssh()
            if not success:
                self.logger.error(f"SSH restart failed: {msg}")
                with open(config_path, 'w') as f:
                    f.write(original_content)
                self._restart_ssh()
                return self._failure("Fix SSH config", f"SSH restart failed, rolled back: {msg}", fixed_settings)

            return self._success(
                f"Fixed SSH security ({len(fixed_settings)} settings)",
                [*fixed_settings, "", "SSH service restarted successfully"],
                backup_id
            )

        except PermissionError:
            return self._failure("Fix SSH config", "Permission denied - must run as root")
        except Exception as e:
            self.logger.error(f"SSH remediation failed: {e}")
            return self._failure("Fix SSH config", f"Unexpected error: {e}")

    def _fix_setting(self, content: str, setting: str, value: str) -> tuple:
        """Fix a single SSH setting in config content."""
        pattern = rf'^#?\s*{setting}\s+\S+.*$'
        replacement = f'{setting} {value}'

        if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
            correct_pattern = rf'^{setting}\s+{value}\s*$'
            if re.search(correct_pattern, content, re.MULTILINE | re.IGNORECASE):
                return content, False
            new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.IGNORECASE)
            return new_content, True
        else:
            if not content.endswith('\n'):
                content += '\n'
            content += f'\n# Added by VPS Security Monitor ({datetime.now().strftime("%Y-%m-%d %H:%M")})\n'
            content += f'{replacement}\n'
            return content, True

    def _restart_ssh(self) -> tuple:
        """Restart SSH service."""
        returncode, stdout, stderr = self._execute_command("systemctl restart sshd || systemctl restart ssh")
        if returncode == 0:
            return True, "SSH restarted via systemctl"
        returncode, stdout, stderr = self._execute_command("service sshd restart || service ssh restart")
        if returncode == 0:
            return True, "SSH restarted via service"
        return False, stderr or "Failed to restart SSH"
