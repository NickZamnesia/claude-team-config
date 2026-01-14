"""Rollback manager for tracking and undoing changes."""

import os
import json
import shutil
from datetime import datetime
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


class RollbackManager:
    """Manages backups and rollbacks of security remediation changes."""

    def __init__(self, backup_dir: str, max_backups: int = 50):
        """Initialize rollback manager.

        Args:
            backup_dir: Directory to store backups
            max_backups: Maximum number of backup sessions to keep
        """
        self.backup_dir = backup_dir
        self.max_backups = max_backups
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_file = os.path.join(backup_dir, f"session_{self.session_id}.json")
        self.changes: List[Dict] = []

        # Ensure backup directory exists
        os.makedirs(backup_dir, exist_ok=True)

        # Clean up old backups
        self._cleanup_old_backups()

    def _cleanup_old_backups(self):
        """Remove old backup sessions beyond max_backups."""
        try:
            sessions = sorted([
                f for f in os.listdir(self.backup_dir)
                if f.startswith('session_') and f.endswith('.json')
            ])

            while len(sessions) > self.max_backups:
                oldest = sessions.pop(0)
                oldest_path = os.path.join(self.backup_dir, oldest)

                # Remove session file
                os.remove(oldest_path)

                # Remove associated backup files
                session_id = oldest.replace('session_', '').replace('.json', '')
                for f in os.listdir(self.backup_dir):
                    if f.startswith(f"backup_{session_id}_"):
                        os.remove(os.path.join(self.backup_dir, f))

                logger.info(f"Cleaned up old backup session: {oldest}")

        except Exception as e:
            logger.warning(f"Error cleaning up old backups: {e}")

    def record_file_change(self, filepath: str, backup_content: str = None):
        """Record a file change for potential rollback.

        Args:
            filepath: Path to the file being changed
            backup_content: Original content to backup (if applicable)
        """
        change = {
            'type': 'file',
            'path': filepath,
            'timestamp': datetime.now().isoformat(),
        }

        if backup_content is not None:
            backup_file = os.path.join(
                self.backup_dir,
                f"backup_{self.session_id}_{os.path.basename(filepath)}"
            )
            with open(backup_file, 'w') as f:
                f.write(backup_content)
            change['backup_file'] = backup_file

        self.changes.append(change)
        self._save()

    def record_permission_change(self, filepath: str, original_mode: str, new_mode: str):
        """Record a permission change for potential rollback.

        Args:
            filepath: Path to the file
            original_mode: Original permission mode (e.g., '644')
            new_mode: New permission mode (e.g., '600')
        """
        self.changes.append({
            'type': 'permission',
            'path': filepath,
            'original_mode': original_mode,
            'new_mode': new_mode,
            'timestamp': datetime.now().isoformat(),
        })
        self._save()

    def record_ufw_change(self, action: str, rules_before: str):
        """Record a UFW firewall change.

        Args:
            action: Description of the action taken
            rules_before: UFW rules before the change
        """
        backup_file = os.path.join(
            self.backup_dir,
            f"ufw_backup_{self.session_id}.txt"
        )
        with open(backup_file, 'w') as f:
            f.write(rules_before)

        self.changes.append({
            'type': 'ufw',
            'action': action,
            'backup_file': backup_file,
            'timestamp': datetime.now().isoformat(),
        })
        self._save()

    def record_command(self, command: str, description: str):
        """Record a command execution.

        Args:
            command: Command that was executed
            description: Description of what it did
        """
        self.changes.append({
            'type': 'command',
            'command': command,
            'description': description,
            'timestamp': datetime.now().isoformat(),
        })
        self._save()

    def _save(self):
        """Save the current session to disk."""
        try:
            with open(self.session_file, 'w') as f:
                json.dump({
                    'session_id': self.session_id,
                    'created': datetime.now().isoformat(),
                    'changes': self.changes,
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save session file: {e}")

    def get_session_id(self) -> str:
        """Get the current session ID."""
        return self.session_id

    def list_sessions(self) -> List[Dict]:
        """List all available rollback sessions.

        Returns:
            List of session info dictionaries
        """
        sessions = []
        try:
            for f in sorted(os.listdir(self.backup_dir), reverse=True):
                if f.startswith('session_') and f.endswith('.json'):
                    filepath = os.path.join(self.backup_dir, f)
                    with open(filepath, 'r') as file:
                        data = json.load(file)
                        sessions.append({
                            'session_id': data.get('session_id'),
                            'created': data.get('created'),
                            'changes_count': len(data.get('changes', [])),
                        })
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")

        return sessions

    def rollback_session(self, session_id: str) -> Dict:
        """Rollback all changes from a session.

        Args:
            session_id: ID of the session to rollback

        Returns:
            Dictionary with rollback results
        """
        session_file = os.path.join(self.backup_dir, f"session_{session_id}.json")

        if not os.path.exists(session_file):
            return {'success': False, 'error': f'Session {session_id} not found'}

        try:
            with open(session_file, 'r') as f:
                data = json.load(f)

            rolled_back = []
            errors = []

            # Process changes in reverse order
            for change in reversed(data.get('changes', [])):
                try:
                    if change['type'] == 'permission':
                        os.chmod(change['path'], int(change['original_mode'], 8))
                        rolled_back.append(f"Restored permissions on {change['path']}")

                    elif change['type'] == 'file' and change.get('backup_file'):
                        if os.path.exists(change['backup_file']):
                            shutil.copy(change['backup_file'], change['path'])
                            rolled_back.append(f"Restored file {change['path']}")

                    elif change['type'] == 'ufw':
                        # UFW rollback is more complex - just log for manual action
                        rolled_back.append(f"UFW change logged - manual review recommended")

                except Exception as e:
                    errors.append(f"Failed to rollback {change}: {e}")

            return {
                'success': len(errors) == 0,
                'rolled_back': rolled_back,
                'errors': errors,
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}
