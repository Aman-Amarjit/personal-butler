"""
Episodic Memory with Temporal Decay

Based on research:
- "Memory in the Age of AI Agents" (arXiv:2512.13564)
- "A Large Language Model with Temporal Episodic Memory" (arXiv:2502.16090)
- "Continuous Dynamics for Context Preservation" (arXiv:2602.21220)
  — thermodynamic decay: importance decays as exp(-λt) where λ is
    inversely proportional to emotional salience

Design:
  - SQLite-backed episodic store (local-first, no cloud)
  - Each memory has: content, timestamp, emotional_valence, importance
  - Temporal decay: importance *= exp(-decay_rate * hours_elapsed)
  - Retrieval: recency + importance + semantic similarity (keyword-based)
  - Consolidation: low-importance memories pruned after retention_days
"""

import sqlite3
import json
import math
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

log = logging.getLogger("panda.memory.episodic")


@dataclass
class Episode:
    """A single episodic memory."""
    content: str                    # What happened / was said
    role: str                       # "user" | "assistant" | "system"
    timestamp: float                # Unix timestamp
    emotional_valence: float        # -1.0 (negative) to +1.0 (positive)
    importance: float               # 0.0 to 1.0 (decays over time)
    tags: List[str]                 # Keywords for retrieval
    session_id: str = ""            # Groups episodes in a conversation
    id: Optional[int] = None        # DB row id


# Decay constant: half-life of ~48 hours for neutral memories
# High-valence memories decay slower (emotional salience effect)
BASE_DECAY_RATE = 0.014             # per hour → half-life ≈ 50 h
SALIENCE_FACTOR = 0.5               # reduces decay for emotional memories


def _decay_factor(hours: float, valence: float) -> float:
    """
    Thermodynamic decay from arXiv:2602.21220.
    λ = BASE_DECAY_RATE / (1 + |valence| * SALIENCE_FACTOR)
    importance(t) = importance(0) * exp(-λ * t)
    """
    lam = BASE_DECAY_RATE / (1.0 + abs(valence) * SALIENCE_FACTOR)
    return math.exp(-lam * hours)


class EpisodicMemory:
    """
    Local episodic memory store with temporal decay.

    Usage:
        mem = EpisodicMemory("data/panda.db")
        mem.store("User asked about weather", role="user", valence=0.1)
        recent = mem.get_recent_context(hours=2)
        relevant = mem.search("weather forecast", top_k=5)
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS episodes (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        content         TEXT    NOT NULL,
        role            TEXT    NOT NULL DEFAULT 'user',
        timestamp       REAL    NOT NULL,
        emotional_valence REAL  NOT NULL DEFAULT 0.0,
        importance      REAL    NOT NULL DEFAULT 0.5,
        tags            TEXT    NOT NULL DEFAULT '[]',
        session_id      TEXT    NOT NULL DEFAULT ''
    );
    CREATE INDEX IF NOT EXISTS idx_ep_timestamp ON episodes(timestamp);
    CREATE INDEX IF NOT EXISTS idx_ep_session   ON episodes(session_id);
    """

    def __init__(self, db_path: str = "data/panda.db",
                 retention_days: int = 30):
        self.db_path = db_path
        self.retention_days = retention_days
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(self.SCHEMA)

    # ── Write ─────────────────────────────────────────────────────────────────

    def store(
        self,
        content: str,
        role: str = "user",
        valence: float = 0.0,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        session_id: str = "",
    ) -> int:
        """Store a new episode. Returns the row id."""
        tags = tags or _extract_keywords(content)
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO episodes
                   (content, role, timestamp, emotional_valence, importance, tags, session_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (content, role, time.time(), valence, importance,
                 json.dumps(tags), session_id),
            )
            return cur.lastrowid

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_recent_context(
        self, hours: float = 2.0, limit: int = 20
    ) -> List[Episode]:
        """Return the most recent episodes within the last `hours`."""
        since = time.time() - hours * 3600
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT * FROM episodes
                   WHERE timestamp >= ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (since, limit),
            ).fetchall()
        return [self._row_to_episode(r) for r in rows]

    def search(self, query: str, top_k: int = 5) -> List[Episode]:
        """
        Keyword-based semantic search.
        Scores each episode by keyword overlap + recency + importance.
        """
        keywords = set(_extract_keywords(query))
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM episodes ORDER BY timestamp DESC LIMIT 200"
            ).fetchall()

        scored: List[tuple] = []
        now = time.time()
        for row in rows:
            ep = self._row_to_episode(row)
            ep_tags = set(ep.tags)
            overlap = len(keywords & ep_tags) / max(len(keywords), 1)
            hours_ago = (now - ep.timestamp) / 3600
            decay = _decay_factor(hours_ago, ep.emotional_valence)
            score = overlap * 0.5 + decay * ep.importance * 0.5
            if score > 0.01:
                scored.append((score, ep))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [ep for _, ep in scored[:top_k]]

    def get_session(self, session_id: str) -> List[Episode]:
        """Return all episodes for a session, oldest first."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM episodes WHERE session_id=? ORDER BY timestamp ASC",
                (session_id,),
            ).fetchall()
        return [self._row_to_episode(r) for r in rows]

    def format_context(self, episodes: List[Episode], max_chars: int = 1500) -> str:
        """Format episodes as a readable context string for the LLM."""
        lines = []
        for ep in reversed(episodes):  # oldest first
            dt = datetime.fromtimestamp(ep.timestamp).strftime("%H:%M")
            lines.append(f"[{dt}] {ep.role.upper()}: {ep.content}")
        text = "\n".join(lines)
        return text[-max_chars:] if len(text) > max_chars else text

    # ── Maintenance ───────────────────────────────────────────────────────────

    def apply_decay_and_prune(self) -> int:
        """
        Apply temporal decay to all episodes and delete expired ones.
        Returns number of deleted episodes.
        """
        now = time.time()
        cutoff = now - self.retention_days * 86400

        with self._conn() as conn:
            rows = conn.execute("SELECT id, timestamp, emotional_valence, importance FROM episodes").fetchall()
            updates = []
            deletes = []
            for row in rows:
                hours = (now - row["timestamp"]) / 3600
                new_imp = row["importance"] * _decay_factor(hours, row["emotional_valence"])
                if row["timestamp"] < cutoff or new_imp < 0.02:
                    deletes.append(row["id"])
                else:
                    updates.append((new_imp, row["id"]))

            if updates:
                conn.executemany("UPDATE episodes SET importance=? WHERE id=?", updates)
            if deletes:
                conn.execute(f"DELETE FROM episodes WHERE id IN ({','.join('?'*len(deletes))})", deletes)

        log.info(f"Memory decay: updated {len(updates)}, pruned {len(deletes)} episodes")
        return len(deletes)

    def stats(self) -> Dict[str, Any]:
        with self._conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
            oldest = conn.execute("SELECT MIN(timestamp) FROM episodes").fetchone()[0]
            newest = conn.execute("SELECT MAX(timestamp) FROM episodes").fetchone()[0]
        return {
            "total_episodes": count,
            "oldest": datetime.fromtimestamp(oldest).isoformat() if oldest else None,
            "newest": datetime.fromtimestamp(newest).isoformat() if newest else None,
            "retention_days": self.retention_days,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_episode(row: sqlite3.Row) -> Episode:
        return Episode(
            id=row["id"],
            content=row["content"],
            role=row["role"],
            timestamp=row["timestamp"],
            emotional_valence=row["emotional_valence"],
            importance=row["importance"],
            tags=json.loads(row["tags"]),
            session_id=row["session_id"],
        )


def _extract_keywords(text: str) -> List[str]:
    """Simple keyword extraction — stopword removal + lowercasing."""
    STOPWORDS = {
        "a","an","the","is","it","in","on","at","to","for","of","and","or",
        "but","not","with","this","that","was","are","be","been","have","has",
        "do","did","will","would","could","should","may","might","i","you",
        "he","she","we","they","me","him","her","us","them","my","your",
        "his","its","our","their","what","when","where","who","how","why",
        "can","just","so","if","then","than","as","by","from","up","about",
        "into","through","during","before","after","above","below","between",
    }
    import re
    words = re.findall(r"\b[a-z]{3,}\b", text.lower())
    return list({w for w in words if w not in STOPWORDS})[:20]
