"""
VideoAnalyzerProcessor — Analyzes video frames for body language cues.

Since we're using Gemini Realtime (which natively processes video frames),
this processor works by:
1. Subscribing to agent events to know when video analysis should happen
2. Maintaining state about observed body language patterns
3. Emitting BodyLanguageEvent when notable observations are made

The actual video understanding is delegated to Gemini's multimodal capabilities.
This processor adds structured tracking and event emission on top of what
Gemini naturally observes through the video stream.

For advanced local body language analysis, this processor can be extended with:
- MediaPipe face mesh for eye/gaze tracking
- MediaPipe pose for posture analysis
- Custom emotion detection models
"""

import logging
import time
from typing import TYPE_CHECKING, Dict, List, Optional

from events.coach_events import BodyLanguageEvent
from vision_agents.core.llm.events import (
    RealtimeAgentSpeechTranscriptionEvent,
    RealtimeResponseEvent,
)
from vision_agents.core.processors.base_processor import Processor

if TYPE_CHECKING:
    from vision_agents.core import Agent

logger = logging.getLogger(__name__)

# How often to prompt Gemini for a body language check (seconds)
BODY_LANGUAGE_CHECK_INTERVAL = 45.0


class VideoAnalyzerProcessor(Processor):
    """Tracks body language observations from the video stream.

    Works with Gemini Realtime which natively analyzes video. This processor
    adds structured event emission and observation tracking on top of Gemini's
    built-in video understanding.
    """

    def __init__(
        self,
        check_interval_seconds: float = BODY_LANGUAGE_CHECK_INTERVAL,
    ):
        self._agent: Optional["Agent"] = None
        self._check_interval = check_interval_seconds
        self._last_check_time: float = 0.0
        self._session_start: float = 0.0

        # Body language observation history
        self._observations: List[Dict] = []

        # Running counts by category
        self._category_counts: Dict[str, Dict[str, int]] = {
            "eye_contact": {"good": 0, "needs_improvement": 0, "neutral": 0},
            "posture": {"good": 0, "needs_improvement": 0, "neutral": 0},
            "expression": {"good": 0, "needs_improvement": 0, "neutral": 0},
            "gesture": {"good": 0, "needs_improvement": 0, "neutral": 0},
        }

    @property
    def name(self) -> str:
        return "video_analyzer"

    def attach_agent(self, agent: "Agent") -> None:
        """Register events and set up periodic body language checking."""
        self._agent = agent
        self._session_start = time.time()
        self._last_check_time = self._session_start

        # Register our event
        agent.events.register(BodyLanguageEvent)

        # Register a function that Gemini can call to report body language observations
        if hasattr(agent.llm, "register_function"):
            @agent.llm.register_function(
                description=(
                    "Report a body language observation about the user. Call this when you "
                    "notice something about the user's body language from the video — such as "
                    "eye contact, posture, facial expression, or hand gestures. Use this to "
                    "track observations over the session."
                )
            )
            async def report_body_language(
                category: str,
                observation: str,
                quality: str,
            ) -> Dict[str, str]:
                """Report a body language observation.

                Args:
                    category: One of 'eye_contact', 'posture', 'expression', 'gesture'.
                    observation: Human-readable description of what was observed.
                    quality: One of 'good', 'needs_improvement', 'neutral'.
                """
                await self._record_observation(category, observation, quality)
                return {
                    "status": "recorded",
                    "total_observations": str(len(self._observations)),
                }

        logger.info("VideoAnalyzerProcessor attached — monitoring body language via Gemini")

    async def _record_observation(
        self, category: str, observation: str, quality: str
    ) -> None:
        """Record a body language observation and emit an event."""
        if not self._agent:
            return

        # Normalize inputs
        category = category.lower().strip()
        quality = quality.lower().strip()

        if category not in self._category_counts:
            category = "gesture"  # Default fallback
        if quality not in ("good", "needs_improvement", "neutral"):
            quality = "neutral"

        # Record
        entry = {
            "category": category,
            "observation": observation,
            "quality": quality,
            "timestamp": time.time() - self._session_start,
        }
        self._observations.append(entry)

        # Update counts
        self._category_counts[category][quality] += 1

        # Emit event
        self._agent.events.send(
            BodyLanguageEvent(
                observation=observation,
                category=category,
                quality=quality,
            )
        )

        logger.info(f"Body language [{category}]: {observation} ({quality})")

    def get_observations(self) -> List[Dict]:
        """Return all recorded body language observations."""
        return self._observations.copy()

    def get_summary(self) -> Dict:
        """Return a summary of body language observations by category."""
        return {
            "total_observations": len(self._observations),
            "by_category": dict(self._category_counts),
            "observations": self._observations,
        }

    async def close(self) -> None:
        """Clean up resources."""
        total = len(self._observations)
        logger.info(f"VideoAnalyzer closing — recorded {total} body language observations")
