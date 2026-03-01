"""
SessionRecorderProcessor — Records all events for post-session analysis.

Captures transcription events, speech analysis events, and body language events
throughout the session. When the session ends, it compiles a complete session
record that can be used to generate reports and track progress.
"""

import json
import logging
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from events.coach_events import (
    BodyLanguageEvent,
    ConfidenceScoreEvent,
    FillerWordDetectedEvent,
    HedgingLanguageEvent,
    PaceAnalysisEvent,
    SessionSummaryEvent,
)
from vision_agents.core.agents.events import AgentFinishEvent
from vision_agents.core.llm.events import (
    RealtimeAgentSpeechTranscriptionEvent,
    RealtimeUserSpeechTranscriptionEvent,
)
from vision_agents.core.processors.base_processor import Processor

if TYPE_CHECKING:
    from vision_agents.core import Agent

logger = logging.getLogger(__name__)


class SessionRecorderProcessor(Processor):
    """Records all session events for post-session report generation."""

    def __init__(self):
        self._agent: Optional["Agent"] = None
        self._session_start: float = 0.0

        # Transcript
        self._transcript: List[Dict[str, Any]] = []

        # Speech analysis events
        self._filler_events: List[Dict[str, Any]] = []
        self._pace_events: List[Dict[str, Any]] = []
        self._hedging_events: List[Dict[str, Any]] = []
        self._confidence_events: List[Dict[str, Any]] = []

        # Body language events
        self._body_language_events: List[Dict[str, Any]] = []

        # Latest confidence score
        self._latest_confidence: Optional[Dict[str, Any]] = None

    @property
    def name(self) -> str:
        return "session_recorder"

    def attach_agent(self, agent: "Agent") -> None:
        """Register events and subscribe to all relevant event types."""
        self._agent = agent
        self._session_start = time.time()

        # Register session summary event
        agent.events.register(SessionSummaryEvent)

        # --- Subscribe to transcription events ---
        @agent.events.subscribe
        async def on_user_speech(event: RealtimeUserSpeechTranscriptionEvent):
            if event.text and event.text.strip():
                self._transcript.append({
                    "speaker": "user",
                    "text": event.text.strip(),
                    "timestamp": time.time() - self._session_start,
                })

        @agent.events.subscribe
        async def on_agent_speech(event: RealtimeAgentSpeechTranscriptionEvent):
            if event.text and event.text.strip():
                self._transcript.append({
                    "speaker": "agent",
                    "text": event.text.strip(),
                    "timestamp": time.time() - self._session_start,
                })

        # --- Subscribe to analysis events ---
        @agent.events.subscribe
        async def on_filler(event: FillerWordDetectedEvent):
            self._filler_events.append({
                "word": event.word,
                "count_in_window": event.count_in_window,
                "total_in_session": event.total_in_session,
                "timestamp": time.time() - self._session_start,
            })

        @agent.events.subscribe
        async def on_pace(event: PaceAnalysisEvent):
            self._pace_events.append({
                "wpm": event.words_per_minute,
                "recommendation": event.recommendation,
                "timestamp": time.time() - self._session_start,
            })

        @agent.events.subscribe
        async def on_hedging(event: HedgingLanguageEvent):
            self._hedging_events.append({
                "phrase": event.phrase,
                "count_in_session": event.count_in_session,
                "timestamp": time.time() - self._session_start,
            })

        @agent.events.subscribe
        async def on_confidence(event: ConfidenceScoreEvent):
            entry = {
                "score": event.score,
                "factors": event.factors,
                "timestamp": time.time() - self._session_start,
            }
            self._confidence_events.append(entry)
            self._latest_confidence = entry

        @agent.events.subscribe
        async def on_body_language(event: BodyLanguageEvent):
            self._body_language_events.append({
                "observation": event.observation,
                "category": event.category,
                "quality": event.quality,
                "timestamp": time.time() - self._session_start,
            })

        # --- Subscribe to session end ---
        @agent.events.subscribe
        async def on_finish(event: AgentFinishEvent):
            await self._generate_session_summary()

        logger.info("SessionRecorderProcessor attached — recording all events")

    async def _generate_session_summary(self) -> None:
        """Generate and emit a session summary when the session ends."""
        if not self._agent:
            return

        duration = time.time() - self._session_start

        # Get speech analyzer metrics if available
        speech_analyzer_metrics = {}
        for processor in self._agent.processors:
            if processor.name == "speech_analyzer":
                speech_analyzer_metrics = processor.get_session_metrics()
                break

        # Compile metrics
        metrics = {
            **speech_analyzer_metrics,
            "pace_readings": self._pace_events,
            "confidence_readings": self._confidence_events,
            "body_language_observations": self._body_language_events,
            "transcript_length": len(self._transcript),
        }

        # Determine strengths and improvements from data
        strengths, improvements = self._analyze_strengths_and_improvements(metrics)

        # Generate exercise recommendations
        exercises = self._recommend_exercises(improvements)

        # Calculate overall score
        overall_score = (
            self._latest_confidence["score"] if self._latest_confidence else 50.0
        )

        # Emit summary event
        summary = SessionSummaryEvent(
            duration_seconds=round(duration, 1),
            transcript=self._transcript,
            metrics=metrics,
            overall_score=round(overall_score, 1),
            strengths=strengths,
            improvements=improvements,
            exercises=exercises,
        )
        self._agent.events.send(summary)

        # Log summary
        logger.info("=" * 60)
        logger.info("  SESSION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"  Duration: {duration:.0f}s")
        logger.info(f"  Overall score: {overall_score:.1f}/100")
        logger.info(f"  Strengths: {strengths}")
        logger.info(f"  Improvements: {improvements}")
        logger.info(f"  Exercises: {[e['type'] for e in exercises]}")
        logger.info("=" * 60)

    def _analyze_strengths_and_improvements(self, metrics: Dict) -> tuple:
        """Analyze session data to identify strengths and areas for improvement."""
        strengths = []
        improvements = []

        # --- Filler words ---
        total_fillers = metrics.get("total_filler_words", 0)
        duration_min = metrics.get("duration_seconds", 0) / 60.0
        if duration_min > 0:
            filler_rate = total_fillers / duration_min
            if filler_rate < 2:
                strengths.append("Minimal filler words — clear and confident speech")
            elif filler_rate > 5:
                improvements.append(
                    f"Reduce filler words (averaging {filler_rate:.1f}/min). "
                    "Try pausing silently instead of using 'um' or 'like'."
                )

        # --- Pace ---
        if self._pace_events:
            avg_wpm = sum(e["wpm"] for e in self._pace_events) / len(self._pace_events)
            if 120 <= avg_wpm <= 160:
                strengths.append(f"Great speaking pace ({avg_wpm:.0f} WPM)")
            elif avg_wpm > 180:
                improvements.append(
                    f"Speaking too fast ({avg_wpm:.0f} WPM). "
                    "Slow down and pause between key points."
                )
            elif avg_wpm < 100:
                improvements.append(
                    f"Speaking pace is slow ({avg_wpm:.0f} WPM). "
                    "Try to maintain more energy and momentum."
                )

        # --- Hedging ---
        total_hedging = metrics.get("total_hedging_phrases", 0)
        if duration_min > 0:
            hedging_rate = total_hedging / duration_min
            if hedging_rate < 1:
                strengths.append("Speaks with conviction — minimal hedging language")
            elif hedging_rate > 3:
                improvements.append(
                    "Reduce hedging language ('I think maybe', 'I guess'). "
                    "State your opinions directly."
                )

        # --- Vocabulary ---
        diversity = metrics.get("vocabulary_diversity", 0)
        if diversity > 0.5:
            strengths.append("Rich and varied vocabulary")
        elif diversity < 0.3 and metrics.get("total_words_spoken", 0) > 50:
            improvements.append(
                "Try using more varied vocabulary to keep conversations engaging."
            )

        # --- Body language ---
        if self._body_language_events:
            good_bl = [e for e in self._body_language_events if e["quality"] == "good"]
            bad_bl = [e for e in self._body_language_events if e["quality"] == "needs_improvement"]
            if len(good_bl) > len(bad_bl):
                strengths.append("Strong body language and presence")
            elif bad_bl:
                categories = set(e["category"] for e in bad_bl)
                if "eye_contact" in categories:
                    improvements.append("Maintain more eye contact with the camera")
                if "posture" in categories:
                    improvements.append("Improve posture — sit up straight and relax shoulders")

        # Default messages
        if not strengths:
            strengths.append("Engaged in conversation and willing to practice")
        if not improvements:
            improvements.append("Keep practicing to build even more confidence")

        return strengths[:3], improvements[:3]

    def _recommend_exercises(self, improvements: List[str]) -> List[Dict[str, str]]:
        """Generate exercise recommendations based on identified improvement areas."""
        exercises = []

        for improvement in improvements:
            imp_lower = improvement.lower()
            if "filler" in imp_lower:
                exercises.append({
                    "type": "filler_elimination",
                    "prompt": (
                        "Describe your morning routine in exactly 60 seconds. "
                        "Challenge: zero filler words. Pause silently instead."
                    ),
                    "time_limit": "60",
                })
            elif "fast" in imp_lower or "pace" in imp_lower or "slow" in imp_lower:
                exercises.append({
                    "type": "pace_control",
                    "prompt": (
                        "Explain how to make your favorite meal, step by step. "
                        "Focus on speaking at a steady, measured pace. "
                        "Take a breath between each step."
                    ),
                    "time_limit": "90",
                })
            elif "hedging" in imp_lower or "conviction" in imp_lower:
                exercises.append({
                    "type": "confidence_building",
                    "prompt": (
                        "State three opinions you hold strongly. For each one, "
                        "start with 'I believe...' and give one reason why. "
                        "No hedging — own your opinions."
                    ),
                    "time_limit": "90",
                })
            elif "vocabulary" in imp_lower:
                exercises.append({
                    "type": "vocabulary_expansion",
                    "prompt": (
                        "Describe your favorite place without using these common words: "
                        "nice, good, great, really, very. Find more specific, vivid words."
                    ),
                    "time_limit": "60",
                })
            elif "eye contact" in imp_lower:
                exercises.append({
                    "type": "eye_contact",
                    "prompt": (
                        "Tell a 2-minute story about something that happened to you recently. "
                        "Keep your eyes on the camera the entire time."
                    ),
                    "time_limit": "120",
                })
            elif "posture" in imp_lower:
                exercises.append({
                    "type": "posture_awareness",
                    "prompt": (
                        "Sit up straight, relax your shoulders, and take three deep breaths. "
                        "Now pitch an idea for 60 seconds while maintaining that posture."
                    ),
                    "time_limit": "60",
                })

        # Always include a general exercise
        if not exercises:
            exercises.append({
                "type": "general_practice",
                "prompt": (
                    "Pick any topic and explain it to me as if I'm hearing about it "
                    "for the first time. Keep it under 90 seconds."
                ),
                "time_limit": "90",
            })

        return exercises[:3]

    def get_session_data(self) -> Dict[str, Any]:
        """Return complete session data for external use (e.g., dashboard)."""
        return {
            "session_start": self._session_start,
            "duration_seconds": time.time() - self._session_start,
            "transcript": self._transcript,
            "filler_events": self._filler_events,
            "pace_events": self._pace_events,
            "hedging_events": self._hedging_events,
            "confidence_events": self._confidence_events,
            "body_language_events": self._body_language_events,
            "latest_confidence": self._latest_confidence,
        }

    async def close(self) -> None:
        """Clean up resources."""
        session_data = self.get_session_data()
        logger.info(
            f"SessionRecorder closing — recorded {len(self._transcript)} "
            f"transcript entries over {session_data['duration_seconds']:.0f}s"
        )
