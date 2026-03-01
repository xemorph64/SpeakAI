"use client";

import { cn } from "@/lib/utils";
import AnimatedNumber from "@/components/ui/AnimatedNumber";
import { motion } from "framer-motion";
import { Gauge, TrendingUp, TrendingDown, Minus } from "lucide-react";

interface PaceBadgeProps {
  wpm: number;
  recommendation: string;
  className?: string;
}

const recConfig: Record<string, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
  good: {
    label: "Good Pace",
    color: "text-[#22C55E]",
    bg: "bg-[#22C55E]/10",
    icon: <TrendingUp className="w-3 h-3" />,
  },
  too_fast: {
    label: "Too Fast",
    color: "text-[#EF4444]",
    bg: "bg-[#EF4444]/10",
    icon: <TrendingUp className="w-3 h-3" />,
  },
  too_slow: {
    label: "Too Slow",
    color: "text-[#F59E0B]",
    bg: "bg-[#F59E0B]/10",
    icon: <TrendingDown className="w-3 h-3" />,
  },
};

const defaultRec = {
  label: "Measuring",
  color: "text-white/40",
  bg: "bg-white/5",
  icon: <Minus className="w-3 h-3" />,
};

export default function PaceBadge({ wpm, recommendation, className }: PaceBadgeProps) {
  const config = recConfig[recommendation] ?? defaultRec;

  return (
    <div className={cn("flex flex-col items-center gap-2", className)}>
      {/* WPM number */}
      <div className="flex items-baseline gap-1">
        <AnimatedNumber
          value={Math.round(wpm)}
          className="text-3xl font-bold text-[#4F8CFF]"
        />
        <span className="text-sm text-white/40 font-medium">WPM</span>
      </div>

      {/* Recommendation badge */}
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className={cn(
          "inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium",
          config.bg,
          config.color
        )}
      >
        {config.icon}
        {config.label}
      </motion.div>

      {/* Ideal range indicator */}
      <div className="w-full max-w-[180px] mt-1">
        <div className="relative h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
          {/* Ideal zone highlight */}
          <div
            className="absolute h-full bg-[#22C55E]/20 rounded-full"
            style={{ left: "40%", width: "27%" }}
          />
          {/* Needle */}
          <motion.div
            className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-[#4F8CFF]"
            style={{ boxShadow: "0 0 8px #4F8CFF60" }}
            initial={{ left: "0%" }}
            animate={{ left: `${Math.min(Math.max((wpm / 250) * 100, 2), 98)}%` }}
            transition={{ duration: 1, ease: [0.25, 0.1, 0.25, 1] }}
          />
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-[9px] text-white/20">0</span>
          <span className="text-[9px] text-white/30">120-160</span>
          <span className="text-[9px] text-white/20">250</span>
        </div>
      </div>
    </div>
  );
}
