"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import GlassCard from "@/components/ui/GlassCard";
import type { CoachEvent } from "@/lib/types";
import {
  AlertTriangle,
  Gauge,
  Shield,
  MessageCircleWarning,
  Eye,
  Activity,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Event color/icon config
// ---------------------------------------------------------------------------

const EVENT_CONFIG: Record<
  string,
  { color: string; bg: string; border: string; icon: React.ReactNode; label: string }
> = {
  filler_words: {
    color: "text-[#F59E0B]",
    bg: "bg-[#F59E0B]/10",
    border: "border-[#F59E0B]/20",
    icon: <MessageCircleWarning className="w-3.5 h-3.5" />,
    label: "Filler",
  },
  pace: {
    color: "text-[#4F8CFF]",
    bg: "bg-[#4F8CFF]/10",
    border: "border-[#4F8CFF]/20",
    icon: <Gauge className="w-3.5 h-3.5" />,
    label: "Pace",
  },
  confidence: {
    color: "text-[#22C55E]",
    bg: "bg-[#22C55E]/10",
    border: "border-[#22C55E]/20",
    icon: <Shield className="w-3.5 h-3.5" />,
    label: "Confidence",
  },
  hedging: {
    color: "text-[#8B5CF6]",
    bg: "bg-[#8B5CF6]/10",
    border: "border-[#8B5CF6]/20",
    icon: <AlertTriangle className="w-3.5 h-3.5" />,
    label: "Hedging",
  },
  body_language: {
    color: "text-[#06B6D4]",
    bg: "bg-[#06B6D4]/10",
    border: "border-[#06B6D4]/20",
    icon: <Eye className="w-3.5 h-3.5" />,
    label: "Body",
  },
};

const FALLBACK_CONFIG = {
  color: "text-white/60",
  bg: "bg-white/5",
  border: "border-white/10",
  icon: <Activity className="w-3.5 h-3.5" />,
  label: "Event",
};

// ---------------------------------------------------------------------------
// Format event body text
// ---------------------------------------------------------------------------

function formatEventBody(event: CoachEvent): string {
  switch (event.metric) {
    case "filler_words":
      return `"${event.word}" — ${event.count_in_window} in last ${event.count_in_window !== undefined ? "60s" : "window"} (total: ${event.total_in_session ?? 0})`;
    case "pace": {
      const wpm = event.words_per_minute?.toFixed(0) ?? "—";
      const rec = event.recommendation;
      if (rec === "good") return `${wpm} WPM ✓`;
      if (rec === "too_fast") return `${wpm} WPM — slow down`;
      if (rec === "too_slow") return `${wpm} WPM — speed up`;
      return `${wpm} WPM`;
    }
    case "confidence":
      return `Score: ${event.score?.toFixed(1) ?? "—"}/100`;
    case "hedging":
      return `"${event.phrase}" (total: ${event.count_in_session ?? 0})`;
    case "body_language": {
      const q = event.quality;
      const emoji = q === "good" ? "✓" : q === "needs_improvement" ? "⚠" : "•";
      return `${emoji} ${event.observation ?? event.category}`;
    }
    default:
      return JSON.stringify(event);
  }
}

// ---------------------------------------------------------------------------
// Timestamp formatter
// ---------------------------------------------------------------------------

function formatTime(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface CoachingFeedPanelProps {
  events: CoachEvent[];
  className?: string;
}

export default function CoachingFeedPanel({ events, className }: CoachingFeedPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to top when new events arrive (newest first)
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [events.length]);

  return (
    <GlassCard className={cn("p-0 flex flex-col", className)} hover={false} glow="blue">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-[#4F8CFF]" />
          <h3 className="text-sm font-semibold text-white/80">Live Coaching Feed</h3>
        </div>
        <span className="text-xs text-white/30">{events.length} events</span>
      </div>

      {/* Event list */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-3 space-y-2 max-h-[500px] scrollbar-thin"
      >
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-white/30">
            <Activity className="w-8 h-8 mb-3 opacity-40" />
            <p className="text-sm">No events yet</p>
            <p className="text-xs mt-1">Start a session to see live coaching feedback</p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {events.map((event) => {
              const config = EVENT_CONFIG[event.metric] ?? FALLBACK_CONFIG;
              return (
                <motion.div
                  key={event.id}
                  initial={{ opacity: 0, y: -10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.25, ease: [0.25, 0.1, 0.25, 1] }}
                  className={cn(
                    "flex items-start gap-3 p-3 rounded-lg border",
                    config.bg,
                    config.border
                  )}
                >
                  {/* Icon pill */}
                  <div
                    className={cn(
                      "flex items-center justify-center w-7 h-7 rounded-md shrink-0 mt-0.5",
                      config.bg,
                      config.color
                    )}
                  >
                    {config.icon}
                  </div>

                  {/* Body */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span
                        className={cn("text-xs font-semibold uppercase tracking-wider", config.color)}
                      >
                        {config.label}
                      </span>
                      <span className="text-[10px] text-white/25 shrink-0">
                        {formatTime(event.timestamp)}
                      </span>
                    </div>
                    <p className="text-xs text-white/60 mt-0.5 leading-relaxed">
                      {formatEventBody(event)}
                    </p>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </GlassCard>
  );
}
