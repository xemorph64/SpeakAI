"use client";

import { motion } from "framer-motion";
import GlassCard from "@/components/ui/GlassCard";
import AnimatedNumber from "@/components/ui/AnimatedNumber";
import type { ConfidenceFactors } from "@/lib/types";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Factor bar configuration
// ---------------------------------------------------------------------------

const FACTORS: Array<{
  key: keyof ConfidenceFactors;
  label: string;
  color: string;
}> = [
  { key: "filler_words", label: "Filler Words", color: "#F59E0B" },
  { key: "pace", label: "Speaking Pace", color: "#4F8CFF" },
  { key: "hedging", label: "Hedging Language", color: "#8B5CF6" },
  { key: "vocabulary", label: "Vocabulary", color: "#06B6D4" },
];

function getBarColor(value: number): string {
  if (value >= 75) return "#22C55E";
  if (value >= 50) return "#F59E0B";
  return "#EF4444";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface ConfidenceBreakdownProps {
  factors: ConfidenceFactors;
  overallScore: number;
  className?: string;
}

export default function ConfidenceBreakdown({
  factors,
  overallScore,
  className,
}: ConfidenceBreakdownProps) {
  return (
    <GlassCard className={cn("p-6", className)} hover={false}>
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-sm font-semibold text-white/80">Confidence Breakdown</h3>
        <div className="flex items-baseline gap-1">
          <AnimatedNumber
            value={Math.round(overallScore)}
            className="text-2xl font-bold text-[#22C55E]"
          />
          <span className="text-xs text-white/40">/100</span>
        </div>
      </div>

      <div className="space-y-4">
        {FACTORS.map(({ key, label, color }) => {
          const value = factors[key] ?? 0;
          const barColor = getBarColor(value);

          return (
            <div key={key}>
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <div
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  <span className="text-xs text-white/60">{label}</span>
                </div>
                <span
                  className="text-xs font-semibold"
                  style={{ color: barColor }}
                >
                  {Math.round(value)}
                </span>
              </div>
              <div className="w-full h-2 bg-white/[0.06] rounded-full overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{
                    backgroundColor: barColor,
                    boxShadow: `0 0 12px ${barColor}30`,
                  }}
                  initial={{ width: "0%" }}
                  animate={{ width: `${Math.min(value, 100)}%` }}
                  transition={{ duration: 1.2, ease: [0.25, 0.1, 0.25, 1] }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </GlassCard>
  );
}
