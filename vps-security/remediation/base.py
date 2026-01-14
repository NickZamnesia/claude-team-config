"""Base classes for auto-remediation."""

from dataclasses import dataclass
from typing import Optional, List
import subprocess
import logging

logger = logging.getLogger(__name__)


@dataclass
class RemediationResult:
    """Result of a remediation action."""
    success: bool
    action: str
    details: List[str]
    rollback_id: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'action': self.action,
            'details': self.details,
            'rollback_id': self.rollback_id,
            'error': self.error,
        }


class BaseRemediation:
    """Base class for all remediation actions."""

    name: str = "Base Remediation"

    def __init__(self, config: dict, rollback_manager):
        """Initialize remediation with config and rollback manager.

        Args:
            config: Configuration dictionary
            rollback_manager: RollbackManager instance for backup/rollback
        """
        self.config = config
        self.rollback_manager = rollback_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def execute(self, check_result) -> RemediationResult:
        """Execute the remediation action.

        Args:
            check_result: CheckResult that triggered this remediation

        Returns:
            RemediationResult with status
        """
        raise NotImplementedError("Subclasses must implement execute()")

    def can_rollback(self) -> bool:
        """Check if this remediation can be rolled back."""
        return True

    def _execute_command(self, cmd: str, timeout: int = 30) -> tuple:
        """Execute a shell command.

        Args:
            cmd: Command to execute
            timeout: Timeout in seconds

        Returns:
            Tuple of (returncode, stdout, stderr)
        """
        try:
            self.logger.info(f"Executing: {cmd}")
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {cmd}")
            return -1, "", "Command timed out"
        except Exception as e:
            self.logger.error(f"Command failed: {cmd}, error: {e}")
            return -1, "", str(e)

    def _success(self, action: str, details: List[str],
                 rollback_id: str = None) -> RemediationResult:
        """Create a success result."""
        return RemediationResult(
            success=True,
            action=action,
            details=details,
            rollback_id=rollback_id
        )

    def _failure(self, action: str, error: str,
                 details: List[str] = None) -> RemediationResult:
        """Create a failure result."""
        return RemediationResult(
            success=False,
            action=action,
            details=details or [],
            error=error
        )
