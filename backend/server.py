"""
SpeakAI — FastAPI Backend Server

================================================================================
Architecture:
  • Per-WebSocket session backed by a Communication Coach agent
  • Agent uses Gemini Realtime for native audio + video understanding
  • Processors emit structured coaching events (filler words, pace, hedging,
    confidence, body language) which are forwarded to the frontend as
    'coach_metrics' WebSocket messages
  • Agent joins a Stream Video call as a real participant via getstream.Edge()
  • SQLite-backed progress tracking and long-term memory
  • Optionally includes a demo mode with simulated coaching metrics
================================================================================

Endpoints:
  WS  /ws/metrics           — real-time coaching session stream
  GET /health               — server health
  GET /token                — Stream Video JWT token
  GET /api/stats            — aggregate session statistics
  GET /api/sessions         — recent session history
  GET /api/trends           — score trend data
  GET /api/exercises        — exercise library

Client → Server messages:
  { type: "start_session", call_id: "..." }  → join a Stream call
  { type: "start_demo" }                     → simulated coaching metrics
  { type: "stop_session" }                   → stop current service
  { type: "send_message", text: "..." }      → send chat to AI agent
  { type: "ping" }                           → keepalive

Server → Client messages:
  { type: "coach_metrics", data: {...} }     → coaching event
  { type: "feedback", data: {...} }          → coaching feedback
  { type: "chat", data: {...} }              → conversation message
  { type: "transcript", data: {...} }        → speech transcript
  { type: "conversation_state", data: {...} }→ who is speaking
  { type: "system_status", payload: {...} }  → debug telemetry
  { type: "session_summary", data: {...} }   → end-of-session summary
  { type: "session_started", data: {...} }   → ack
  { type: "session_stopped", data: {...} }   → ack
  { type: "demo_started", data: {...} }      → ack
  { type: "pong" }                           → keepalive ack
  { type: "error", message: "..." }          → error
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import jwt

from .core.config import server_cfg, sdk_cfg

# ---------------------------------------------------------------------------
# Path setup — agent modules live under backend/agent/
# ---------------------------------------------------------------------------

AGENT_DIR = Path(__file__).parent / "agent"
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
sys.path.insert(0, str(AGENT_DIR))

# Make post_session's SQLite DBs land in backend/data/
os.environ.setdefault("COACH_DATA_DIR", str(DATA_DIR))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("speakai")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)


# ---------------------------------------------------------------------------
# Agent session wrapper
# ---------------------------------------------------------------------------

class AgentSession:
    """
    Wraps a Communication Coach agent instance for a single WebSocket session.
    Subscribes to coach events and forwards them as JSON to the WS client.
    """

    def __init__(
        self,
        session_id: str,
        send_fn: Callable[[Dict[str, Any]], Coroutine],
    ):
        self.session_id = session_id
        self._send = send_fn
        self._agent = None
        self._task: Optional[asyncio.Task] = None
        self.is_active = False
        self._start_time: Optional[float] = None

    async def start(self, call_id: str) -> Dict[str, Any]:
        """Create the agent and join the Stream Video call."""
        from agent.main import create_agent

        self._agent = await create_agent()
        self._start_time = time.time()
        self.is_active = True

        # Subscribe to coach events and forward as WS messages
        self._subscribe_events()

        # Launch the call in a background task
        self._task = asyncio.create_task(self._run_call(call_id))

        return {
            "session_id": self.session_id,
            "call_id": call_id,
            "status": "started",
        }

    def _subscribe_events(self):
        """Subscribe to all coaching events and forward them to the frontend."""
        if not self._agent:
            return

        from events.coach_events import (
            FillerWordDetectedEvent,
            PaceAnalysisEvent,
            ConfidenceScoreEvent,
            HedgingLanguageEvent,
            BodyLanguageEvent,
            SessionSummaryEvent,
        )
        from vision_agents.core.llm.events import (
            RealtimeUserSpeechTranscriptionEvent,
            RealtimeAgentSpeechTranscriptionEvent,
        )

        @self._agent.events.subscribe
        async def on_filler(event: FillerWordDetectedEvent):
            await self._send({
                "type": "coach_metrics",
                "data": {
                    "metric": "filler_words",
                    "word": event.word,
                    "count_in_window": event.count_in_window,
                    "total_in_session": event.total_in_session,
                    "window_seconds": event.window_seconds,
                    "timestamp": time.time(),
                },
            })

        @self._agent.events.subscribe
        async def on_pace(event: PaceAnalysisEvent):
            await self._send({
                "type": "coach_metrics",
                "data": {
                    "metric": "pace",
                    "words_per_minute": event.words_per_minute,
                    "recommendation": event.recommendation,
                    "window_seconds": event.window_seconds,
                    "timestamp": time.time(),
                },
            })

        @self._agent.events.subscribe
        async def on_confidence(event: ConfidenceScoreEvent):
            await self._send({
                "type": "coach_metrics",
                "data": {
                    "metric": "confidence",
                    "score": event.score,
                    "factors": event.factors,
                    "timestamp": time.time(),
                },
            })

        @self._agent.events.subscribe
        async def on_hedging(event: HedgingLanguageEvent):
            await self._send({
                "type": "coach_metrics",
                "data": {
                    "metric": "hedging",
                    "phrase": event.phrase,
                    "count_in_session": event.count_in_session,
                    "timestamp": time.time(),
                },
            })

        @self._agent.events.subscribe
        async def on_body_language(event: BodyLanguageEvent):
            await self._send({
                "type": "coach_metrics",
                "data": {
                    "metric": "body_language",
                    "category": event.category,
                    "observation": event.observation,
                    "quality": event.quality,
                    "timestamp": time.time(),
                },
            })

        @self._agent.events.subscribe
        async def on_session_summary(event: SessionSummaryEvent):
            await self._send({
                "type": "session_summary",
                "data": {
                    "duration_seconds": event.duration_seconds,
                    "overall_score": event.overall_score,
                    "metrics": event.metrics,
                    "strengths": event.strengths,
                    "improvements": event.improvements,
                    "exercises": event.exercises,
                    "transcript": event.transcript,
                },
            })

        @self._agent.events.subscribe
        async def on_user_transcript(event: RealtimeUserSpeechTranscriptionEvent):
            await self._send({
                "type": "transcript",
                "data": {
                    "speaker": "user",
                    "text": event.text,
                    "timestamp": time.time(),
                    "confidence": 1.0,
                    "is_final": True,
                },
            })

        @self._agent.events.subscribe
        async def on_agent_transcript(event: RealtimeAgentSpeechTranscriptionEvent):
            await self._send({
                "type": "transcript",
                "data": {
                    "speaker": "agent",
                    "text": event.text,
                    "timestamp": time.time(),
                    "confidence": 1.0,
                    "is_final": True,
                },
            })

    async def _run_call(self, call_id: str):
        """Agent joins the call and runs until disconnected."""
        try:
            from agent.main import join_call

            await join_call(self._agent, "default", call_id)
        except asyncio.CancelledError:
            logger.info(f"[{self.session_id}] Agent call cancelled")
        except Exception as e:
            logger.error(f"[{self.session_id}] Agent call error: {e}", exc_info=True)
            await self._send({
                "type": "error",
                "message": f"Agent error: {str(e)[:200]}",
            })
        finally:
            self.is_active = False

    async def send_chat(self, text: str):
        """Send a text message to the agent's LLM."""
        if self._agent and self._agent.llm:
            # Echo the user message first
            await self._send({
                "type": "chat",
                "data": {
                    "id": uuid.uuid4().hex[:8],
                    "role": "user",
                    "content": text,
                    "timestamp": time.time(),
                    "source": "text",
                },
            })
            try:
                await self._agent.llm.simple_response(text=text)
            except Exception as e:
                logger.debug(f"[{self.session_id}] Chat error: {e}")

    async def stop(self) -> Dict[str, Any]:
        """Gracefully stop the agent."""
        duration = time.time() - self._start_time if self._start_time else 0
        self.is_active = False

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass

        return {
            "session_id": self.session_id,
            "duration_seconds": round(duration, 1),
            "status": "stopped",
        }

    def get_telemetry(self) -> Dict[str, Any]:
        """Return session telemetry snapshot."""
        elapsed = time.time() - self._start_time if self._start_time else 0
        return {
            "session_id": self.session_id,
            "is_active": self.is_active,
            "elapsed_seconds": round(elapsed, 1),
            "agent_connected": self._agent is not None,
        }


# ---------------------------------------------------------------------------
# Demo service — generates simulated coaching events
# ---------------------------------------------------------------------------

class DemoService:
    """Simulates coaching metrics for UI development without API keys."""

    def __init__(self, session_id: str, send_fn: Callable):
        self.session_id = session_id
        self._send = send_fn
        self.is_active = False
        self._task: Optional[asyncio.Task] = None
        self._start_time: Optional[float] = None

    async def start(self) -> Dict[str, Any]:
        self.is_active = True
        self._start_time = time.time()
        self._task = asyncio.create_task(self._run_demo())
        return {"session_id": self.session_id, "mode": "demo", "status": "started"}

    async def _run_demo(self):
        """Generate simulated coaching metrics at ~2 Hz."""
        tick = 0
        fillers = ["um", "uh", "like", "you know", "basically"]
        hedging = ["I think maybe", "probably", "I guess", "sort of"]
        body_obs = [
            ("eye_contact", "Good eye contact maintained", "good"),
            ("posture", "Slight forward lean", "neutral"),
            ("expression", "Confident smile", "good"),
            ("gesture", "Open hand gestures", "good"),
            ("posture", "Slouching detected", "needs_improvement"),
            ("eye_contact", "Looking away from camera", "needs_improvement"),
        ]

        try:
            while self.is_active:
                t = time.time()
                elapsed = t - (self._start_time or t)

                # Confidence score every 5s
                if tick % 10 == 0:
                    score = 65 + 20 * math.sin(elapsed / 30)
                    await self._send({
                        "type": "coach_metrics",
                        "data": {
                            "metric": "confidence",
                            "score": round(score, 1),
                            "factors": {
                                "filler_words": round(70 + 15 * math.sin(elapsed / 20), 1),
                                "pace": round(80 + 10 * math.cos(elapsed / 25), 1),
                                "hedging": round(75 + 10 * math.sin(elapsed / 15), 1),
                                "vocabulary": round(65 + 15 * math.cos(elapsed / 35), 1),
                            },
                            "timestamp": t,
                        },
                    })

                # Pace every 3s
                if tick % 6 == 1:
                    wpm = 135 + 30 * math.sin(elapsed / 20)
                    rec = "good" if 120 <= wpm <= 160 else ("too_fast" if wpm > 160 else "too_slow")
                    await self._send({
                        "type": "coach_metrics",
                        "data": {
                            "metric": "pace",
                            "words_per_minute": round(wpm, 1),
                            "recommendation": rec,
                            "window_seconds": 30.0,
                            "timestamp": t,
                        },
                    })

                # Filler word event every 8s
                if tick % 16 == 3:
                    filler = fillers[tick // 16 % len(fillers)]
                    count = 2 + int(3 * abs(math.sin(elapsed / 40)))
                    await self._send({
                        "type": "coach_metrics",
                        "data": {
                            "metric": "filler_words",
                            "word": filler,
                            "count_in_window": count,
                            "total_in_session": tick // 4,
                            "window_seconds": 60.0,
                            "timestamp": t,
                        },
                    })

                # Hedging every 12s
                if tick % 24 == 7:
                    phrase = hedging[tick // 24 % len(hedging)]
                    await self._send({
                        "type": "coach_metrics",
                        "data": {
                            "metric": "hedging",
                            "phrase": phrase,
                            "count_in_session": tick // 12,
                            "timestamp": t,
                        },
                    })

                # Body language every 15s
                if tick % 30 == 10:
                    cat, obs, qual = body_obs[tick // 30 % len(body_obs)]
                    await self._send({
                        "type": "coach_metrics",
                        "data": {
                            "metric": "body_language",
                            "category": cat,
                            "observation": obs,
                            "quality": qual,
                            "timestamp": t,
                        },
                    })

                # System status every 5s
                if tick % 10 == 5:
                    await self._send({
                        "type": "system_status",
                        "payload": {
                            "agent_joined": True,
                            "session_state": "active",
                            "session_mode": "multimodal",
                            "elapsed_seconds": round(elapsed, 1),
                            "source": "demo",
                        },
                    })

                tick += 1
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass

    async def stop(self) -> Dict[str, Any]:
        self.is_active = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        duration = time.time() - self._start_time if self._start_time else 0
        return {
            "session_id": self.session_id,
            "duration_seconds": round(duration, 1),
            "mode": "demo",
            "status": "stopped",
        }

    def get_telemetry(self) -> Dict[str, Any]:
        elapsed = time.time() - self._start_time if self._start_time else 0
        return {
            "session_id": self.session_id,
            "is_active": self.is_active,
            "elapsed_seconds": round(elapsed, 1),
            "mode": "demo",
        }


# ---------------------------------------------------------------------------
# Session Registry
# ---------------------------------------------------------------------------

_sessions: Dict[str, AgentSession] = {}
_demo_services: Dict[str, DemoService] = {}


# ---------------------------------------------------------------------------
# Post-Session Data (ProgressTracker + ExerciseLibrary)
# ---------------------------------------------------------------------------

def _get_tracker():
    from post_session.progress_tracker import ProgressTracker
    return ProgressTracker()

def _get_exercises():
    from post_session.exercise_library import ExerciseLibrary
    return ExerciseLibrary()


# ---------------------------------------------------------------------------
# FastAPI Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SpeakAI Backend starting...")
    logger.info(f"   Stream keys configured: {sdk_cfg.has_all_keys}")
    yield
    logger.info("Shutting down — closing all sessions...")
    for sid in list(_sessions.keys()):
        try:
            await _sessions.pop(sid).stop()
        except Exception:
            pass
    for sid in list(_demo_services.keys()):
        try:
            await _demo_services.pop(sid).stop()
        except Exception:
            pass
    logger.info("SpeakAI Backend stopped")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SpeakAI — AI Communication Coach",
    version="1.0.0",
    description=(
        "AI agent that joins Stream Video calls as a real participant, "
        "provides real-time coaching on communication skills via Gemini "
        "Realtime, and streams coaching metrics to the frontend."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(server_cfg.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "sdk_keys_configured": sdk_cfg.has_all_keys,
        "active_sessions": len(_sessions),
        "active_demos": len(_demo_services),
    }


@app.get("/token")
async def token(user_id: str):
    if not sdk_cfg.stream_api_key or not sdk_cfg.stream_api_secret:
        return {"error": "Stream API keys not configured"}

    now = int(time.time())
    payload = {
        "user_id": user_id,
        "iat": now,
        "exp": now + 3600,
    }
    stream_token = jwt.encode(payload, sdk_cfg.stream_api_secret, algorithm="HS256")

    return {
        "api_key": sdk_cfg.stream_api_key,
        "token": stream_token,
        "user_id": user_id,
    }


# ---------------------------------------------------------------------------
# Post-Session API (proxies to ProgressTracker & ExerciseLibrary)
# ---------------------------------------------------------------------------

@app.get("/api/stats")
async def get_stats():
    """Aggregate statistics: total sessions, avg score, streaks, level."""
    try:
        return _get_tracker().get_stats()
    except Exception as e:
        return {"error": str(e)[:200]}


@app.get("/api/sessions")
async def get_sessions(limit: int = 20):
    """Recent session history."""
    try:
        return _get_tracker().get_session_history(limit=limit)
    except Exception as e:
        return {"error": str(e)[:200]}


@app.get("/api/sessions/{session_id}")
async def get_session_detail(session_id: int):
    """Detailed data for a single session."""
    try:
        detail = _get_tracker().get_session_detail(session_id)
        if not detail:
            return {"error": "Session not found"}
        return detail
    except Exception as e:
        return {"error": str(e)[:200]}


@app.get("/api/trends")
async def get_trends(limit: int = 30):
    """Score trend data for charts."""
    try:
        return _get_tracker().get_score_trend(limit=limit)
    except Exception as e:
        return {"error": str(e)[:200]}


@app.get("/api/exercises")
async def get_exercises(skill: str = None, difficulty: str = None):
    """Exercise library, optionally filtered."""
    try:
        lib = _get_exercises()
        if skill:
            return lib.get_by_skill(skill)
        if difficulty:
            return lib.get_by_difficulty(difficulty)
        return lib.get_all()
    except Exception as e:
        return {"error": str(e)[:200]}


@app.get("/api/exercises/recommend")
async def recommend_exercises():
    """Recommend exercises based on latest session weaknesses."""
    try:
        tracker = _get_tracker()
        lib = _get_exercises()
        sessions = tracker.get_session_history(limit=1)
        if sessions:
            improvements = sessions[0].get("improvements", [])
            return lib.recommend_for_weaknesses(improvements)
        return lib.get_random(3)
    except Exception as e:
        return {"error": str(e)[:200]}


# ---------------------------------------------------------------------------
# WebSocket: Per-Session Coaching Stream
# ---------------------------------------------------------------------------

@app.websocket("/ws/metrics")
async def websocket_metrics(ws: WebSocket):
    """
    WebSocket endpoint — one AgentSession or DemoService per connection.
    The AI agent joins a Stream Video call and streams coaching events.
    """
    await ws.accept()

    session_id = uuid.uuid4().hex[:12]
    current_service: Any = None
    start_task: Any = None
    status_task: Any = None

    async def send(data: Dict[str, Any]) -> None:
        try:
            await ws.send_text(json.dumps(data))
        except Exception:
            pass

    async def periodic_status():
        """Send system status every 5 seconds."""
        try:
            while True:
                await asyncio.sleep(5)
                if current_service:
                    telem = current_service.get_telemetry()
                    await send({"type": "system_status", "payload": telem})
        except asyncio.CancelledError:
            pass

    try:
        status_task = asyncio.create_task(periodic_status())

        while True:
            raw = await ws.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = message.get("type", "")

            # ── Start live session ──
            if msg_type == "start_session":
                if current_service is not None:
                    await send({"type": "error", "message": "Session already active"})
                    continue

                call_id = message.get("call_id", f"speakai-{session_id}")

                if not sdk_cfg.has_all_keys:
                    await send({
                        "type": "error",
                        "message": (
                            "Live agent unavailable. Set STREAM_API_KEY, "
                            "STREAM_API_SECRET, and GOOGLE_API_KEY."
                        ),
                    })
                    continue

                try:
                    session = AgentSession(session_id=session_id, send_fn=send)
                    _sessions[session_id] = session
                    current_service = session

                    await send({
                        "type": "session_starting",
                        "data": {
                            "session_id": session_id,
                            "call_id": call_id,
                            "session_state": "init",
                        },
                    })

                    async def _start():
                        try:
                            info = await session.start(call_id)
                            await send({"type": "session_started", "data": info})
                        except Exception as e:
                            logger.error(f"[{session_id}] Start failed: {e}")
                            _sessions.pop(session_id, None)
                            await send({
                                "type": "error",
                                "message": f"Failed to start agent: {str(e)[:200]}",
                            })

                    start_task = asyncio.create_task(_start())

                except Exception as e:
                    logger.error(f"[{session_id}] Session create error: {e}")
                    _sessions.pop(session_id, None)
                    current_service = None
                    await send({
                        "type": "error",
                        "message": f"Failed to create session: {str(e)[:200]}",
                    })

            # ── Start demo ──
            elif msg_type == "start_demo":
                if current_service is not None:
                    await send({"type": "error", "message": "Session already active"})
                    continue

                demo = DemoService(session_id=session_id, send_fn=send)
                info = await demo.start()
                _demo_services[session_id] = demo
                current_service = demo
                await send({"type": "demo_started", "data": info})

            # ── Stop session ──
            elif msg_type == "stop_session":
                if current_service is None:
                    continue

                if start_task and not start_task.done():
                    start_task.cancel()
                    try:
                        await start_task
                    except BaseException:
                        pass
                    start_task = None

                if isinstance(current_service, DemoService):
                    summary = await current_service.stop()
                    _demo_services.pop(session_id, None)
                else:
                    summary = await current_service.stop()
                    _sessions.pop(session_id, None)

                current_service = None
                await send({"type": "session_stopped", "data": summary})

            # ── Send chat message ──
            elif msg_type == "send_message":
                text = message.get("text", "").strip()
                if not text:
                    continue
                if current_service is None:
                    await send({"type": "error", "message": "No active session"})
                    continue
                if isinstance(current_service, DemoService):
                    await send({"type": "chat", "data": {
                        "id": uuid.uuid4().hex[:8],
                        "role": "user",
                        "content": text,
                        "timestamp": time.time(),
                        "source": "text",
                    }})
                    await send({"type": "chat", "data": {
                        "id": uuid.uuid4().hex[:8],
                        "role": "assistant",
                        "content": "I'm in demo mode. Start a live session to chat with the AI coach!",
                        "timestamp": time.time(),
                        "source": "demo",
                    }})
                else:
                    try:
                        await current_service.send_chat(text)
                    except Exception as e:
                        logger.debug(f"[{session_id}] Chat error: {e}")
                        await send({"type": "error", "message": "Failed to send message"})

            # ── Keepalive ──
            elif msg_type == "ping":
                await send({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"[{session_id}] WebSocket disconnected")
    except Exception as e:
        logger.error(f"[{session_id}] WebSocket error: {e}", exc_info=True)
    finally:
        if status_task and not status_task.done():
            status_task.cancel()
            try:
                await status_task
            except BaseException:
                pass

        if start_task and not start_task.done():
            start_task.cancel()
            try:
                await start_task
            except BaseException:
                pass

        if current_service is not None:
            if isinstance(current_service, DemoService):
                await current_service.stop()
                _demo_services.pop(session_id, None)
            else:
                await current_service.stop()
                _sessions.pop(session_id, None)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.server:app",
        host=server_cfg.host,
        port=server_cfg.port,
        reload=True,
        log_level="info",
    )
