"""
Report Generator — Creates formatted post-session reports.

Takes a SessionSummaryEvent and produces a readable report string,
and handles persisting data to the ProgressTracker.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from post_session.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates formatted post-session reports and persists to database."""

    def __init__(self, progress_tracker: Optional[ProgressTracker] = None):
        self._tracker = progress_tracker or ProgressTracker()

    def generate_report(self, summary_data: Dict[str, Any]) -> str:
        """Generate a formatted text report from session summary data.

        Args:
            summary_data: Dict with keys matching SessionSummaryEvent fields.

        Returns:
            Formatted report string.
        """
        duration = summary_data.get("duration_seconds", 0)
        score = summary_data.get("overall_score", 0)
        metrics = summary_data.get("metrics", {})
        strengths = summary_data.get("strengths", [])
        improvements = summary_data.get("improvements", [])
        exercises = summary_data.get("exercises", [])

        # Format duration
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        duration_str = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

        # Build report
        lines = []
        lines.append("=" * 50)
        lines.append("  COMMUNICATION COACHING SESSION REPORT")
        lines.append(f"  {datetime.now().strftime('%B %d, %Y  %I:%M %p')}")
        lines.append("=" * 50)
        lines.append("")

        # Overview
        lines.append(f"  Duration:        {duration_str}")
        lines.append(f"  Overall Score:   {score:.0f}/100")
        lines.append(f"  Words Spoken:    {metrics.get('total_words_spoken', 0)}")
        lines.append(f"  Filler Words:    {metrics.get('total_filler_words', 0)}")
        lines.append(f"  Hedging Phrases: {metrics.get('total_hedging_phrases', 0)}")

        vocab_div = metrics.get("vocabulary_diversity", 0)
        lines.append(f"  Vocabulary:      {vocab_div:.1%} diversity")
        lines.append("")

        # Filler word breakdown
        filler_breakdown = metrics.get("filler_breakdown", {})
        if filler_breakdown:
            lines.append("  FILLER WORD BREAKDOWN")
            lines.append("  " + "-" * 30)
            for word, count in sorted(filler_breakdown.items(), key=lambda x: -x[1]):
                lines.append(f"    '{word}': {count}x")
            lines.append("")

        # Pace readings
        pace_readings = metrics.get("pace_readings", [])
        if pace_readings:
            avg_pace = sum(r["wpm"] for r in pace_readings) / len(pace_readings)
            lines.append(f"  Average Pace:    {avg_pace:.0f} WPM")
            lines.append(f"  (Ideal range: 120-160 WPM)")
            lines.append("")

        # Strengths
        lines.append("  YOUR STRENGTHS")
        lines.append("  " + "-" * 30)
        for i, s in enumerate(strengths, 1):
            lines.append(f"    {i}. {s}")
        lines.append("")

        # Improvements
        lines.append("  AREAS TO IMPROVE")
        lines.append("  " + "-" * 30)
        for i, imp in enumerate(improvements, 1):
            lines.append(f"    {i}. {imp}")
        lines.append("")

        # Exercises
        if exercises:
            lines.append("  RECOMMENDED EXERCISES")
            lines.append("  " + "-" * 30)
            for i, ex in enumerate(exercises, 1):
                lines.append(f"    {i}. [{ex.get('type', 'general')}]")
                lines.append(f"       {ex.get('prompt', '')}")
                time_limit = ex.get("time_limit", "0")
                if time_limit and time_limit != "0":
                    lines.append(f"       Time limit: {time_limit}s")
                lines.append("")

        lines.append("=" * 50)

        return "\n".join(lines)

    def save_and_report(self, summary_data: Dict[str, Any]) -> str:
        """Save session to database and return formatted report.

        Args:
            summary_data: Dict with session summary fields.

        Returns:
            Formatted report string.
        """
        # Save to database
        session_id = self._tracker.save_session(summary_data)
        logger.info(f"Session {session_id} saved to database")

        # Get updated stats for the report
        stats = self._tracker.get_stats()

        # Generate the report
        report = self.generate_report(summary_data)

        # Append gamification info
        level_info = stats.get("level", {})
        report += f"\n  Level: {level_info.get('current', 'Beginner')}"
        if level_info.get("next"):
            report += f" → Next: {level_info['next']}"
            sessions_needed = level_info.get("sessions_to_next", 0)
            if sessions_needed:
                report += f" ({sessions_needed} more sessions)"
        report += f"\n  Streak: {stats.get('current_streak', 0)} days"
        report += f"\n  Total Sessions: {stats.get('total_sessions', 0)}"
        report += f"\n  Total Practice: {stats.get('total_practice_minutes', 0):.0f} minutes"

        # New badges
        badges = stats.get("badges", [])
        if badges:
            report += f"\n  Badges: {', '.join(b['name'] for b in badges)}"

        report += "\n" + "=" * 50

        return report
