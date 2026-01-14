"""Check SSL certificate expiration."""

import ssl
import socket
from datetime import datetime
from typing import List, Tuple, Optional
from .base import BaseCheck, CheckResult, Severity


class SSLCertificatesCheck(BaseCheck):
    """Monitor SSL certificate expiration dates."""

    name = "SSL Certificates"
    description = "Checks SSL certificate expiration for configured domains"

    def run(self) -> CheckResult:
        """Check SSL certificate expiration dates."""
        ssl_config = self.config.get('ssl', {})
        domains = ssl_config.get('domains', [])
        warning_days = ssl_config.get('warning_days_before_expiry', 14)
        critical_days = ssl_config.get('critical_days_before_expiry', 7)

        if not domains:
            return self._ok_result(
                message="No SSL domains configured to monitor",
                details=["Add domains to config.yaml under ssl.domains"]
            )

        results = []
        critical_domains = []
        warning_domains = []
        ok_domains = []
        error_domains = []

        for domain in domains:
            expiry = self._get_cert_expiry(domain)

            if expiry is None:
                error_domains.append(domain)
                results.append(f"{domain}: Could not check certificate")
                continue

            days_left = (expiry - datetime.now()).days

            if days_left <= 0:
                critical_domains.append((domain, days_left))
                results.append(f"{domain}: EXPIRED {abs(days_left)} days ago!")
            elif days_left <= critical_days:
                critical_domains.append((domain, days_left))
                results.append(f"{domain}: CRITICAL - expires in {days_left} days")
            elif days_left <= warning_days:
                warning_domains.append((domain, days_left))
                results.append(f"{domain}: WARNING - expires in {days_left} days")
            else:
                ok_domains.append((domain, days_left))
                results.append(f"{domain}: OK - expires in {days_left} days")

        # Determine overall severity
        if critical_domains:
            details = results + [
                "",
                "To renew certificates:",
                "  certbot renew --dry-run  # Test renewal",
                "  certbot renew            # Actually renew"
            ]

            return self._critical_result(
                message=f"SSL certificates expiring soon: {len(critical_domains)}",
                details=details,
                raw_data={
                    'critical': critical_domains,
                    'warning': warning_domains,
                    'ok': ok_domains
                }
            )

        if warning_domains:
            details = results + [
                "",
                "Consider renewing soon:",
                "  certbot renew"
            ]

            return self._warning_result(
                message=f"SSL certificates expiring within {warning_days} days: {len(warning_domains)}",
                details=details,
                raw_data={
                    'warning': warning_domains,
                    'ok': ok_domains
                }
            )

        return self._ok_result(
            message=f"All {len(ok_domains)} SSL certificates valid",
            details=results
        )

    def _get_cert_expiry(self, domain: str, port: int = 443) -> Optional[datetime]:
        """Get the expiration date of an SSL certificate.

        Args:
            domain: Domain name to check
            port: Port number (default 443)

        Returns:
            Expiration datetime or None if check failed
        """
        try:
            context = ssl.create_default_context()

            with socket.create_connection((domain, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()

                    # Parse expiry date
                    # Format: 'Jun 15 12:00:00 2024 GMT'
                    expiry_str = cert.get('notAfter')
                    if expiry_str:
                        expiry = datetime.strptime(
                            expiry_str,
                            '%b %d %H:%M:%S %Y %Z'
                        )
                        return expiry

        except ssl.SSLError as e:
            self.logger.warning(f"SSL error checking {domain}: {e}")
        except socket.timeout:
            self.logger.warning(f"Timeout checking SSL for {domain}")
        except socket.gaierror as e:
            self.logger.warning(f"DNS error for {domain}: {e}")
        except Exception as e:
            self.logger.warning(f"Error checking SSL for {domain}: {e}")

        # Fallback: try using openssl command
        return self._get_cert_expiry_openssl(domain, port)

    def _get_cert_expiry_openssl(self, domain: str, port: int = 443) -> Optional[datetime]:
        """Get certificate expiry using openssl command (fallback).

        Args:
            domain: Domain name
            port: Port number

        Returns:
            Expiration datetime or None
        """
        try:
            returncode, stdout, stderr = self._execute_command(
                f"echo | openssl s_client -servername {domain} -connect {domain}:{port} 2>/dev/null | "
                f"openssl x509 -noout -enddate 2>/dev/null"
            )

            if returncode == 0 and 'notAfter=' in stdout:
                # Parse "notAfter=Jun 15 12:00:00 2024 GMT"
                date_str = stdout.split('=')[1].strip()
                return datetime.strptime(date_str, '%b %d %H:%M:%S %Y %Z')

        except Exception as e:
            self.logger.warning(f"OpenSSL fallback failed for {domain}: {e}")

        return None
