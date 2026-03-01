"""
SpeechAnalyzerProcessor — Real-time analysis of user speech patterns.

Subscribes to RealtimeUserSpeechTranscriptionEvent and analyzes:
- Filler word frequency (um, uh, like, you know, etc.)
- Speaking pace (words per minute)
- Hedging language detection
- Vocabulary diversity (type-token ratio)
- Composite confidence score

Emits coach events that can be used by the LLM for real-time coaching,
and by the SessionRecorder for post-session reports.
"""

import logging
import re
import time
from collections import deque
from typing import TYPE_CHECKING, Dict, List, Optional

from events.coach_events import (
    ConfidenceScoreEvent,
    FillerWordDetectedEvent,
    HedgingLanguageEvent,
    PaceAnalysisEvent,
)
from vision_agents.core.llm.events import RealtimeUserSpeechTranscriptionEvent
from vision_agents.core.processors.base_processor import Processor

if TYPE_CHECKING:
    from vision_agents.core import Agent

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Filler words to detect (case-insensitive)
FILLER_WORDS = {
    "um", "uh", "uhm", "umm", "hmm",
    "like",  # when used as filler, not comparison
    "you know",
    "sort of",
    "kind of",
    "basically",
    "literally",
    "actually",
    "right",
    "so",  # when used as filler at the start
    "well",  # when used as filler at the start
    "i mean",
}

# Multi-word fillers need regex patterns
FILLER_PATTERNS = [
    re.compile(r"\byou know\b", re.IGNORECASE),
    re.compile(r"\bsort of\b", re.IGNORECASE),
    re.compile(r"\bkind of\b", re.IGNORECASE),
    re.compile(r"\bi mean\b", re.IGNORECASE),
]

# Single-word fillers
SINGLE_FILLER_WORDS = {"um", "uh", "uhm", "umm", "hmm", "like", "basically", "literally", "actually"}

# Hedging phrases
HEDGING_PATTERNS = [
    re.compile(r"\bi think maybe\b", re.IGNORECASE),
    re.compile(r"\bi guess\b", re.IGNORECASE),
    re.compile(r"\bi suppose\b", re.IGNORECASE),
    re.compile(r"\bprobably\b", re.IGNORECASE),
    re.compile(r"\bmaybe\b", re.IGNORECASE),
    re.compile(r"\bi'm not sure but\b", re.IGNORECASE),
    re.compile(r"\bi don't know if\b", re.IGNORECASE),
    re.compile(r"\bit might be\b", re.IGNORECASE),
    re.compile(r"\bcould be\b", re.IGNORECASE),
    re.compile(r"\bpossibly\b", re.IGNORECASE),
]

# Pace thresholds (words per minute)
PACE_TOO_SLOW = 100
PACE_GOOD_MIN = 120
PACE_GOOD_MAX = 160
PACE_TOO_FAST = 180

# Filler word threshold for coaching nudge
FILLER_THRESHOLD_PER_WINDOW = 3
FILLER_WINDOW_SECONDS = 60.0

# How often to emit pace/confidence events (seconds)
ANALYSIS_INTERVAL_SECONDS = 30.0


class TranscriptEntry:
    """A single transcript entry with metadata."""

    def __init__(self, text: str, timestamp: float):
        self.text = text
        self.timestamp = timestamp
        self.word_count = len(text.split())


class SpeechAnalyzerProcessor(Processor):
    """Analyzes real-time user speech for communication coaching."""

    def __init__(
        self,
        filler_threshold: int = FILLER_THRESHOLD_PER_WINDOW,
        filler_window_seconds: float = FILLER_WINDOW_SECONDS,
        analysis_interval_seconds: float = ANALYSIS_INTERVAL_SECONDS,
    ):
        self._agent: Optional["Agent"] = None
        self._filler_threshold = filler_threshold
        self._filler_window_seconds = filler_window_seconds
        self._analysis_interval_seconds = analysis_interval_seconds

        # Transcript buffer (sliding window for analysis)
        self._transcript_entries: deque[TranscriptEntry] = deque()

        # Filler word tracking
        self._filler_events: deque[Dict] = deque()  # {word, timestamp}
        self._total_fillers: int = 0
        self._filler_counts: Dict[str, int] = {}  # word -> count

        # Hedging tracking
        self._total_hedging: int = 0

        # Pace tracking
        self._last_analysis_time: float = 0.0

        # Session start time
        self._session_start: float = 0.0

        # All words for vocabulary diversity
        self._all_words: List[str] = []

    @property
    def name(self) -> str:
        return "speech_analyzer"

    def attach_agent(self, agent: "Agent") -> None:
        """Register custom events and subscribe to transcription events."""
        self._agent = agent
        self._session_start = time.time()
        self._last_analysis_time = self._session_start

        # Register our custom events
        agent.events.register(
            FillerWordDetectedEvent,
            PaceAnalysisEvent,
            HedgingLanguageEvent,
            ConfidenceScoreEvent,
        )

        # Subscribe to user speech transcription
        @agent.events.subscribe
        async def on_user_transcription(event: RealtimeUserSpeechTranscriptionEvent):
            await self._analyze_transcription(event.text, event.timestamp)

        logger.info("SpeechAnalyzerProcessor attached — listening for transcription events")

    async def _analyze_transcription(self, text: str, timestamp) -> None:
        """Analyze a piece of transcribed user speech."""
        if not text or not text.strip():
            return

        now = time.time()

        # Store transcript entry
        entry = TranscriptEntry(text=text.strip(), timestamp=now)
        self._transcript_entries.append(entry)

        # Store words for vocabulary analysis
        words = text.lower().split()
        self._all_words.extend(words)

        # --- Filler word detection ---
        fillers_found = self._detect_fillers(text, now)
        if fillers_found:
            await self._emit_filler_events(fillers_found, now)

        # --- Hedging language detection ---
        hedging_found = self._detect_hedging(text)
        if hedging_found:
            await self._emit_hedging_events(hedging_found)

        # --- Periodic analysis (pace + confidence) ---
        if now - self._last_analysis_time >= self._analysis_interval_seconds:
            await self._emit_pace_analysis(now)
            await self._emit_confidence_score(now)
            self._last_analysis_time = now

    def _detect_fillers(self, text: str, now: float) -> List[str]:
        """Detect filler words in text. Returns list of fillers found."""
        found = []

        # Check multi-word fillers first
        for pattern in FILLER_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                found.append(match.lower())

        # Check single-word fillers
        words = text.lower().split()
        for word in words:
            # Strip punctuation for matching
            clean = re.sub(r"[^\w]", "", word)
            if clean in SINGLE_FILLER_WORDS:
                found.append(clean)

        # Update tracking
        for filler in found:
            self._filler_events.append({"word": filler, "timestamp": now})
            self._total_fillers += 1
            self._filler_counts[filler] = self._filler_counts.get(filler, 0) + 1

        # Prune old filler events outside the window
        cutoff = now - self._filler_window_seconds
        while self._filler_events and self._filler_events[0]["timestamp"] < cutoff:
            self._filler_events.popleft()

        return found

    def _detect_hedging(self, text: str) -> List[str]:
        """Detect hedging language in text."""
        found = []
        for pattern in HEDGING_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                found.append(match.lower())
                self._total_hedging += 1
        return found

    async def _emit_filler_events(self, fillers: List[str], now: float) -> None:
        """Emit filler word events if threshold is crossed."""
        fillers_in_window = len(self._filler_events)

        # Only emit if we've exceeded the threshold
        if fillers_in_window >= self._filler_threshold and self._agent:
            # Emit for the most frequent filler in this batch
            most_common = max(set(fillers), key=fillers.count)
            self._agent.events.send(
                FillerWordDetectedEvent(
                    word=most_common,
                    count_in_window=fillers_in_window,
                    total_in_session=self._total_fillers,
                    window_seconds=self._filler_window_seconds,
                )
            )
            logger.info(
                f"Filler words detected: {fillers_in_window} in last "
                f"{self._filler_window_seconds}s (total: {self._total_fillers})"
            )

    async def _emit_hedging_events(self, phrases: List[str]) -> None:
        """Emit hedging language events."""
        if self._agent:
            for phrase in phrases:
                self._agent.events.send(
                    HedgingLanguageEvent(
                        phrase=phrase,
                        count_in_session=self._total_hedging,
                    )
                )

    async def _emit_pace_analysis(self, now: float) -> None:
        """Calculate and emit speaking pace analysis."""
        if not self._agent:
            return

        # Calculate WPM over the analysis window
        cutoff = now - self._analysis_interval_seconds
        words_in_window = sum(
            entry.word_count
            for entry in self._transcript_entries
            if entry.timestamp >= cutoff
        )

        # Convert to words per minute
        window_minutes = self._analysis_interval_seconds / 60.0
        wpm = words_in_window / window_minutes if window_minutes > 0 else 0

        # Determine recommendation
        if wpm < PACE_TOO_SLOW:
            recommendation = "too_slow"
        elif wpm > PACE_TOO_FAST:
            recommendation = "too_fast"
        else:
            recommendation = "good"

        self._agent.events.send(
            PaceAnalysisEvent(
                words_per_minute=round(wpm, 1),
                recommendation=recommendation,
                window_seconds=self._analysis_interval_seconds,
            )
        )
        logger.info(f"Pace analysis: {wpm:.1f} WPM ({recommendation})")

    async def _emit_confidence_score(self, now: float) -> None:
        """Calculate and emit composite confidence score."""
        if not self._agent:
            return

        session_duration = now - self._session_start
        if session_duration < 10:  # Don't score the first 10 seconds
            return

        # --- Factor: Filler words (0-100, 100 = few fillers) ---
        filler_rate = self._total_fillers / (session_duration / 60.0) if session_duration > 0 else 0
        # Ideal: < 2 per minute, Bad: > 8 per minute
        filler_score = max(0, min(100, 100 - (filler_rate - 2) * 12.5))

        # --- Factor: Pace (0-100, 100 = good pace) ---
        # Use recent pace data
        cutoff = now - self._analysis_interval_seconds
        words_in_window = sum(
            entry.word_count
            for entry in self._transcript_entries
            if entry.timestamp >= cutoff
        )
        window_minutes = self._analysis_interval_seconds / 60.0
        wpm = words_in_window / window_minutes if window_minutes > 0 else 0

        if PACE_GOOD_MIN <= wpm <= PACE_GOOD_MAX:
            pace_score = 100
        elif wpm < PACE_GOOD_MIN:
            pace_score = max(0, 100 - (PACE_GOOD_MIN - wpm) * 2)
        else:
            pace_score = max(0, 100 - (wpm - PACE_GOOD_MAX) * 2)

        # --- Factor: Hedging (0-100, 100 = little hedging) ---
        hedging_rate = self._total_hedging / (session_duration / 60.0) if session_duration > 0 else 0
        hedging_score = max(0, min(100, 100 - (hedging_rate - 1) * 15))

        # --- Factor: Vocabulary diversity (0-100) ---
        if len(self._all_words) > 20:
            unique_words = len(set(self._all_words))
            ttr = unique_words / len(self._all_words)
            vocab_score = min(100, ttr * 200)  # TTR of 0.5 = 100
        else:
            vocab_score = 50  # Not enough data yet

        # --- Composite score ---
        composite = (
            filler_score * 0.30 +
            pace_score * 0.25 +
            hedging_score * 0.20 +
            vocab_score * 0.25
        )

        self._agent.events.send(
            ConfidenceScoreEvent(
                score=round(composite, 1),
                factors={
                    "filler_words": round(filler_score, 1),
                    "pace": round(pace_score, 1),
                    "hedging": round(hedging_score, 1),
                    "vocabulary": round(vocab_score, 1),
                },
            )
        )
        logger.info(f"Confidence score: {composite:.1f}/100")

    # --- Public accessors for other processors (e.g., SessionRecorder) ---

    def get_session_metrics(self) -> Dict:
        """Return aggregated session metrics for post-session analysis."""
        now = time.time()
        duration = now - self._session_start if self._session_start else 0

        return {
            "duration_seconds": round(duration, 1),
            "total_filler_words": self._total_fillers,
            "filler_breakdown": dict(self._filler_counts),
            "total_hedging_phrases": self._total_hedging,
            "total_words_spoken": len(self._all_words),
            "unique_words": len(set(self._all_words)) if self._all_words else 0,
            "vocabulary_diversity": (
                round(len(set(self._all_words)) / len(self._all_words), 3)
                if self._all_words
                else 0
            ),
        }

    def get_transcript_entries(self) -> List[Dict]:
        """Return all transcript entries as dicts."""
        return [
            {"text": e.text, "timestamp": e.timestamp, "word_count": e.word_count}
            for e in self._transcript_entries
        ]

    async def close(self) -> None:
        """Clean up resources."""
        logger.info(
            f"SpeechAnalyzer closing — session metrics: {self.get_session_metrics()}"
        )
