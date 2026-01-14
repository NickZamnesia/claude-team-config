"""Check for suspicious processes and network activity."""

import re
from typing import List, Tuple
from .base import BaseCheck, CheckResult, Severity


class SuspiciousActivityCheck(BaseCheck):
    """Detect potentially malicious processes and connections."""

    name = "Suspicious Activity"
    description = "Checks for crypto miners, unusual processes, and suspicious connections"

    def run(self) -> CheckResult:
        """Check for suspicious activity."""
        config = self.config.get('suspicious_activity', {})
        issues = []

        # Check for suspicious processes
        if config.get('check_crypto_mining', True):
            crypto_issues = self._check_crypto_mining(config)
            issues.extend(crypto_issues)

        # Check for high CPU processes
        cpu_threshold = config.get('cpu_threshold', 90)
        cpu_issues = self._check_high_cpu(cpu_threshold)
        issues.extend(cpu_issues)

        # Check for suspicious outbound connections
        suspicious_ports = config.get('suspicious_ports', [])
        if suspicious_ports:
            conn_issues = self._check_suspicious_connections(suspicious_ports)
            issues.extend(conn_issues)

        if issues:
            severity = Severity.CRITICAL if any('crypto' in i.lower() or 'miner' in i.lower() for i in issues) else Severity.WARNING

            return CheckResult(
                check_name=self.name,
                severity=severity,
                message=f"Suspicious activity detected: {len(issues)} issue(s)",
                details=issues,
                auto_fixable=False,  # Never auto-kill processes
                fix_action="investigate_processes"
            )

        return self._ok_result(
            message="No suspicious activity detected",
            details=[
                "No known crypto mining processes found",
                "No processes with suspicious names",
                "No unusual high-CPU processes"
            ]
        )

    def _check_crypto_mining(self, config: dict) -> List[str]:
        """Check for known crypto mining processes.

        Args:
            config: Suspicious activity config

        Returns:
            List of issues found
        """
        issues = []
        suspicious_names = config.get('suspicious_process_names', [
            'xmrig', 'minerd', 'cpuminer', 'cryptonight', 'stratum',
            'xmr-stak', 'ccminer', 'ethminer', 'nbminer', 'phoenixminer'
        ])

        # Get running processes
        returncode, stdout, stderr = self._execute_command(
            "ps aux --no-headers 2>/dev/null"
        )

        if returncode != 0:
            return issues

        for line in stdout.strip().split('\n'):
            if not line:
                continue

            line_lower = line.lower()
            for name in suspicious_names:
                if name.lower() in line_lower:
                    # Extract process info
                    parts = line.split()
                    if len(parts) >= 11:
                        user = parts[0]
                        pid = parts[1]
                        cpu = parts[2]
                        command = ' '.join(parts[10:])
                        issues.append(
                            f"SUSPICIOUS PROCESS: {name} (PID {pid}, User {user}, CPU {cpu}%)"
                        )
                        issues.append(f"  Command: {command[:80]}")

        return issues

    def _check_high_cpu(self, threshold: int) -> List[str]:
        """Check for processes using high CPU.

        Args:
            threshold: CPU percentage threshold

        Returns:
            List of issues found
        """
        issues = []

        # Get top CPU processes
        returncode, stdout, stderr = self._execute_command(
            f"ps aux --sort=-%cpu --no-headers 2>/dev/null | head -5"
        )

        if returncode != 0:
            return issues

        for line in stdout.strip().split('\n'):
            if not line:
                continue

            parts = line.split()
            if len(parts) < 11:
                continue

            try:
                cpu = float(parts[2])
                if cpu >= threshold:
                    user = parts[0]
                    pid = parts[1]
                    command = ' '.join(parts[10:])

                    # Skip known legitimate high-CPU processes
                    if any(legit in command.lower() for legit in ['docker', 'mysql', 'postgres', 'nginx', 'apache', 'node', 'python']):
                        continue

                    issues.append(
                        f"HIGH CPU PROCESS: PID {pid} using {cpu}% CPU (User: {user})"
                    )
                    issues.append(f"  Command: {command[:80]}")
            except (ValueError, IndexError):
                continue

        return issues

    def _check_suspicious_connections(self, suspicious_ports: List[int]) -> List[str]:
        """Check for outbound connections to suspicious ports.

        Args:
            suspicious_ports: List of suspicious port numbers

        Returns:
            List of issues found
        """
        issues = []

        # Get established connections
        returncode, stdout, stderr = self._execute_command(
            "ss -tunp state established 2>/dev/null || netstat -tunp 2>/dev/null | grep ESTABLISHED"
        )

        if returncode != 0:
            return issues

        for line in stdout.strip().split('\n'):
            if not line or 'ESTAB' not in line.upper():
                continue

            for port in suspicious_ports:
                if f':{port}' in line:
                    issues.append(f"SUSPICIOUS CONNECTION to port {port}: {line.strip()}")
                    break

        return issues
