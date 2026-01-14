"""Check for exposed database ports in Docker containers.

This is the most critical check - exposed database ports were the
exact vulnerability that caused the ransomware attack on 2026-01-12.
"""

import os
import re
from typing import List, Tuple
from .base import BaseCheck, CheckResult, Severity


class DockerPortsCheck(BaseCheck):
    """Detect if database ports are exposed to the internet."""

    name = "Database Port Exposure"
    description = "Checks if PostgreSQL, MySQL, or Redis ports are publicly accessible"

    # Database ports that should NEVER be exposed to 0.0.0.0
    DANGEROUS_PORTS = {
        '5432': 'PostgreSQL',
        '3306': 'MySQL',
        '3307': 'MySQL (alternate)',
        '6379': 'Redis',
        '6380': 'Redis (alternate)',
        '27017': 'MongoDB',
        '9200': 'Elasticsearch',
    }

    def run(self) -> CheckResult:
        """Check for exposed database ports."""
        exposed_containers = self._check_running_containers()
        exposed_compose = self._check_compose_files()

        all_exposed = exposed_containers + exposed_compose

        if all_exposed:
            return self._critical_result(
                message=f"CRITICAL: {len(all_exposed)} database port(s) exposed to internet!",
                details=[
                    "This is the SAME vulnerability that caused the ransomware attack!",
                    "",
                    *all_exposed,
                    "",
                    "FIX: Remove 'ports' section from database services in docker-compose.yml",
                    "Databases should only be accessible via internal Docker network.",
                ],
                auto_fixable=False,  # Requires manual docker-compose edit
                fix_action="remove_database_ports",
                raw_data={'exposed': all_exposed}
            )

        return self._ok_result(
            message="All database ports properly isolated",
            details=[
                "No PostgreSQL, MySQL, Redis, or MongoDB ports exposed to 0.0.0.0",
                "Databases are only accessible via internal Docker network"
            ]
        )

    def _check_running_containers(self) -> List[str]:
        """Check running Docker containers for exposed ports."""
        exposed = []

        # Get all running containers with their port mappings
        returncode, stdout, stderr = self._execute_command(
            "docker ps --format '{{.Names}}|{{.Ports}}' 2>/dev/null"
        )

        if returncode != 0:
            self.logger.warning(f"Could not check Docker containers: {stderr}")
            return exposed

        for line in stdout.strip().split('\n'):
            if not line or '|' not in line:
                continue

            parts = line.split('|')
            container_name = parts[0]
            ports_str = parts[1] if len(parts) > 1 else ''

            # Parse port mappings like "0.0.0.0:5432->5432/tcp"
            for port, db_name in self.DANGEROUS_PORTS.items():
                # Check if port is bound to 0.0.0.0 (public)
                if f'0.0.0.0:{port}' in ports_str or f'0.0.0.0:' in ports_str and f'->{port}/' in ports_str:
                    exposed.append(
                        f"[CONTAINER] {container_name}: {db_name} port {port} exposed to 0.0.0.0"
                    )
                # Also check for any binding to the dangerous port
                elif f':{port}->' in ports_str:
                    # Extract the host binding
                    match = re.search(rf'(\d+\.\d+\.\d+\.\d+):(\d+)->{port}', ports_str)
                    if match:
                        host_ip = match.group(1)
                        host_port = match.group(2)
                        if host_ip == '0.0.0.0':
                            exposed.append(
                                f"[CONTAINER] {container_name}: {db_name} port {port} exposed on {host_ip}:{host_port}"
                            )

        return exposed

    def _check_compose_files(self) -> List[str]:
        """Check docker-compose.yml files for exposed database ports."""
        exposed = []

        projects = self.config.get('projects', [])

        for project in projects:
            compose_file = project.get('docker_compose')
            if not compose_file or not os.path.exists(compose_file):
                continue

            issues = self._parse_compose_file(compose_file, project.get('name', 'unknown'))
            exposed.extend(issues)

        return exposed

    def _parse_compose_file(self, filepath: str, project_name: str) -> List[str]:
        """Parse a docker-compose.yml file for dangerous port exposures."""
        exposed = []

        try:
            with open(filepath, 'r') as f:
                content = f.read()
        except Exception as e:
            self.logger.error(f"Could not read {filepath}: {e}")
            return exposed

        # Simple regex-based parsing (avoids YAML dependency in checks)
        # Look for patterns like:
        #   ports:
        #     - "5432:5432"
        #     - "3306:3306"

        for port, db_name in self.DANGEROUS_PORTS.items():
            # Match various port mapping formats
            patterns = [
                rf'["\']?\d*:?{port}:{port}["\']?',  # "5432:5432" or 5432:5432
                rf'["\']?{port}:{port}["\']?',       # "5432:5432"
                rf'["\']?\d+:{port}["\']?',          # "5433:5432" (host:container)
            ]

            for pattern in patterns:
                if re.search(pattern, content):
                    # Verify it's in a ports section (not just a comment)
                    lines = content.split('\n')
                    in_ports_section = False

                    for i, line in enumerate(lines):
                        stripped = line.strip()

                        if stripped.startswith('ports:'):
                            in_ports_section = True
                            continue

                        if in_ports_section:
                            # Check if we're still in the ports list
                            if stripped.startswith('-'):
                                if re.search(pattern, stripped):
                                    exposed.append(
                                        f"[COMPOSE] {project_name}: {db_name} port {port} exposed in {filepath}"
                                    )
                                    break
                            elif stripped and not stripped.startswith('#'):
                                # Exited ports section
                                in_ports_section = False

        return exposed
