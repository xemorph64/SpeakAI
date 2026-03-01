"""
AI Communication Coach

A real-time AI agent that helps users improve their everyday communication
skills through natural conversation with live coaching feedback.

Features:
  - Real-time speech analysis (filler words, pace, hedging, vocabulary)
  - Video body language tracking (eye contact, posture, expression, gestures)
  - Session recording with full transcript
  - Post-session reports with scores, strengths, & improvement areas
  - Exercise recommendations based on identified weaknesses
  - SQLite-persisted progress tracking with gamification

Run the agent:
    cd examples/09_communication_coach
    uv run python main.py run --call-type default --call-id test

Run the dashboard (separate terminal):
    cd examples/09_communication_coach
    uv run python -m dashboard.app
    # Then open http://localhost:8080
"""

import logging
import os
import time

from dotenv import load_dotenv
from events.coach_events import SessionSummaryEvent
from google.genai.types import (
    AudioTranscriptionConfigDict,
    LiveConnectConfigDict,
    Modality,
    RealtimeInputConfigDict,
    TurnCoverage,
)
from memory.memory_manager import MemoryManager
from post_session.report_generator import ReportGenerator
from processors.session_recorder import SessionRecorderProcessor
from processors.speech_analyzer import SpeechAnalyzerProcessor
from processors.video_analyzer import VideoAnalyzerProcessor
from vision_agents.core import Agent, Runner, User
from vision_agents.core.agents import AgentLauncher
from vision_agents.core.agents.conversation import InMemoryConversation
from vision_agents.plugins import gemini, getstream

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

load_dotenv()

if not os.getenv("API_KEY") and os.getenv("STREAM_API_KEY"):
    os.environ["API_KEY"] = os.environ["STREAM_API_KEY"]

if not os.getenv("API_SECRET") and os.getenv("STREAM_API_SECRET"):
    os.environ["API_SECRET"] = os.environ["STREAM_API_SECRET"]

# Shared report generator instance
report_generator = ReportGenerator()
memory_manager = MemoryManager()


async def create_agent(**kwargs) -> Agent:
    """Create the Communication Coach agent."""

    realtime_model = os.getenv(
        "GEMINI_REALTIME_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025"
    )
    realtime_config = LiveConnectConfigDict(
        response_modalities=[Modality.AUDIO],
        input_audio_transcription=AudioTranscriptionConfigDict(),
        realtime_input_config=RealtimeInputConfigDict(
            turn_coverage=TurnCoverage.TURN_INCLUDES_ONLY_ACTIVITY
        ),
    )

    agent = Agent(
        edge=getstream.Edge(),
        agent_user=User(name="Communication Coach", id="comm-coach"),
        instructions="Read @communication_coach.md",
        llm=gemini.Realtime(
            model=realtime_model,
            config=realtime_config,
            fps=1,
        ),
        processors=[
            SpeechAnalyzerProcessor(),      # Real-time speech pattern analysis
            VideoAnalyzerProcessor(),       # Body language tracking via Gemini
            SessionRecorderProcessor(),     # Records everything for post-session reports
        ],
    )

    if hasattr(agent.llm, "register_function"):

        @agent.llm.register_function(
            description=(
                "Retrieve relevant long-term session memories from local storage. "
                "Use when user references past sessions, recurring goals, previous feedback, "
                "or when context is unclear and historical coaching details can help."
            )
        )
        async def get_relevant_memories(query: str, limit: int = 5) -> dict:
            memories = memory_manager.search_memories(query=query, limit=limit)
            return {
                "query": query,
                "count": len(memories),
                "memories": memories,
            }

        @agent.llm.register_function(
            description=(
                "Get the user's current communication profile summary based on previous sessions."
            )
        )
        async def get_user_profile_summary() -> dict:
            return {"profile_summary": memory_manager.get_profile_summary()}

    # Subscribe to session summary to generate report
    @agent.events.subscribe
    async def on_session_summary(event: SessionSummaryEvent):
        """Generate and log the post-session report when a session ends."""
        summary_data = {
            "duration_seconds": event.duration_seconds,
            "overall_score": event.overall_score,
            "metrics": event.metrics,
            "strengths": event.strengths,
            "improvements": event.improvements,
            "exercises": event.exercises,
            "transcript": event.transcript,
        }
        report = report_generator.save_and_report(summary_data)
        memory_manager.save_session_summary(
            summary_data,
            session_id=f"session-{int(time.time())}",
        )
        logger.info("\n" + report)

    return agent


async def join_call(agent: Agent, call_type: str, call_id: str, **kwargs) -> None:
    """Join a call and start the coaching session."""

    call = await agent.create_call(call_type, call_id)

    logger.info("=" * 60)
    logger.info("  AI Communication Coach")
    logger.info("=" * 60)
    logger.info(f"  Call type: {call_type}")
    logger.info(f"  Call ID:   {call_id}")
    logger.info("=" * 60)

    async with agent.join(call):
        # Use local in-memory conversation for runtime turn memory to avoid
        # remote chat write amplification from realtime chunk events.
        # Long-term memory remains persisted via local SQLite memory manager.
        agent.conversation = InMemoryConversation(
            instructions=agent.instructions.full_reference,
            messages=[],
        )
        agent.llm.set_conversation(agent.conversation)

        # Kick off the session — the coach greets the user
        await agent.llm.simple_response(
            text=(
                "Greet the user warmly. Introduce yourself as their communication coach. "
                "Ask what they'd like to practice today, and offer to suggest a topic if "
                "they're not sure. Keep it short and friendly."
            )
        )

        # Run until the call ends
        await agent.finish()


if __name__ == "__main__":
    Runner(AgentLauncher(create_agent=create_agent, join_call=join_call)).cli()
