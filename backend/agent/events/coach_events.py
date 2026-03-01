"""
Custom event types for the Communication Coach agent.

All events follow the Vision-Agents event conventions:
- Class name ends with 'Event'
- Has a 'type: str' attribute with a unique identifier
- Inherits from PluginBaseEvent or BaseEvent
- Uses dataclass + DataClassJsonMixin for serialization
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from vision_agents.core.events.base import PluginBaseEvent


# =============================================================================
# Speech Analysis Events
# =============================================================================


@dataclass
class FillerWordDetectedEvent(PluginBaseEvent):
    """Emitted when filler words are detected in user's speech.

    Not emitted for every single filler — only when a threshold is crossed
    within a time window (e.g., 3+ fillers in 60 seconds).
    """

    type: str = field(default="coach.filler_word_detected", init=False)
    word: str = ""
    """The filler word that was detected (e.g., 'um', 'uh', 'like')."""
    count_in_window: int = 0
    """Number of filler words in the current analysis window."""
    total_in_session: int = 0
    """Total filler word count in the entire session so far."""
    window_seconds: float = 60.0
    """The time window in seconds over which filler words are counted."""


@dataclass
class PaceAnalysisEvent(PluginBaseEvent):
    """Emitted periodically with speaking pace analysis.

    Recommended pace: 120-160 WPM for conversational speech.
    """

    type: str = field(default="coach.pace_analysis", init=False)
    words_per_minute: float = 0.0
    """Current speaking pace in words per minute."""
    recommendation: str = ""
    """One of: 'too_fast', 'too_slow', 'good'."""
    window_seconds: float = 30.0
    """The time window over which pace was measured."""


@dataclass
class HedgingLanguageEvent(PluginBaseEvent):
    """Emitted when hedging/uncertainty language is detected.

    Hedging phrases: 'I think maybe', 'I guess', 'sort of', 'probably',
    'I'm not sure but', 'kind of'.
    """

    type: str = field(default="coach.hedging_language", init=False)
    phrase: str = ""
    """The hedging phrase detected."""
    count_in_session: int = 0
    """Total hedging phrase count in the session."""


@dataclass
class ConfidenceScoreEvent(PluginBaseEvent):
    """Emitted periodically with the user's composite confidence score.

    Score is 0-100 based on filler words, pace, hedging, and silence patterns.
    """

    type: str = field(default="coach.confidence_score", init=False)
    score: float = 0.0
    """Composite confidence score from 0 (low) to 100 (high)."""
    factors: Dict[str, float] = field(default_factory=dict)
    """Breakdown of individual factor scores. Keys: 'filler_words', 'pace', 'hedging', 'silence'."""


# =============================================================================
# Body Language Events
# =============================================================================


@dataclass
class BodyLanguageEvent(PluginBaseEvent):
    """Emitted when notable body language is observed via video analysis."""

    type: str = field(default="coach.body_language", init=False)
    observation: str = ""
    """Human-readable observation (e.g., 'good eye contact', 'looking away frequently')."""
    category: str = ""
    """Category: 'eye_contact', 'posture', 'expression', 'gesture'."""
    quality: str = ""
    """Quality rating: 'good', 'needs_improvement', 'neutral'."""


# =============================================================================
# Session Events
# =============================================================================


@dataclass
class SessionSummaryEvent(PluginBaseEvent):
    """Emitted when a coaching session ends with a full summary."""

    type: str = field(default="coach.session_summary", init=False)
    duration_seconds: float = 0.0
    """Total session duration in seconds."""
    transcript: List[Dict[str, Any]] = field(default_factory=list)
    """List of transcript entries: [{'speaker': 'user'|'agent', 'text': '...', 'timestamp': ...}]."""
    metrics: Dict[str, Any] = field(default_factory=dict)
    """Aggregated session metrics."""
    overall_score: float = 0.0
    """Overall communication score for the session (0-100)."""
    strengths: List[str] = field(default_factory=list)
    """Top strengths identified during the session."""
    improvements: List[str] = field(default_factory=list)
    """Top areas for improvement."""
    exercises: List[Dict[str, str]] = field(default_factory=list)
    """Recommended exercises: [{'type': '...', 'prompt': '...', 'time_limit': ...}]."""


@dataclass
class ExercisePromptEvent(PluginBaseEvent):
    """Emitted when the coach suggests a specific exercise."""

    type: str = field(default="coach.exercise_prompt", init=False)
    exercise_type: str = ""
    """Type: 'elevator_pitch', 'summarize', 'explain_concisely', 'role_play'."""
    prompt: str = ""
    """The exercise prompt text."""
    time_limit_seconds: int = 0
    """Time limit for the exercise (0 = no limit)."""
