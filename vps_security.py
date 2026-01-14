#!/usr/bin/env python3
"""
VPS Security Monitor
====================

Automated security monitoring and remediation for VPS servers.
Runs every 6 hours via systemd timer to detect and fix security issues.

Usage:
    python3 vps_security.py              # Run full security scan
    python3 vps_security.py --verbose    # Run with detailed output
    python3 vps_security.py --test-slack # Test Slack notification
    python3 vps_security.py --list-sessions    # List rollback sessions
    python3 vps_security.py --rollback <id>    # Rollback a session

Author: Nick Ave / Just Amazing BV
Created: 2026-01-13
"""

import os
import sys
import yaml
import argparse
import logging
from datetime import datetime
from typing import List, Tuple
from logging.handlers import RotatingFileHandler

# Add script directory to path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from checks import ALL_CHECKS, CheckResult, Severity
from remediation import RollbackManager, FirewallRemediation, PermissionRemediation
from notifications import SlackNotifier


def setup_logging(config: dict) -> logging.Logger:
    """Set up logging with file and console handlers.

    Args:
        config: Configuration dictionary

    Returns:
        Configured logger
    """
    log_config = config.get('logging', {})
    log_file = log_config.get('file', '/opt/vps-security/logs/security.log')
    log_level = getattr(logging, log_config.get('level', 'INFO').upper())
    max_size = log_config.get('max_size_mb', 10) * 1024 * 1024
    backup_count = log_config.get('backup_count', 5)

    # Ensure log directory exists
    log_dir = os.path.dirname(log_file)
    os.makedirs(log_dir, exist_ok=True)

    # Create logger
    logger = logging.getLogger('vps_security')
    logger.setLevel(log_level)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_size,
        backupCount=backup_count
    )
    file_handler.setLevel(log_level)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    # Console handler (if enabled or running verbose)
    if log_config.get('console', True):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_format = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

    return logger


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file.

    Args:
        config_path: Path to config.yaml

    Returns:
        Configuration dictionary
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Expand environment variables in webhook URL
    slack_config = config.get('notifications', {}).get('slack', {})
    webhook_url = slack_config.get('webhook_url', '')
    if webhook_url.startswith('${') and webhook_url.endswith('}'):
        env_var = webhook_url[2:-1]
        slack_config['webhook_url'] = os.environ.get(env_var, '')

    return config


def run_checks(config: dict, logger: logging.Logger) -> List[CheckResult]:
    """Run all security checks.

    Args:
        config: Configuration dictionary
        logger: Logger instance

    Returns:
        List of CheckResult objects
    """
    results = []

    for check_class in ALL_CHECKS:
        try:
            logger.info(f"Running check: {check_class.name}")
            check = check_class(config)
            result = check.run()
            results.append(result)

            # Log result
            if result.severity == Severity.OK:
                logger.info(f"  OK: {result.message}")
            elif result.severity == Severity.INFO:
                logger.info(f"  INFO: {result.message}")
            elif result.severity == Severity.WARNING:
                logger.warning(f"  WARNING: {result.message}")
            elif result.severity == Severity.CRITICAL:
                logger.error(f"  CRITICAL: {result.message}")

        except Exception as e:
            logger.error(f"Check {check_class.name} failed: {e}")
            results.append(CheckResult(
                check_name=check_class.name,
                severity=Severity.WARNING,
                message=f"Check failed with error: {e}",
                details=[str(e)],
                auto_fixable=False
            ))

    return results


def process_remediation(results: List[CheckResult], config: dict,
                        logger: logging.Logger) -> Tuple[List[Tuple], List[CheckResult]]:
    """Process results and apply auto-remediation where appropriate.

    Args:
        results: List of CheckResult objects
        config: Configuration dictionary
        logger: Logger instance

    Returns:
        Tuple of (auto_fixed, alerts)
    """
    remediation_config = config.get('remediation', {})

    if not remediation_config.get('enabled', True):
        logger.info("Auto-remediation is disabled")
        return [], [r for r in results if r.severity in [Severity.CRITICAL, Severity.WARNING, Severity.INFO]]

    # Initialize rollback manager
    backup_dir = remediation_config.get('backup_dir', '/opt/vps-security/backups')
    rollback_manager = RollbackManager(backup_dir)

    # Map fix actions to remediation classes
    remediation_map = {
        'enable_ufw': FirewallRemediation,
        'add_missing_rules': FirewallRemediation,
        'fix_env_permissions': PermissionRemediation,
    }

    auto_fix_actions = remediation_config.get('auto_fix', [])

    auto_fixed = []
    alerts = []

    for result in results:
        if result.severity == Severity.OK:
            continue

        # Check if this is auto-fixable
        if result.auto_fixable and result.fix_action:
            # Check if this action type is in auto_fix list
            action_type = None
            if 'firewall' in result.fix_action.lower() or result.fix_action in ['enable_ufw', 'add_missing_rules']:
                action_type = 'firewall_disabled' if 'enable' in result.fix_action else 'firewall_missing_rules'
            elif 'permission' in result.fix_action.lower():
                action_type = 'file_permissions'

            if action_type in auto_fix_actions or result.fix_action in auto_fix_actions:
                # Get remediation class
                remediation_class = remediation_map.get(result.fix_action)

                if remediation_class:
                    try:
                        logger.info(f"Auto-remediating: {result.check_name} ({result.fix_action})")
                        remediation = remediation_class(config, rollback_manager)
                        fix_result = remediation.execute(result)

                        if fix_result.success:
                            logger.info(f"  Fixed: {fix_result.action}")
                            auto_fixed.append((result, fix_result))
                        else:
                            logger.error(f"  Failed: {fix_result.error}")
                            alerts.append(result)

                    except Exception as e:
                        logger.error(f"Remediation failed: {e}")
                        alerts.append(result)
                else:
                    alerts.append(result)
            else:
                alerts.append(result)
        elif result.severity in [Severity.CRITICAL, Severity.WARNING, Severity.INFO]:
            alerts.append(result)

    return auto_fixed, alerts


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='VPS Security Monitor')
    parser.add_argument('--config', '-c', default=os.path.join(SCRIPT_DIR, 'config.yaml'),
                        help='Path to config file')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--test-slack', action='store_true',
                        help='Send a test Slack notification')
    parser.add_argument('--list-sessions', action='store_true',
                        help='List available rollback sessions')
    parser.add_argument('--rollback', metavar='SESSION_ID',
                        help='Rollback changes from a session')
    parser.add_argument('--dry-run', action='store_true',
                        help='Run checks but do not remediate or notify')

    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

    # Set up logging
    if args.verbose:
        config.setdefault('logging', {})['level'] = 'DEBUG'
        config['logging']['console'] = True

    logger = setup_logging(config)
    logger.info("=" * 60)
    logger.info(f"VPS Security Monitor started at {datetime.now()}")
    logger.info("=" * 60)

    # Handle special commands
    if args.test_slack:
        notifier = SlackNotifier(config)
        success = notifier.send_test_message()
        if success:
            print("Test message sent successfully!")
        else:
            print("Failed to send test message. Check webhook URL and logs.")
        sys.exit(0 if success else 1)

    if args.list_sessions:
        backup_dir = config.get('remediation', {}).get('backup_dir', '/opt/vps-security/backups')
        rollback_manager = RollbackManager(backup_dir)
        sessions = rollback_manager.list_sessions()

        if not sessions:
            print("No rollback sessions found.")
        else:
            print("\nAvailable rollback sessions:")
            print("-" * 60)
            for session in sessions:
                print(f"  {session['session_id']} - {session['created']} ({session['changes_count']} changes)")
        sys.exit(0)

    if args.rollback:
        backup_dir = config.get('remediation', {}).get('backup_dir', '/opt/vps-security/backups')
        rollback_manager = RollbackManager(backup_dir)
        result = rollback_manager.rollback_session(args.rollback)

        if result['success']:
            print(f"Rollback successful!")
            for item in result.get('rolled_back', []):
                print(f"  - {item}")
        else:
            print(f"Rollback failed: {result.get('error', 'Unknown error')}")
            for error in result.get('errors', []):
                print(f"  ERROR: {error}")
        sys.exit(0 if result['success'] else 1)

    # Run security checks
    logger.info("Running security checks...")
    results = run_checks(config, logger)

    # Process remediation
    if not args.dry_run:
        auto_fixed, alerts = process_remediation(results, config, logger)
    else:
        auto_fixed = []
        alerts = [r for r in results if r.severity in [Severity.CRITICAL, Severity.WARNING, Severity.INFO]]
        logger.info("Dry run - skipping remediation")

    # Determine if all OK
    all_ok = all(r.severity == Severity.OK for r in results)

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)

    critical_count = sum(1 for r in alerts if r.severity == Severity.CRITICAL)
    warning_count = sum(1 for r in alerts if r.severity == Severity.WARNING)
    info_count = sum(1 for r in alerts if r.severity == Severity.INFO)

    logger.info(f"Checks run: {len(results)}")
    logger.info(f"Auto-fixed: {len(auto_fixed)}")
    logger.info(f"Critical alerts: {critical_count}")
    logger.info(f"Warnings: {warning_count}")
    logger.info(f"Info: {info_count}")

    # Send Slack notification
    if not args.dry_run:
        notifier = SlackNotifier(config)

        # Only send if there are issues or we fixed something
        if not all_ok or auto_fixed:
            success = notifier.send_summary(auto_fixed, alerts, all_ok)
            if success:
                logger.info("Slack notification sent")
            else:
                logger.warning("Failed to send Slack notification")
        else:
            logger.info("All checks passed - skipping notification")

    logger.info("")
    logger.info(f"Scan completed at {datetime.now()}")

    # Exit with appropriate code
    if critical_count > 0:
        sys.exit(2)
    elif warning_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
