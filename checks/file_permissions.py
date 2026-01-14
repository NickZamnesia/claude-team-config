"""Check file permissions for security issues."""

import os
import stat
from typing import List
from .base import BaseCheck, CheckResult, Severity


class FilePermissionsCheck(BaseCheck):
    """Audit file permissions for security issues."""

    name = "File Permissions"
    description = "Checks .env files and sensitive directories for proper permissions"

    def run(self) -> CheckResult:
        """Check file permissions."""
        perm_config = self.config.get('file_permissions', {})
        projects = self.config.get('projects', [])

        issues = []
        fixable_files = []

        # Check .env files in each project
        for project in projects:
            project_path = project.get('path', '')
            if not os.path.exists(project_path):
                continue

            env_path = os.path.join(project_path, '.env')
            if os.path.exists(env_path):
                issue = self._check_env_file(env_path, perm_config)
                if issue:
                    issues.append(issue)
                    fixable_files.append(env_path)

        # Check additional sensitive files
        sensitive_files = perm_config.get('sensitive_files', [])
        for filepath in sensitive_files:
            if os.path.exists(filepath):
                issue = self._check_env_file(filepath, perm_config)
                if issue:
                    issues.append(issue)
                    fixable_files.append(filepath)

        # Check for world-writable files in /opt
        world_writable = self._find_world_writable('/opt')
        if world_writable:
            issues.append(f"Found {len(world_writable)} world-writable files in /opt:")
            issues.extend([f"  {f}" for f in world_writable[:10]])
            if len(world_writable) > 10:
                issues.append(f"  ... and {len(world_writable) - 10} more")

        if issues:
            return self._warning_result(
                message=f"File permission issues found: {len(issues)}",
                details=issues,
                auto_fixable=len(fixable_files) > 0,
                fix_action="fix_env_permissions" if fixable_files else None,
                raw_data={'files': fixable_files}
            )

        return self._ok_result(
            message="All file permissions are correct",
            details=[
                "All .env files have mode 600",
                "No world-writable files in /opt"
            ]
        )

    def _check_env_file(self, filepath: str, perm_config: dict) -> str:
        """Check a single .env file's permissions.

        Args:
            filepath: Path to the file
            perm_config: Permission configuration

        Returns:
            Issue string if there's a problem, None otherwise
        """
        try:
            mode = stat.S_IMODE(os.stat(filepath).st_mode)
            mode_str = oct(mode)[-3:]

            max_mode = perm_config.get('env_files', {}).get('max_mode', '600')

            # Check if file is more permissive than allowed
            if self._is_more_permissive(mode_str, max_mode):
                return f"{filepath} has mode {mode_str} (should be {max_mode} or more restrictive)"

        except PermissionError:
            return f"{filepath} - cannot check permissions (access denied)"
        except Exception as e:
            return f"{filepath} - error checking permissions: {e}"

        return None

    def _is_more_permissive(self, actual: str, max_allowed: str) -> bool:
        """Check if actual permissions are more permissive than allowed.

        Args:
            actual: Actual mode (e.g., '644')
            max_allowed: Maximum allowed mode (e.g., '600')

        Returns:
            True if actual is more permissive
        """
        try:
            # Convert to integers for comparison
            actual_int = int(actual, 8)
            max_int = int(max_allowed, 8)

            # Check each permission bit
            # If actual has a bit set that max doesn't, it's more permissive
            for shift in range(9):  # 9 permission bits
                actual_bit = (actual_int >> shift) & 1
                max_bit = (max_int >> shift) & 1
                if actual_bit and not max_bit:
                    return True

            return False
        except ValueError:
            return False

    def _find_world_writable(self, directory: str, limit: int = 50) -> List[str]:
        """Find world-writable files in a directory.

        Args:
            directory: Directory to search
            limit: Maximum number of files to return

        Returns:
            List of world-writable file paths
        """
        world_writable = []

        try:
            # Use find command for efficiency
            returncode, stdout, stderr = self._execute_command(
                f"find {directory} -type f -perm -0002 2>/dev/null | head -{limit}"
            )

            if returncode == 0 and stdout:
                world_writable = [f for f in stdout.strip().split('\n') if f]

        except Exception as e:
            self.logger.warning(f"Error finding world-writable files: {e}")

        return world_writable
