"""File permission remediation actions."""

import os
import stat
from typing import List
from .base import BaseRemediation, RemediationResult


class PermissionRemediation(BaseRemediation):
    """Auto-fix file permission issues."""

    name = "Permission Remediation"

    def execute(self, check_result) -> RemediationResult:
        """Execute permission remediation.

        Args:
            check_result: CheckResult with fix_action and raw_data

        Returns:
            RemediationResult
        """
        fix_action = check_result.fix_action

        if fix_action == "fix_env_permissions":
            return self._fix_env_permissions(check_result.raw_data.get('files', []))
        else:
            return self._failure(
                action=f"Unknown fix action: {fix_action}",
                error="Unrecognized remediation action"
            )

    def _fix_env_permissions(self, files: List[str]) -> RemediationResult:
        """Fix .env file permissions to 600.

        Args:
            files: List of file paths to fix
        """
        if not files:
            return self._success(
                action="Fix .env permissions",
                details=["No files to fix"]
            )

        actions_taken = []
        errors = []

        for filepath in files:
            try:
                if not os.path.exists(filepath):
                    errors.append(f"File not found: {filepath}")
                    continue

                # Get current permissions
                current_mode = stat.S_IMODE(os.stat(filepath).st_mode)
                current_mode_str = oct(current_mode)[-3:]

                # Record for rollback
                self.rollback_manager.record_permission_change(
                    filepath,
                    original_mode=current_mode_str,
                    new_mode='600'
                )

                # Set to 600 (owner read/write only)
                os.chmod(filepath, 0o600)

                actions_taken.append(f"{filepath}: {current_mode_str} -> 600")
                self.logger.info(f"Fixed permissions on {filepath}: {current_mode_str} -> 600")

            except PermissionError as e:
                errors.append(f"Permission denied: {filepath}")
            except Exception as e:
                errors.append(f"Error fixing {filepath}: {e}")

        if errors and not actions_taken:
            return self._failure(
                action="Fix .env permissions",
                error="; ".join(errors),
                details=[]
            )

        if errors:
            # Partial success
            return RemediationResult(
                success=True,
                action=f"Fixed {len(actions_taken)} file(s), {len(errors)} error(s)",
                details=actions_taken + [f"ERRORS: {e}" for e in errors],
                rollback_id=self.rollback_manager.get_session_id()
            )

        return self._success(
            action=f"Fixed permissions on {len(actions_taken)} file(s)",
            details=actions_taken,
            rollback_id=self.rollback_manager.get_session_id()
        )
