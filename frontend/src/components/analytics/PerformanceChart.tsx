"use client";

import { motion } from "framer-motion";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import GlassCard from "@/components/ui/GlassCard";

const defaultData = [
  { time: "S1", wpm: 120, confidence: 55, fillers: 8 },
  { time: "S2", wpm: 135, confidence: 60, fillers: 6 },
  { time: "S3", wpm: 145, confidence: 65, fillers: 5 },
  { time: "S4", wpm: 130, confidence: 62, fillers: 7 },
  { time: "S5", wpm: 140, confidence: 70, fillers: 4 },
  { time: "S6", wpm: 138, confidence: 72, fillers: 3 },
  { time: "S7", wpm: 142, confidence: 75, fillers: 3 },
  { time: "S8", wpm: 135, confidence: 78, fillers: 2 },
];

interface ChartDataPoint {
  time: string;
  wpm: number;
  confidence: number;
  fillers: number;
}

interface PerformanceChartProps {
  data?: ChartDataPoint[];
  subtitle?: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
  }>;
  label?: string;
}

const CustomTooltip = ({ active, payload, label }: CustomTooltipProps) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#0B0F19]/95 backdrop-blur-xl border border-white/[0.08] rounded-xl p-3 shadow-2xl">
        <p className="text-white/40 text-xs mb-2 font-medium">{label}</p>
        {payload.map((entry, index) => (
          <div key={index} className="flex items-center gap-2 text-xs py-0.5">
            <div
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-white/50">{entry.name}:</span>
            <span className="text-white font-semibold">{entry.value}</span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function PerformanceChart({
  data,
  subtitle,
}: PerformanceChartProps) {
  const chartData = data && data.length > 0 ? data : defaultData;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
    >
      <GlassCard className="p-6" hover={false}>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-base font-semibold text-white/90">
              Performance Over Time
            </h3>
            <p className="text-xs text-white/40 mt-1">
              {subtitle || "Coaching metrics across sessions"}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-[#4F8CFF]" />
              <span className="text-[11px] text-white/40">WPM</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-[#22C55E]" />
              <span className="text-[11px] text-white/40">Confidence</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-[#F59E0B]" />
              <span className="text-[11px] text-white/40">Fillers</span>
            </div>
          </div>
        </div>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 5, right: 5, left: -20, bottom: 5 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.04)"
                vertical={false}
              />
              <XAxis
                dataKey="time"
                stroke="rgba(255,255,255,0.2)"
                tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 11 }}
                axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
                tickLine={false}
              />
              <YAxis
                stroke="rgba(255,255,255,0.2)"
                tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 11 }}
                axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
                tickLine={false}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ display: "none" }} />
              <Line
                type="monotone"
                dataKey="wpm"
                name="WPM"
                stroke="#4F8CFF"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: "#4F8CFF", stroke: "#4F8CFF", strokeWidth: 2 }}
              />
              <Line
                type="monotone"
                dataKey="confidence"
                name="Confidence"
                stroke="#22C55E"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: "#22C55E", stroke: "#22C55E", strokeWidth: 2 }}
              />
              <Line
                type="monotone"
                dataKey="fillers"
                name="Fillers"
                stroke="#F59E0B"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: "#F59E0B", stroke: "#F59E0B", strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </GlassCard>
    </motion.div>
  );
}
