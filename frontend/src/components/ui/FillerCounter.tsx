"use client";

import { cn } from "@/lib/utils";
import AnimatedNumber from "@/components/ui/AnimatedNumber";
import { motion, AnimatePresence } from "framer-motion";
import { MessageCircleWarning } from "lucide-react";

interface FillerCounterProps {
  countInWindow: number;
  totalInSession: number;
  lastWord: string;
  /** Threshold above which the counter shows a warning */
  threshold?: number;
  className?: string;
}

export default function FillerCounter({
  countInWindow,
  totalInSession,
  lastWord,
  threshold = 3,
  className,
}: FillerCounterProps) {
  const isAboveThreshold = countInWindow >= threshold;

  return (
    <div className={cn("flex flex-col items-center gap-2", className)}>
      {/* Main count */}
      <div className="relative">
        <AnimatedNumber
          value={totalInSession}
          className={cn(
            "text-3xl font-bold",
            isAboveThreshold ? "text-[#EF4444]" : "text-[#F59E0B]"
          )}
        />
        {/* Pulse ring when above threshold */}
        <AnimatePresence>
          {isAboveThreshold && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="absolute -inset-2 rounded-full border-2 border-[#EF4444]/30 animate-pulse"
            />
          )}
        </AnimatePresence>
      </div>

      <span className="text-xs text-white/40">total this session</span>

      {/* Window count bar */}
      <div className="w-full max-w-[160px]">
        <div className="flex justify-between text-[10px] mb-1">
          <span className="text-white/30">Last 60s</span>
          <span className={cn(
            "font-semibold",
            isAboveThreshold ? "text-[#EF4444]" : "text-[#F59E0B]"
          )}>
            {countInWindow}
          </span>
        </div>
        <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
          <motion.div
            className="h-full rounded-full"
            style={{
              backgroundColor: isAboveThreshold ? "#EF4444" : "#F59E0B",
              boxShadow: isAboveThreshold
                ? "0 0 12px #EF444430"
                : "0 0 12px #F59E0B30",
            }}
            initial={{ width: "0%" }}
            animate={{ width: `${Math.min((countInWindow / 10) * 100, 100)}%` }}
            transition={{ duration: 0.6, ease: [0.25, 0.1, 0.25, 1] }}
          />
        </div>
      </div>

      {/* Last detected word */}
      <AnimatePresence mode="wait">
        {lastWord && (
          <motion.div
            key={lastWord + totalInSession}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            className="flex items-center gap-1.5 mt-1"
          >
            <MessageCircleWarning className="w-3 h-3 text-[#F59E0B]/60" />
            <span className="text-[11px] text-white/40">
              Last: <span className="text-[#F59E0B] font-medium">&ldquo;{lastWord}&rdquo;</span>
            </span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
