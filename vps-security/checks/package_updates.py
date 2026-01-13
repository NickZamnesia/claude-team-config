"""Check for available system package updates."""

from typing import List, Tuple
from .base import BaseCheck, CheckResult, Severity


class PackageUpdatesCheck(BaseCheck):
    """Check for available system security updates."""

    name = "Package Updates"
    description = "Checks for available system package updates"

    def run(self) -> CheckResult:
        """Check for available package updates."""
        # First, update package list (quick operation)
        self._execute_command("apt update -qq 2>/dev/null")

        # Get list of upgradable packages
        returncode, stdout, stderr = self._execute_command(
            "apt list --upgradable 2>/dev/null | grep -v 'Listing'"
        )

        if returncode != 0:
            return self._info_result(
                message="Could not check for package updates",
                details=["apt command failed or not available"]
            )

        if not stdout.strip():
            return self._ok_result(
                message="System packages are up to date",
                details=["No pending updates"]
            )

        # Parse package list
        packages = [line.strip() for line in stdout.strip().split('\n') if line.strip()]
        total_count = len(packages)

        # Identify security updates
        security_packages = []
        kernel_packages = []
        other_packages = []

        for pkg in packages:
            pkg_lower = pkg.lower()
            if 'security' in pkg_lower or 'CVE' in pkg:
                security_packages.append(pkg)
            elif 'linux-image' in pkg_lower or 'linux-headers' in pkg_lower:
                kernel_packages.append(pkg)
            else:
                other_packages.append(pkg)

        details = [
            f"Total packages to update: {total_count}",
        ]

        if security_packages:
            details.append(f"Security updates: {len(security_packages)}")
            details.extend([f"  - {pkg.split('/')[0]}" for pkg in security_packages[:5]])
            if len(security_packages) > 5:
                details.append(f"  ... and {len(security_packages) - 5} more security updates")

        if kernel_packages:
            details.append(f"Kernel updates: {len(kernel_packages)}")
            details.extend([f"  - {pkg.split('/')[0]}" for pkg in kernel_packages[:3]])

        details.extend([
            "",
            "To update all packages:",
            "  apt update && apt upgrade -y",
            "",
            "To update security packages only:",
            "  apt update && apt upgrade -y --only-upgrade"
        ])

        # Determine severity
        if security_packages:
            severity = Severity.WARNING
            message = f"{len(security_packages)} security update(s) available"
        elif kernel_packages:
            severity = Severity.INFO
            message = f"{total_count} update(s) available (including kernel)"
        else:
            severity = Severity.INFO
            message = f"{total_count} package update(s) available"

        return CheckResult(
            check_name=self.name,
            severity=severity,
            message=message,
            details=details,
            auto_fixable=False,  # Never auto-update packages
            fix_action="manual_update",
            raw_data={
                'total': total_count,
                'security': len(security_packages),
                'kernel': len(kernel_packages),
                'packages': packages[:20]  # First 20 for reference
            }
        )
