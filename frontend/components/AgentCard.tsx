"use client";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, AlertCircle, Loader2, Circle, Activity } from "lucide-react";
import clsx from "clsx";
import type { AgentStatus } from "@/lib/api";

interface Props {
  name: string;
  displayName: string;
  status: AgentStatus;
  lastThought: string | null;
  tokensUsed: number;
  latencyMs: number | null;
  error: string | null;
  accentColor?: "blue" | "purple" | "teal" | "warning";
}

const COLOR_MAP = {
  blue: { dot: "bg-accent-primary", glow: "shadow-[0_0_20px_rgba(91,141,239,0.4)]", text: "text-accent-primary" },
  purple: { dot: "bg-accent-purple", glow: "shadow-[0_0_20px_rgba(159,122,234,0.4)]", text: "text-accent-purple" },
  teal: { dot: "bg-accent-teal", glow: "shadow-[0_0_20px_rgba(56,217,205,0.4)]", text: "text-accent-teal" },
  warning: { dot: "bg-accent-warning", glow: "shadow-[0_0_20px_rgba(245,166,35,0.4)]", text: "text-accent-warning" },
};

export default function AgentCard({ name, displayName, status, lastThought: thought, tokensUsed, latencyMs, error, accentColor = "blue" }: Props) {
  const c = COLOR_MAP[accentColor];

  const StatusIcon = () => {
    switch (status) {
      case "idle":
        return <Circle size={14} className="text-text-muted" />;
      case "running":
        return <Loader2 size={14} className={clsx("animate-spin", c.text)} />;
      case "retrying":
        return <Activity size={14} className="animate-pulse text-accent-warning" />;
      case "completed":
        return <CheckCircle2 size={14} className="text-accent-success" />;
      case "failed":
        return <AlertCircle size={14} className="text-accent-danger" />;
    }
  };

  const statusLabel = {
    idle: "Awaiting",
    running: "Processing",
    retrying: "Retrying",
    completed: "Complete",
    failed: "Failed",
  }[status];

  return (
    <motion.div
      layout
      className={clsx(
        "panel-padded relative transition-all",
        status === "running" && c.glow,
      )}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className={clsx("h-2 w-2 rounded-full flex-shrink-0", c.dot, status === "running" && "animate-pulse-glow")} />
          <div className="min-w-0 flex-1">
            <p className="font-medium text-sm truncate">{displayName}</p>
            <p className="label-mono text-[10px] mt-0.5 truncate">{name}</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <StatusIcon />
          <span className={clsx(
            "text-[10px] uppercase tracking-wider font-medium",
            status === "running" && c.text,
            status === "completed" && "text-accent-success",
            status === "failed" && "text-accent-danger",
            status === "idle" && "text-text-muted",
          )}>
            {statusLabel}
          </span>
        </div>
      </div>

      <AnimatePresence mode="wait">
        {thought && (
          <motion.p
            key={thought}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="text-xs text-text-secondary leading-relaxed mb-3 min-h-[16px]"
          >
            {status === "running" && (
              <span className="streaming-dots inline-block mr-2">
                <span /><span /><span />
              </span>
            )}
            {thought}
          </motion.p>
        )}
      </AnimatePresence>

      {error && (
        <p className="text-xs text-accent-danger bg-accent-danger/10 p-2 rounded mt-2">
          {error}
        </p>
      )}

      <div className="flex items-center gap-4 mt-3 pt-3 border-t border-border-default">
        <Stat label="Tokens" value={tokensUsed > 0 ? tokensUsed.toLocaleString() : "—"} />
        <Stat label="Latency" value={latencyMs ? `${(latencyMs / 1000).toFixed(1)}s` : "—"} />
      </div>
    </motion.div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-[9px] uppercase tracking-wider text-text-muted">{label}</span>
      <span className="font-mono text-xs text-text-secondary">{value}</span>
    </div>
  );
}
