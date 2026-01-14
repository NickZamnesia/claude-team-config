"""Base classes for security checks."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
import subprocess
import logging

logger = logging.getLogger(__name__)


class Severity(Enum):
    """Severity levels for security issues."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    OK = "ok"


@dataclass
class CheckResult:
    """Result of a security check."""
    check_name: str
    severity: Severity
    message: str
    details: List[str] = field(default_factory=list)
    auto_fixable: bool = False
    fix_action: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'check_name': self.check_name,
            'severity': self.severity.value,
            'message': self.message,
            'details': self.details,
            'auto_fixable': self.auto_fixable,
            'fix_action': self.fix_action,
            'raw_data': self.raw_data,
        }


class BaseCheck:
    """Base class for all security checks."""

    name: str = "Base Check"
    description: str = "Base security check"

    def __init__(self, config: dict):
        """Initialize check with configuration.

        Args:
            config: Configuration dictionary from config.yaml
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def run(self) -> CheckResult:
        """Execute the security check.

        Returns:
            CheckResult with findings
        """
        raise NotImplementedError("Subclasses must implement run()")

    def _execute_command(self, cmd: str, timeout: int = 30) -> tuple:
        """Execute a shell command and return results.

        Args:
            cmd: Command to execute
            timeout: Timeout in seconds

        Returns:
            Tuple of (returncode, stdout, stderr)
        """
        try:
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

    def _ok_result(self, message: str, details: List[str] = None) -> CheckResult:
        """Create an OK result."""
        return CheckResult(
            check_name=self.name,
            severity=Severity.OK,
            message=message,
            details=details or [],
            auto_fixable=False
        )

    def _warning_result(self, message: str, details: List[str] = None,
                        auto_fixable: bool = False, fix_action: str = None,
                        raw_data: dict = None) -> CheckResult:
        """Create a warning result."""
        return CheckResult(
            check_name=self.name,
            severity=Severity.WARNING,
            message=message,
            details=details or [],
            auto_fixable=auto_fixable,
            fix_action=fix_action,
            raw_data=raw_data
        )

    def _critical_result(self, message: str, details: List[str] = None,
                         auto_fixable: bool = False, fix_action: str = None,
                         raw_data: dict = None) -> CheckResult:
        """Create a critical result."""
        return CheckResult(
            check_name=self.name,
            severity=Severity.CRITICAL,
            message=message,
            details=details or [],
            auto_fixable=auto_fixable,
            fix_action=fix_action,
            raw_data=raw_data
        )

    def _info_result(self, message: str, details: List[str] = None) -> CheckResult:
        """Create an info result."""
        return CheckResult(
            check_name=self.name,
            severity=Severity.INFO,
            message=message,
            details=details or [],
            auto_fixable=False
        )
