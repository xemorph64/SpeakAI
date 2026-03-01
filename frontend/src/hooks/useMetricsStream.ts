/**
 * SpeakAI — WebSocket Hook for Real-Time Coaching Metrics
 *
 * Connects to the Python backend WebSocket and provides:
 * - Live coaching metrics (filler words, pace, confidence, hedging, body language)
 * - Coaching event feed (scrolling list of individual events)
 * - Chat messages (bidirectional AI ↔ user conversation)
 * - Live transcript (speech-to-text from audio)
 * - Conversation state (who's speaking, turn count)
 * - Session control (start/stop/demo)
 * - Connection state management
 * - Auto-reconnect with exponential backoff
 *
 * The AI agent joins a Stream Video call as a real participant.
 * Coaching events are emitted by the Communication Coach processors.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import type {
  CoachingMetrics,
  CoachEvent,
  CoachEventType,
  ChatMessage,
  TranscriptEntry,
  ConversationState,
  ConnectionStatus,
  SessionStatus,
  SystemStatus,
  BodyLanguageObservation,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

const DEFAULT_METRICS: CoachingMetrics = {
  filler_words: 0,
  filler_total: 0,
  filler_last_word: "",
  words_per_minute: 0,
  pace_recommendation: "good",
  confidence_score: 0,
  confidence_factors: { filler_words: 0, pace: 0, hedging: 0, vocabulary: 0 },
  hedging_count: 0,
  hedging_last_phrase: "",
  body_language: [],
};

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

interface UseMetricsStreamOptions {
  url?: string;
  autoConnect?: boolean;
  maxReconnectAttempts?: number;
}

let eventIdCounter = 0;

const DEFAULT_WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8080/ws/metrics";

export function useMetricsStream(options: UseMetricsStreamOptions = {}) {
  const {
    url = DEFAULT_WS_URL,
    autoConnect = true,
    maxReconnectAttempts = 10,
  } = options;

  const [metrics, setMetrics] = useState<CoachingMetrics>(DEFAULT_METRICS);
  const [coachEvents, setCoachEvents] = useState<CoachEvent[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");
  const [sessionStatus, setSessionStatus] = useState<SessionStatus>("idle");
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);

  // Communication state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [conversationState, setConversationState] = useState<ConversationState | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingInterval = useRef<ReturnType<typeof setInterval> | null>(null);

  // -- Connect ---------------------------------------------------------------

  const connect = useCallback(() => {
    if (
      wsRef.current?.readyState === WebSocket.OPEN ||
      wsRef.current?.readyState === WebSocket.CONNECTING
    ) {
      return;
    }

    setConnectionStatus("connecting");
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus("connected");
      setLastError(null);
      reconnectAttempts.current = 0;
      console.log("✅ Metrics WebSocket connected");

      pingInterval.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, 15_000);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);

        switch (message.type) {
          // ── Coaching metrics (from Communication Coach processors) ──
          case "coach_metrics": {
            const data = message.data as Record<string, unknown>;
            const metric = data.metric as CoachEventType;

            // Create a CoachEvent for the feed
            const coachEvent: CoachEvent = {
              id: `evt-${++eventIdCounter}`,
              metric,
              timestamp: (data.timestamp as number) || Date.now() / 1000,
              ...(data as Record<string, unknown>),
            } as CoachEvent;

            setCoachEvents((prev) => [coachEvent, ...prev].slice(0, 100));

            // Update aggregate metrics
            setMetrics((prev) => {
              const next = { ...prev };
              switch (metric) {
                case "filler_words":
                  next.filler_words = (data.count_in_window as number) ?? prev.filler_words;
                  next.filler_total = (data.total_in_session as number) ?? prev.filler_total;
                  next.filler_last_word = (data.word as string) ?? prev.filler_last_word;
                  break;
                case "pace":
                  next.words_per_minute = (data.words_per_minute as number) ?? prev.words_per_minute;
                  next.pace_recommendation = (data.recommendation as string) ?? prev.pace_recommendation;
                  break;
                case "confidence":
                  next.confidence_score = (data.score as number) ?? prev.confidence_score;
                  if (data.factors) {
                    next.confidence_factors = data.factors as typeof next.confidence_factors;
                  }
                  break;
                case "hedging":
                  next.hedging_count = (data.count_in_session as number) ?? prev.hedging_count;
                  next.hedging_last_phrase = (data.phrase as string) ?? prev.hedging_last_phrase;
                  break;
                case "body_language": {
                  const obs: BodyLanguageObservation = {
                    category: (data.category as string) ?? "",
                    observation: (data.observation as string) ?? "",
                    quality: (data.quality as string) ?? "neutral",
                    timestamp: (data.timestamp as number) ?? Date.now() / 1000,
                  };
                  next.body_language = [obs, ...prev.body_language].slice(0, 20);
                  break;
                }
              }
              return next;
            });
            break;
          }

          // ── Chat messages ──
          case "chat": {
            const chatMsg = (message.payload ?? message.data) as ChatMessage;
            setChatMessages((prev) => [...prev, chatMsg].slice(-100));
            break;
          }

          // ── Transcript ──
          case "transcript": {
            const entry = (message.payload ?? message.data) as TranscriptEntry;
            if (entry.is_final) {
              setTranscript((prev) => [...prev, entry].slice(-200));
            }
            break;
          }

          // ── Conversation state ──
          case "conversation_state": {
            const state = (message.payload ?? message.data) as ConversationState;
            setConversationState(state);
            break;
          }

          // ── Session lifecycle ──
          case "session_started":
            setSessionStatus("active");
            setLastError(null);
            setChatMessages([]);
            setTranscript([]);
            setConversationState(null);
            setCoachEvents([]);
            setMetrics(DEFAULT_METRICS);
            break;

          case "session_starting":
            setSessionStatus("starting");
            setLastError(null);
            break;

          case "session_stopped":
            setSessionStatus("idle");
            break;

          case "session_summary":
            console.log("Session summary:", message.data);
            break;

          case "demo_started":
            setSessionStatus("demo");
            setLastError(null);
            setChatMessages([]);
            setTranscript([]);
            setCoachEvents([]);
            setMetrics(DEFAULT_METRICS);
            break;

          case "pong":
            break;

          case "system_status":
            setSystemStatus((message.payload ?? message.data) as SystemStatus);
            break;

          case "error":
            setLastError(message.message ?? "Unknown server error");
            console.warn("⚠️ Server error:", message.message ?? message.data);
            break;

          default:
            break;
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onerror = () => {
      setConnectionStatus("error");
    };

    ws.onclose = () => {
      setConnectionStatus("disconnected");
      if (pingInterval.current) clearInterval(pingInterval.current);

      if (reconnectAttempts.current < maxReconnectAttempts) {
        const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 30_000);
        setConnectionStatus("reconnecting");
        reconnectTimer.current = setTimeout(() => {
          reconnectAttempts.current++;
          connect();
        }, delay);
      }
    };
  }, [url, maxReconnectAttempts]);

  // -- Disconnect ------------------------------------------------------------

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    if (pingInterval.current) clearInterval(pingInterval.current);
    reconnectAttempts.current = maxReconnectAttempts;
    wsRef.current?.close();
    wsRef.current = null;
    setConnectionStatus("disconnected");
  }, [maxReconnectAttempts]);

  // -- Session Controls ------------------------------------------------------

  const startSession = useCallback((callId?: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({ type: "start_session", ...(callId ? { call_id: callId } : {}) })
      );
    }
  }, []);

  const stopSession = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "stop_session" }));
      setSessionStatus("idle");
    }
  }, []);

  const startDemo = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "start_demo" }));
    }
  }, []);

  const sendMessage = useCallback((text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN && text.trim()) {
      wsRef.current.send(JSON.stringify({ type: "send_message", text: text.trim() }));
    }
  }, []);

  // -- Lifecycle -------------------------------------------------------------

  useEffect(() => {
    if (autoConnect) connect();
    return () => disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    // Coaching state
    metrics,
    coachEvents,

    // Connection
    connectionStatus,
    sessionStatus,
    systemStatus,
    lastError,

    // Communication
    chatMessages,
    transcript,
    conversationState,

    // Actions
    connect,
    disconnect,
    startSession,
    stopSession,
    startDemo,
    sendMessage,
  };
}
