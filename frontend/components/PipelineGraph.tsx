"use client";
import { motion } from "framer-motion";
import clsx from "clsx";
import type { AgentStatus } from "@/lib/api";

interface Props {
  agents: Record<string, { status: AgentStatus }>;
}

interface Node {
  id: string;
  label: string;
  x: number;
  y: number;
  layer: number;
}

interface Edge {
  from: string;
  to: string;
}

const NODES: Node[] = [
  { id: "input", label: "Brief", x: 50, y: 200, layer: 0 },
  { id: "trend_agent", label: "Trend", x: 220, y: 80, layer: 1 },
  { id: "audience_agent", label: "Audience", x: 220, y: 200, layer: 1 },
  { id: "creative_agent", label: "Creative", x: 220, y: 320, layer: 1 },
  { id: "scoring_agent", label: "Scoring", x: 420, y: 320, layer: 2 },
  { id: "supervisor", label: "Supervisor", x: 600, y: 200, layer: 3 },
  { id: "output", label: "Brief", x: 760, y: 200, layer: 4 },
];

const EDGES: Edge[] = [
  { from: "input", to: "trend_agent" },
  { from: "input", to: "audience_agent" },
  { from: "input", to: "creative_agent" },
  { from: "creative_agent", to: "scoring_agent" },
  { from: "trend_agent", to: "supervisor" },
  { from: "audience_agent", to: "supervisor" },
  { from: "scoring_agent", to: "supervisor" },
  { from: "supervisor", to: "output" },
];

export default function PipelineGraph({ agents }: Props) {
  const nodeStatus = (id: string): AgentStatus | "io" => {
    if (id === "input" || id === "output") return "io" as any;
    return agents[id]?.status || "idle";
  };

  const isEdgeActive = (from: string, to: string) => {
    const fromStatus = nodeStatus(from);
    const toStatus = nodeStatus(to);
    if (fromStatus === "completed" && (toStatus === "running" || toStatus === "completed")) return true;
    if (fromStatus === "io" && toStatus === "running") return true;
    return false;
  };

  return (
    <div className="panel-padded">
      <p className="label-eyebrow mb-4">Pipeline Topology</p>
      <svg viewBox="0 0 820 400" className="w-full h-auto">
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" fill="#2A3756" />
          </marker>
          <marker id="arrow-active" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" fill="#5B8DEF" />
          </marker>
          <linearGradient id="edge-flow" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#5B8DEF" stopOpacity="0.2" />
            <stop offset="50%" stopColor="#5B8DEF" stopOpacity="1" />
            <stop offset="100%" stopColor="#5B8DEF" stopOpacity="0.2" />
          </linearGradient>
        </defs>

        {/* Layer divider lines */}
        {[170, 350, 530].map((x, i) => (
          <line key={i} x1={x} y1={20} x2={x} y2={380} stroke="#1E2841" strokeDasharray="2,4" strokeWidth="1" />
        ))}

        {/* Edges */}
        {EDGES.map((e, i) => {
          const from = NODES.find((n) => n.id === e.from)!;
          const to = NODES.find((n) => n.id === e.to)!;
          const active = isEdgeActive(e.from, e.to);
          return (
            <motion.line
              key={i}
              x1={from.x + 40}
              y1={from.y}
              x2={to.x - 40}
              y2={to.y}
              stroke={active ? "#5B8DEF" : "#1E2841"}
              strokeWidth={active ? 2 : 1}
              markerEnd={active ? "url(#arrow-active)" : "url(#arrow)"}
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.8, delay: i * 0.05 }}
            />
          );
        })}

        {/* Nodes */}
        {NODES.map((n) => {
          const status = nodeStatus(n.id);
          const isIO = status === ("io" as any);
          const isRunning = status === "running";
          const isComplete = status === "completed";
          const isFailed = status === "failed";

          let fill = "#0E1322";
          let stroke = "#2A3756";
          let textColor = "#9AA5BD";
          if (isIO) { fill = "#151B2E"; stroke = "#2A3756"; textColor = "#E8ECF4"; }
          if (isRunning) { fill = "#152040"; stroke = "#5B8DEF"; textColor = "#7AABFF"; }
          if (isComplete) { fill = "#10261E"; stroke = "#3FCF8E"; textColor = "#3FCF8E"; }
          if (isFailed) { fill = "#2A1416"; stroke = "#EF5B5B"; textColor = "#EF5B5B"; }

          return (
            <g key={n.id}>
              {isRunning && (
                <motion.circle
                  cx={n.x} cy={n.y} r={45}
                  fill="none" stroke="#5B8DEF" strokeWidth="1" opacity="0.4"
                  animate={{ r: [45, 55, 45], opacity: [0.4, 0, 0.4] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
              )}
              <motion.rect
                x={n.x - 40} y={n.y - 22}
                width={80} height={44} rx={6}
                fill={fill} stroke={stroke} strokeWidth={1.5}
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: n.layer * 0.1 }}
              />
              <text x={n.x} y={n.y + 4} textAnchor="middle"
                    fontSize="11" fontWeight="500" fill={textColor}
                    fontFamily="Inter, sans-serif">
                {n.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
