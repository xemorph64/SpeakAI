"""
Progress Tracker — SQLite-based persistence for session history and gamification.

Stores session summaries, tracks scores over time, manages levels/badges/streaks,
and provides data for the dashboard.
"""

import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "coach.db"
)

# Gamification levels
LEVELS = [
    {"name": "Beginner", "min_score": 0, "sessions_required": 0},
    {"name": "Conversationalist", "min_score": 30, "sessions_required": 3},
    {"name": "Articulate", "min_score": 50, "sessions_required": 8},
    {"name": "Eloquent", "min_score": 70, "sessions_required": 15},
    {"name": "Master Communicator", "min_score": 85, "sessions_required": 30},
]

# Badge definitions
BADGES = [
    {
        "id": "first_session",
        "name": "First Steps",
        "description": "Complete your first coaching session",
        "condition": lambda stats: stats["total_sessions"] >= 1,
    },
    {
        "id": "filler_buster",
        "name": "Filler Buster",
        "description": "Complete a session with fewer than 2 filler words per minute",
        "condition": lambda stats: stats.get("last_filler_rate", 999) < 2,
    },
    {
        "id": "pace_master",
        "name": "Pace Master",
        "description": "Maintain a good pace (120-160 WPM) throughout a session",
        "condition": lambda stats: stats.get("last_pace_good", False),
    },
    {
        "id": "streak_3",
        "name": "On a Roll",
        "description": "Practice 3 days in a row",
        "condition": lambda stats: stats.get("current_streak", 0) >= 3,
    },
    {
        "id": "streak_7",
        "name": "Week Warrior",
        "description": "Practice 7 days in a row",
        "condition": lambda stats: stats.get("current_streak", 0) >= 7,
    },
    {
        "id": "ten_sessions",
        "name": "Dedicated Learner",
        "description": "Complete 10 coaching sessions",
        "condition": lambda stats: stats["total_sessions"] >= 10,
    },
    {
        "id": "high_scorer",
        "name": "Communication Pro",
        "description": "Score 80+ in a session",
        "condition": lambda stats: stats.get("last_score", 0) >= 80,
    },
    {
        "id": "improver",
        "name": "Rising Star",
        "description": "Improve your score by 10+ points from your first session",
        "condition": lambda stats: (
            stats.get("last_score", 0) - stats.get("first_score", 0) >= 10
        ),
    },
]


class ProgressTracker:
    """SQLite-based session history and gamification tracker."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or DEFAULT_DB_PATH

        # Ensure data directory exists
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)

        # Initialize database
        self._init_db()

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    overall_score REAL NOT NULL,
                    metrics TEXT NOT NULL,
                    strengths TEXT NOT NULL,
                    improvements TEXT NOT NULL,
                    exercises TEXT NOT NULL,
                    transcript TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS badges (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    earned_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS exercises_completed (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    exercise_type TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );
            """)

    def save_session(self, summary: Dict[str, Any]) -> int:
        """Save a session summary and return the session ID."""
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO sessions (timestamp, duration_seconds, overall_score,
                                      metrics, strengths, improvements, exercises, transcript)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().isoformat(),
                    summary.get("duration_seconds", 0),
                    summary.get("overall_score", 0),
                    json.dumps(summary.get("metrics", {})),
                    json.dumps(summary.get("strengths", [])),
                    json.dumps(summary.get("improvements", [])),
                    json.dumps(summary.get("exercises", [])),
                    json.dumps(summary.get("transcript", [])),
                ),
            )
            session_id = cursor.lastrowid
            logger.info(f"Session saved with ID: {session_id}")

            # Check for new badges
            self._check_badges(conn, summary)

            return session_id

    def get_session_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent session history."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, timestamp, duration_seconds, overall_score,
                       metrics, strengths, improvements, exercises
                FROM sessions
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            return [
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "duration_seconds": row["duration_seconds"],
                    "overall_score": row["overall_score"],
                    "metrics": json.loads(row["metrics"]),
                    "strengths": json.loads(row["strengths"]),
                    "improvements": json.loads(row["improvements"]),
                    "exercises": json.loads(row["exercises"]),
                }
                for row in rows
            ]

    def get_session_detail(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Return detailed data for a single session."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()

            if not row:
                return None

            return {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "duration_seconds": row["duration_seconds"],
                "overall_score": row["overall_score"],
                "metrics": json.loads(row["metrics"]),
                "strengths": json.loads(row["strengths"]),
                "improvements": json.loads(row["improvements"]),
                "exercises": json.loads(row["exercises"]),
                "transcript": json.loads(row["transcript"]),
            }

    def get_score_trend(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Return score trend data for charting."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT timestamp, overall_score, metrics
                FROM sessions
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            trend = []
            for row in rows:
                metrics = json.loads(row["metrics"])
                trend.append({
                    "timestamp": row["timestamp"],
                    "overall_score": row["overall_score"],
                    "filler_rate": (
                        metrics.get("total_filler_words", 0) /
                        max(metrics.get("duration_seconds", 1) / 60.0, 0.01)
                    ),
                    "vocabulary_diversity": metrics.get("vocabulary_diversity", 0),
                })

            # Reverse so oldest first (for charting)
            return list(reversed(trend))

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics for dashboard."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Total sessions and average score
            stats_row = conn.execute(
                """
                SELECT COUNT(*) as total, AVG(overall_score) as avg_score,
                       MAX(overall_score) as best_score
                FROM sessions
                """
            ).fetchone()

            total_sessions = stats_row["total"] or 0
            avg_score = stats_row["avg_score"] or 0
            best_score = stats_row["best_score"] or 0

            # First and last scores
            first_row = conn.execute(
                "SELECT overall_score FROM sessions ORDER BY timestamp ASC LIMIT 1"
            ).fetchone()
            last_row = conn.execute(
                "SELECT overall_score, metrics FROM sessions ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()

            first_score = first_row["overall_score"] if first_row else 0
            last_score = last_row["overall_score"] if last_row else 0

            # Last session metrics for badge checking
            last_metrics = json.loads(last_row["metrics"]) if last_row else {}
            last_duration = last_metrics.get("duration_seconds", 0)
            last_filler_rate = (
                last_metrics.get("total_filler_words", 0) / max(last_duration / 60.0, 0.01)
                if last_duration > 0 else 999
            )

            # Pace check
            pace_readings = last_metrics.get("pace_readings", [])
            last_pace_good = all(
                120 <= r.get("wpm", 0) <= 160 for r in pace_readings
            ) if pace_readings else False

            # Streak calculation
            streak = self._calculate_streak(conn)

            # Current level
            level = self._calculate_level(total_sessions, last_score)

            # Earned badges
            badges = self._get_badges(conn)

            # Total practice time
            total_time = conn.execute(
                "SELECT SUM(duration_seconds) as total FROM sessions"
            ).fetchone()["total"] or 0

            return {
                "total_sessions": total_sessions,
                "avg_score": round(avg_score, 1),
                "best_score": round(best_score, 1),
                "first_score": round(first_score, 1),
                "last_score": round(last_score, 1),
                "last_filler_rate": round(last_filler_rate, 1),
                "last_pace_good": last_pace_good,
                "current_streak": streak,
                "level": level,
                "badges": badges,
                "total_practice_minutes": round(total_time / 60.0, 1),
            }

    def _calculate_streak(self, conn: sqlite3.Connection) -> int:
        """Calculate current practice day streak."""
        rows = conn.execute(
            """
            SELECT DISTINCT DATE(timestamp) as day
            FROM sessions
            ORDER BY day DESC
            """
        ).fetchall()

        if not rows:
            return 0

        streak = 0
        today = datetime.now().date()

        for row in rows:
            day = datetime.fromisoformat(row[0]).date()
            expected = today - timedelta(days=streak)
            if day == expected:
                streak += 1
            else:
                break

        return streak

    def _calculate_level(self, total_sessions: int, latest_score: float) -> Dict[str, Any]:
        """Determine current level based on sessions and score."""
        current_level = LEVELS[0]
        next_level = LEVELS[1] if len(LEVELS) > 1 else None

        for i, level in enumerate(LEVELS):
            if total_sessions >= level["sessions_required"] and latest_score >= level["min_score"]:
                current_level = level
                next_level = LEVELS[i + 1] if i + 1 < len(LEVELS) else None

        return {
            "current": current_level["name"],
            "next": next_level["name"] if next_level else None,
            "sessions_to_next": (
                max(0, next_level["sessions_required"] - total_sessions)
                if next_level else 0
            ),
            "score_needed": next_level["min_score"] if next_level else 0,
        }

    def _check_badges(self, conn: sqlite3.Connection, summary: Dict[str, Any]) -> None:
        """Check and award new badges after a session."""
        stats = self.get_stats()

        # Override with latest session data
        stats["last_score"] = summary.get("overall_score", 0)

        earned = {row[0] for row in conn.execute("SELECT id FROM badges").fetchall()}

        for badge in BADGES:
            if badge["id"] not in earned:
                try:
                    if badge["condition"](stats):
                        conn.execute(
                            "INSERT INTO badges (id, name, description, earned_at) VALUES (?, ?, ?, ?)",
                            (badge["id"], badge["name"], badge["description"],
                             datetime.now().isoformat()),
                        )
                        logger.info(f"Badge earned: {badge['name']} — {badge['description']}")
                except Exception as e:
                    logger.debug(f"Badge check error for {badge['id']}: {e}")

    def _get_badges(self, conn: sqlite3.Connection) -> List[Dict[str, str]]:
        """Return all earned badges."""
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, name, description, earned_at FROM badges ORDER BY earned_at"
        ).fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "earned_at": row["earned_at"],
            }
            for row in rows
        ]
