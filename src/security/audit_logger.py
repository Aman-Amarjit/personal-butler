"""
Audit Logger

Maintains tamper-proof audit trail with cryptographic signing
and integrity verification.
"""

import logging
import json
import sqlite3
import hmac
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path


logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Maintains cryptographically signed audit logs.
    
    Features:
    - Event logging with timestamps
    - HMAC-SHA256 signing
    - Log integrity verification
    - Log rotation (30-day retention)
    - Audit log export
    """

    def __init__(
        self,
        db_path: str = "data/audit.db",
        secret_key: Optional[str] = None,
        retention_days: int = 30
    ):
        """
        Initialize audit logger.

        Args:
            db_path: Path to audit database
            secret_key: Secret key for HMAC signing
            retention_days: Log retention period in days
        """
        self.db_path = db_path
        # Generate a machine-specific key if none provided
        # (never hardcode a real secret here — use config/local.json for production)
        if secret_key:
            self.secret_key = secret_key
        else:
            import hashlib, platform
            machine_id = platform.node() + platform.machine()
            self.secret_key = hashlib.sha256(machine_id.encode()).hexdigest()[:32]
        self.retention_days = retention_days

        # Create database directory if needed
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Initialize audit database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create audit log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    user TEXT,
                    details TEXT,
                    signature TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # Create index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON audit_logs(timestamp)
            """)

            conn.commit()
            conn.close()

            logger.info("Audit database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize audit database: {e}")

    def log_action(
        self,
        action: str,
        user: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log an action with cryptographic signature.

        Args:
            action: Action description
            user: User performing action
            details: Additional details

        Returns:
            True if successful, False otherwise
        """
        try:
            timestamp = datetime.now().isoformat()
            details_json = json.dumps(details or {})

            # Create signature
            signature = self._create_signature(
                timestamp, action, user, details_json
            )

            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO audit_logs 
                (timestamp, action, user, details, signature, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (timestamp, action, user, details_json, signature, timestamp))

            conn.commit()
            conn.close()

            logger.info(f"Action logged: {action} by {user}")
            return True

        except Exception as e:
            logger.error(f"Failed to log action: {e}")
            return False

    def _create_signature(
        self,
        timestamp: str,
        action: str,
        user: Optional[str],
        details: str
    ) -> str:
        """Create HMAC-SHA256 signature"""
        message = f"{timestamp}:{action}:{user}:{details}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    def verify_log_integrity(self, log_id: int) -> bool:
        """
        Verify integrity of a log entry.

        Args:
            log_id: Log entry ID

        Returns:
            True if signature is valid, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT timestamp, action, user, details, signature
                FROM audit_logs WHERE id = ?
            """, (log_id,))

            row = cursor.fetchone()
            conn.close()

            if not row:
                logger.warning(f"Log entry not found: {log_id}")
                return False

            timestamp, action, user, details, stored_signature = row

            # Recalculate signature
            calculated_signature = self._create_signature(
                timestamp, action, user, details
            )

            # Compare signatures
            is_valid = hmac.compare_digest(stored_signature, calculated_signature)

            if not is_valid:
                logger.warning(f"Log integrity check failed: {log_id}")

            return is_valid

        except Exception as e:
            logger.error(f"Error verifying log integrity: {e}")
            return False

    def get_audit_trail(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        action_filter: Optional[str] = None,
        user_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get audit trail for specified time range.

        Args:
            start_time: Start time for query
            end_time: End time for query
            action_filter: Filter by action
            user_filter: Filter by user

        Returns:
            List of audit log entries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = "SELECT * FROM audit_logs WHERE 1=1"
            params = []

            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())

            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())

            if action_filter:
                query += " AND action LIKE ?"
                params.append(f"%{action_filter}%")

            if user_filter:
                query += " AND user = ?"
                params.append(user_filter)

            query += " ORDER BY timestamp DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            # Convert to dictionaries
            logs = []
            for row in rows:
                logs.append({
                    "id": row[0],
                    "timestamp": row[1],
                    "action": row[2],
                    "user": row[3],
                    "details": json.loads(row[4]),
                    "signature": row[5]
                })

            return logs

        except Exception as e:
            logger.error(f"Error retrieving audit trail: {e}")
            return []

    def export_audit_logs(
        self,
        export_path: str,
        format: str = "json"
    ) -> bool:
        """
        Export audit logs to file.

        Args:
            export_path: Path to export file
            format: Export format (json or csv)

        Returns:
            True if successful, False otherwise
        """
        try:
            logs = self.get_audit_trail()

            if format == "json":
                with open(export_path, "w") as f:
                    json.dump(logs, f, indent=2)
            elif format == "csv":
                import csv
                with open(export_path, "w", newline="") as f:
                    if logs:
                        writer = csv.DictWriter(f, fieldnames=logs[0].keys())
                        writer.writeheader()
                        writer.writerows(logs)
            else:
                logger.error(f"Unsupported export format: {format}")
                return False

            logger.info(f"Audit logs exported to {export_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export audit logs: {e}")
            return False

    def rotate_logs(self) -> int:
        """
        Rotate logs older than retention period.

        Returns:
            Number of logs deleted
        """
        try:
            cutoff_date = (
                datetime.now() - timedelta(days=self.retention_days)
            ).isoformat()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get count of logs to delete
            cursor.execute(
                "SELECT COUNT(*) FROM audit_logs WHERE timestamp < ?",
                (cutoff_date,)
            )
            count = cursor.fetchone()[0]

            # Delete old logs
            cursor.execute(
                "DELETE FROM audit_logs WHERE timestamp < ?",
                (cutoff_date,)
            )

            conn.commit()
            conn.close()

            if count > 0:
                logger.info(f"Rotated {count} old audit logs")

            return count

        except Exception as e:
            logger.error(f"Error rotating logs: {e}")
            return 0

    def get_status(self) -> Dict[str, Any]:
        """Get audit logger status"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM audit_logs")
            log_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT MIN(timestamp), MAX(timestamp) FROM audit_logs"
            )
            min_max = cursor.fetchone()
            conn.close()

            return {
                "db_path": self.db_path,
                "log_count": log_count,
                "retention_days": self.retention_days,
                "oldest_log": min_max[0] if min_max[0] else None,
                "newest_log": min_max[1] if min_max[1] else None
            }

        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {}

    # ------------------------------------------------------------------
    # Convenience aliases used by integration tests
    # ------------------------------------------------------------------

    def log(
        self,
        action: str,
        user: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Alias for log_action."""
        return self.log_action(action=action, user=user, details=details)

    def get_entries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return the most recent *limit* audit entries."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            conn.close()
            return [
                {
                    "id": row[0],
                    "timestamp": row[1],
                    "action": row[2],
                    "user": row[3],
                    "details": json.loads(row[4]),
                    "signature": row[5],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Error getting entries: {e}")
            return []

    def verify_integrity(self) -> bool:
        """Verify integrity of all log entries. Returns True if all pass."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM audit_logs")
            ids = [row[0] for row in cursor.fetchall()]
            conn.close()
            return all(self.verify_log_integrity(log_id) for log_id in ids)
        except Exception as e:
            logger.error(f"Error verifying integrity: {e}")
            return False
