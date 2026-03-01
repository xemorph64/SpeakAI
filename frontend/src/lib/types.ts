/**
 * SpeakAI — Shared TypeScript Types
 *
 * Types for the Communication Coach's real-time coaching metrics,
 * events, and session data.
 */

// ---------------------------------------------------------------------------
// Coaching Metrics (streamed from backend via WebSocket)
// ---------------------------------------------------------------------------

/** Aggregate coaching metrics state, updated incrementally from events */
export interface CoachingMetrics {
  /** Filler word count in the current analysis window */
  filler_words: number;
  /** Total filler words in the entire session */
  filler_total: number;
  /** Most recent filler word detected */
  filler_last_word: string;
  /** Current speaking pace (words per minute) */
  words_per_minute: number;
  /** Pace recommendation: "too_fast" | "too_slow" | "good" */
  pace_recommendation: string;
  /** Composite confidence score 0–100 */
  confidence_score: number;
  /** Breakdown of confidence score factors */
  confidence_factors: ConfidenceFactors;
  /** Total hedging phrases in sessions */
  hedging_count: number;
  /** Last hedging phrase detected */
  hedging_last_phrase: string;
  /** Recent body language observations */
  body_language: BodyLanguageObservation[];
}

export interface ConfidenceFactors {
  filler_words: number;
  pace: number;
  hedging: number;
  vocabulary: number;
}

export interface BodyLanguageObservation {
  category: string;  // "eye_contact" | "posture" | "expression" | "gesture"
  observation: string;
  quality: string;   // "good" | "needs_improvement" | "neutral"
  timestamp: number;
}

// ---------------------------------------------------------------------------
// Coach Event (individual event from WebSocket)
// ---------------------------------------------------------------------------

export type CoachEventType =
  | "filler_words"
  | "pace"
  | "confidence"
  | "hedging"
  | "body_language";

export interface CoachEvent {
  id: string;
  metric: CoachEventType;
  timestamp: number;
  // Filler fields
  word?: string;
  count_in_window?: number;
  total_in_session?: number;
  // Pace fields
  words_per_minute?: number;
  recommendation?: string;
  // Confidence fields
  score?: number;
  factors?: ConfidenceFactors;
  // Hedging fields
  phrase?: string;
  count_in_session?: number;
  // Body language fields
  category?: string;
  observation?: string;
  quality?: string;
}

// ---------------------------------------------------------------------------
// Communication types (kept from original)
// ---------------------------------------------------------------------------

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
  source?: string;
}

export interface TranscriptEntry {
  speaker: string;
  text: string;
  timestamp: number;
  confidence: number;
  is_final: boolean;
}

export interface ConversationState {
  is_user_speaking: boolean;
  is_agent_speaking: boolean;
  turn_count: number;
  last_user_speech: string;
  last_agent_response: string;
}

// ---------------------------------------------------------------------------
// Session types
// ---------------------------------------------------------------------------

export type ConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "error"
  | "reconnecting";

export type SessionStatus = "idle" | "starting" | "active" | "demo";

export interface SystemStatus {
  agent_joined: boolean;
  session_state?: string;
  session_mode?: string;
  elapsed_seconds?: number;
  source?: string;
  [key: string]: unknown;
}
