"use client";
import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { AgentEvent } from "@/lib/api";
import { Activity } from "lucide-react";

interface Props {
  events: AgentEvent[];
}

const AGENT_LABELS: Record<string, string> = {
  trend_agent: "TREND",
  audience_agent: "AUDIENCE",
  creative_agent: "CREATIVE",
  scoring_agent: "SCORING",
  supervisor: "SUPERVISOR",
  __pipeline__: "SYSTEM",
};

const AGENT_COLORS: Record<string, string> = {
  trend_agent: "text-accent-primary",
  audience_agent: "text-accent-purple",
  creative_agent: "text-accent-teal",
  scoring_agent: "text-accent-warning",
  supervisor: "text-accent-glow",
  __pipeline__: "text-text-secondary",
};

export default function StreamingThoughts({ events }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: "smooth" });
  }, [events]);

  const eventsWithThoughts = events.filter((e) => e.thought);

  return (
    <div className="panel-padded h-[400px] flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Activity size={14} className="text-accent-primary" />
          <p className="label-eyebrow">Live Reasoning Stream</p>
        </div>
        <p className="label-mono">{eventsWithThoughts.length} events</p>
      </div>

      <div ref={ref} className="flex-1 overflow-y-auto space-y-2.5 pr-1">
        {eventsWithThoughts.length === 0 ? (
          <div className="h-full flex items-center justify-center text-text-muted text-sm">
            Awaiting pipeline activity...
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {eventsWithThoughts.map((e, i) => (
              <motion.div
                key={`${e.timestamp}-${i}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2 }}
                className="flex gap-3 text-xs"
              >
                <span className="font-mono text-text-muted w-16 flex-shrink-0">
                  {new Date(e.timestamp).toLocaleTimeString("en-US", { hour12: false })}
                </span>
                <span className={`font-mono text-[10px] uppercase tracking-wider w-20 flex-shrink-0 mt-0.5 ${AGENT_COLORS[e.agent_name] || "text-text-muted"}`}>
                  {AGENT_LABELS[e.agent_name] || e.agent_name}
                </span>
                <span className="text-text-secondary leading-relaxed flex-1">
                  {e.thought}
                  {e.tokens_used != null && e.tokens_used > 0 && (
                    <span className="ml-2 text-text-muted">
                      [{e.tokens_used.toLocaleString()} tok · {((e.latency_ms || 0) / 1000).toFixed(1)}s]
                    </span>
                  )}
                </span>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
