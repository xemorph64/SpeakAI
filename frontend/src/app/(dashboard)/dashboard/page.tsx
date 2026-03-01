"use client";

import { motion } from "framer-motion";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import StreamCallPanel from "@/components/dashboard/StreamCallPanel";
import ChatPanel from "@/components/dashboard/ChatPanel";
import CoachingFeedPanel from "@/components/dashboard/CoachingFeedPanel";
import ConfidenceBreakdown from "@/components/dashboard/ConfidenceBreakdown";
import MetricCard from "@/components/ui/MetricCard";
import GlassCard from "@/components/ui/GlassCard";
import AnimatedNumber from "@/components/ui/AnimatedNumber";
import PaceBadge from "@/components/ui/PaceBadge";
import FillerCounter from "@/components/ui/FillerCounter";
import { useMetricsStream } from "@/hooks/useMetricsStream";
import { addSession, type StoredSession } from "@/lib/sessionStore";
import type { CoachingMetrics } from "@/lib/types";
import {
  Gauge,
  Shield,
  MessageCircleWarning,
  AlertTriangle,
  Play,
  Square,
  Radio,
  Wifi,
  WifiOff,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Semi-circle gauge (reused for confidence score)
// ---------------------------------------------------------------------------

function SemiCircleGauge({
  value,
  max,
  color,
}: {
  value: number;
  max: number;
  color: string;
}) {
  const percentage = Math.min(value / max, 1);

  return (
    <div className="relative w-full flex justify-center">
      <svg viewBox="0 0 120 70" className="w-full max-w-[160px]">
        <path
          d="M 10 65 A 50 50 0 0 1 110 65"
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth="8"
          strokeLinecap="round"
        />
        <motion.path
          d="M 10 65 A 50 50 0 0 1 110 65"
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: percentage }}
          transition={{ duration: 1.5, ease: [0.25, 0.1, 0.25, 1] }}
          style={{ filter: `drop-shadow(0 0 6px ${color}40)` }}
        />
        <motion.line
          x1="60"
          y1="65"
          x2="60"
          y2="25"
          stroke="white"
          strokeWidth="1.5"
          strokeLinecap="round"
          style={{ transformOrigin: "60px 65px" }}
          initial={{ rotate: -90 }}
          animate={{ rotate: -90 + 180 * percentage }}
          transition={{ duration: 1.5, ease: [0.25, 0.1, 0.25, 1] }}
          opacity={0.6}
        />
        <circle cx="60" cy="65" r="3" fill="white" opacity="0.4" />
      </svg>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Animation variants
// ---------------------------------------------------------------------------

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 15 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.25, 0.1, 0.25, 1] as const },
  },
};

// ---------------------------------------------------------------------------
// Wrapper with Suspense
// ---------------------------------------------------------------------------

export default function DashboardPageWrapper() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-64 text-white/30 text-sm">
          Loading dashboard…
        </div>
      }
    >
      <DashboardPage />
    </Suspense>
  );
}

// ---------------------------------------------------------------------------
// Main Dashboard Page
// ---------------------------------------------------------------------------

function DashboardPage() {
  const searchParams = useSearchParams();
  const scenarioType = searchParams.get("type") || "Free Practice";

  const [streamCallId, setStreamCallId] = useState("speakai-live");
  const [streamReady, setStreamReady] = useState(false);
  const [streamMediaReady, setStreamMediaReady] = useState(false);

  const {
    metrics,
    coachEvents,
    connectionStatus,
    sessionStatus,
    systemStatus,
    lastError,
    connect,
    startSession,
    stopSession,
    startDemo,
    chatMessages,
    transcript,
    conversationState,
    sendMessage,
  } = useMetricsStream({ url: "ws://localhost:8080/ws/metrics", autoConnect: false });

  // Auto-connect on mount
  useEffect(() => {
    connect();
  }, [connect]);

  // -- Session tracking for persistence --
  const sessionStartRef = useRef<number | null>(null);
  const [sessionLabel, setSessionLabel] = useState(scenarioType);

  useEffect(() => {
    setSessionLabel(searchParams.get("type") || "Free Practice");
  }, [searchParams]);

  // Track session start
  useEffect(() => {
    if (sessionStatus !== "idle" && sessionStartRef.current === null) {
      sessionStartRef.current = Date.now();
    }
  }, [sessionStatus]);

  // Save session when it stops
  const handleStop = useCallback(() => {
    const durationSeconds = sessionStartRef.current
      ? Math.round((Date.now() - sessionStartRef.current) / 1000)
      : 0;

    if (durationSeconds > 3) {
      const stored: StoredSession = {
        id: crypto.randomUUID(),
        title: `${sessionLabel} Session`,
        type: sessionLabel,
        date: new Date().toISOString(),
        durationSeconds,
        score: Math.round(metrics.confidence_score),
        metrics: {
          confidence_score: metrics.confidence_score,
          filler_total: metrics.filler_total,
          words_per_minute: metrics.words_per_minute,
          hedging_count: metrics.hedging_count,
          pace_recommendation: metrics.pace_recommendation,
        },
        timeline: [],
      };
      addSession(stored);
    }

    sessionStartRef.current = null;
    stopSession();
  }, [metrics, sessionLabel, stopSession]);

  // Auto-start from query param
  useEffect(() => {
    if (
      searchParams.get("autostart") === "demo" &&
      connectionStatus === "connected" &&
      sessionStatus === "idle"
    ) {
      startDemo();
    }
    if (
      searchParams.get("autostart") === "live" &&
      connectionStatus === "connected" &&
      sessionStatus === "idle" &&
      streamReady
    ) {
      startSession(streamCallId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connectionStatus, streamReady, streamCallId]);

  const isSessionActive = sessionStatus !== "idle";

  // Confidence color
  const confidenceColor =
    metrics.confidence_score >= 75
      ? "#22C55E"
      : metrics.confidence_score >= 50
        ? "#F59E0B"
        : "#EF4444";

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      {/* ── Session Control Bar ── */}
      <motion.div
        variants={fadeUp}
        className="flex items-center justify-between gap-4 flex-wrap"
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            {connectionStatus === "connected" ? (
              <Wifi className="w-4 h-4 text-[#22C55E]" />
            ) : connectionStatus === "reconnecting" ? (
              <WifiOff className="w-4 h-4 text-[#F59E0B] animate-pulse" />
            ) : (
              <WifiOff className="w-4 h-4 text-white/30" />
            )}
            <span className="text-xs text-white/40 capitalize">
              {connectionStatus}
            </span>
          </div>
          {isSessionActive && (
            <div className="flex items-center gap-1.5">
              <Radio className="w-3 h-3 text-[#EF4444] animate-pulse" />
              <span className="text-xs text-white/50 uppercase tracking-wider font-medium">
                {sessionStatus === "demo" ? "Demo Mode" : "Live Session"}
              </span>
            </div>
          )}
          {isSessionActive &&
            sessionStatus !== "demo" &&
            systemStatus?.session_state &&
            systemStatus.session_state !== "active" && (
              <span className="text-[10px] font-semibold uppercase tracking-widest px-2 py-0.5 rounded-full border text-white/30 border-white/10 bg-white/5">
                {systemStatus.session_state}
              </span>
            )}
        </div>

        <div className="flex items-center gap-2">
          {!isSessionActive ? (
            <>
              <button
                onClick={() => startSession(streamCallId)}
                disabled={
                  connectionStatus !== "connected" ||
                  !streamReady ||
                  !streamMediaReady
                }
                className="inline-flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-lg bg-[#4F8CFF]/15 text-[#4F8CFF] border border-[#4F8CFF]/20 hover:bg-[#4F8CFF]/25 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <Play className="w-3.5 h-3.5" /> Start Session
              </button>
              <button
                onClick={startDemo}
                disabled={connectionStatus !== "connected"}
                className="inline-flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-lg bg-[#8B5CF6]/15 text-[#8B5CF6] border border-[#8B5CF6]/20 hover:bg-[#8B5CF6]/25 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <Radio className="w-3.5 h-3.5" /> Demo Mode
              </button>
            </>
          ) : (
            <button
              onClick={handleStop}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-lg bg-[#EF4444]/15 text-[#EF4444] border border-[#EF4444]/20 hover:bg-[#EF4444]/25 transition-colors"
            >
              <Square className="w-3.5 h-3.5" /> Stop Session
            </button>
          )}
        </div>
      </motion.div>

      {lastError && (
        <motion.p variants={fadeUp} className="text-xs text-[#EF4444]/80 -mt-2">
          {lastError}
        </motion.p>
      )}

      {/* ── Main Grid: Video + Metrics + Feed ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Video Call + Chat */}
        <motion.div variants={fadeUp} className="lg:col-span-5">
          <StreamCallPanel
            connectionStatus={connectionStatus}
            sessionStatus={sessionStatus}
            streaming={isSessionActive}
            onReadyChange={setStreamReady}
            onMediaReadyChange={setStreamMediaReady}
            onCallIdChange={setStreamCallId}
          />
          <motion.div variants={fadeUp} className="mt-4">
            <ChatPanel
              messages={chatMessages}
              transcript={transcript}
              conversationState={conversationState}
              onSendMessage={sendMessage}
              sessionActive={isSessionActive}
              className="h-[300px]"
            />
          </motion.div>
        </motion.div>

        {/* Center Column: Core Metrics */}
        <div className="lg:col-span-4 space-y-4">
          {/* Confidence Score — big gauge */}
          <motion.div variants={fadeUp}>
            <MetricCard
              label="Confidence Score"
              value={Math.round(metrics.confidence_score)}
              suffix="/100"
              trend={
                metrics.confidence_score >= 70
                  ? "up"
                  : metrics.confidence_score > 0
                    ? "down"
                    : undefined
              }
              trendValue={
                metrics.confidence_score >= 70 ? "Strong" : "Improve"
              }
              icon={<Shield className="w-5 h-5" />}
              color="green"
            >
              <SemiCircleGauge
                value={metrics.confidence_score}
                max={100}
                color={confidenceColor}
              />
            </MetricCard>
          </motion.div>

          {/* Speaking Pace */}
          <motion.div variants={fadeUp}>
            <MetricCard
              label="Speaking Pace"
              value={Math.round(metrics.words_per_minute)}
              suffix="WPM"
              trend={
                metrics.pace_recommendation === "good"
                  ? "up"
                  : metrics.words_per_minute > 0
                    ? "down"
                    : undefined
              }
              trendValue={
                metrics.pace_recommendation === "good"
                  ? "Good pace"
                  : metrics.pace_recommendation === "too_fast"
                    ? "Slow down"
                    : "Speed up"
              }
              icon={<Gauge className="w-5 h-5" />}
              color="blue"
            >
              <PaceBadge
                wpm={metrics.words_per_minute}
                recommendation={metrics.pace_recommendation}
              />
            </MetricCard>
          </motion.div>

          {/* Filler Words */}
          <motion.div variants={fadeUp}>
            <MetricCard
              label="Filler Words"
              value={metrics.filler_total}
              trend={
                metrics.filler_words <= 3 && metrics.filler_total > 0
                  ? "down"
                  : metrics.filler_words > 3
                    ? "up"
                    : undefined
              }
              trendValue={
                metrics.filler_words <= 3 ? "Low" : "High"
              }
              icon={<MessageCircleWarning className="w-5 h-5" />}
              color="warning"
            >
              <FillerCounter
                countInWindow={metrics.filler_words}
                totalInSession={metrics.filler_total}
                lastWord={metrics.filler_last_word}
              />
            </MetricCard>
          </motion.div>

          {/* Hedging Language */}
          <motion.div variants={fadeUp}>
            <MetricCard
              label="Hedging Language"
              value={metrics.hedging_count}
              trend={
                metrics.hedging_count <= 2 && metrics.hedging_count > 0
                  ? "down"
                  : metrics.hedging_count > 2
                    ? "up"
                    : undefined
              }
              trendValue={
                metrics.hedging_count <= 2 ? "Low" : "Frequent"
              }
              icon={<AlertTriangle className="w-5 h-5" />}
              color="violet"
            >
              {metrics.hedging_last_phrase && (
                <p className="text-xs text-white/40 mt-1 text-center">
                  Last:{" "}
                  <span className="text-[#8B5CF6] font-medium">
                    &ldquo;{metrics.hedging_last_phrase}&rdquo;
                  </span>
                </p>
              )}
            </MetricCard>
          </motion.div>
        </div>

        {/* Right Column: Live Coaching Feed */}
        <motion.div variants={fadeUp} className="lg:col-span-3">
          <CoachingFeedPanel events={coachEvents} className="h-full" />
        </motion.div>
      </div>

      {/* ── Bottom: Confidence Factor Breakdown + Session Overview ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <motion.div variants={fadeUp}>
          <ConfidenceBreakdown
            factors={metrics.confidence_factors}
            overallScore={metrics.confidence_score}
          />
        </motion.div>

        <motion.div variants={fadeUp}>
          <GlassCard className="p-6" hover={false}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-white/80">
                Session Overview
              </h3>
              <span className="text-xs text-white/30 font-mono capitalize">
                {sessionStatus === "idle"
                  ? "Standby"
                  : `${sessionStatus} session`}
              </span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              {[
                {
                  label: "Confidence",
                  value: `${Math.round(metrics.confidence_score)}`,
                  sub:
                    metrics.confidence_score >= 70
                      ? "Strong"
                      : metrics.confidence_score > 0
                        ? "Needs work"
                        : "—",
                },
                {
                  label: "Pace",
                  value: `${Math.round(metrics.words_per_minute)}`,
                  sub:
                    metrics.pace_recommendation === "good"
                      ? "Good pace"
                      : metrics.pace_recommendation === "too_fast"
                        ? "Too fast"
                        : metrics.pace_recommendation === "too_slow"
                          ? "Too slow"
                          : "—",
                },
                {
                  label: "Fillers",
                  value: `${metrics.filler_total}`,
                  sub: `${metrics.filler_words} in last 60s`,
                },
                {
                  label: "Conversation",
                  value: `${conversationState?.turn_count ?? 0}`,
                  sub: conversationState?.is_agent_speaking
                    ? "AI Speaking"
                    : conversationState?.is_user_speaking
                      ? "User Speaking"
                      : `${chatMessages.length} msgs`,
                },
              ].map((stat, i) => (
                <motion.div
                  key={stat.label}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.8 + i * 0.1 }}
                >
                  <p className="text-xs text-white/40 mb-1">{stat.label}</p>
                  <p className="text-xl font-bold text-white/90">
                    {stat.value}
                  </p>
                  <p className="text-[11px] text-white/30 mt-0.5">
                    {stat.sub}
                  </p>
                </motion.div>
              ))}
            </div>
          </GlassCard>
        </motion.div>
      </div>
    </motion.div>
  );
}
