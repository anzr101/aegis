"use client";
import { useState } from "react";
import BriefForm from "@/components/BriefForm";
import AgentCard from "@/components/AgentCard";
import PipelineGraph from "@/components/PipelineGraph";
import StreamingThoughts from "@/components/StreamingThoughts";
import ResultsPanel from "@/components/ResultsPanel";
import { usePipelineStore } from "@/lib/store";
import { startPipeline, subscribeToPipeline, getPipelineResult, type CampaignBrief } from "@/lib/api";
import { RotateCcw, Zap } from "lucide-react";

export default function Page() {
  const [error, setError] = useState<string | null>(null);
  const {
    runId, brief, agents, events, pipelineStatus, pipelineThought,
    result, isStreaming, startRun, pushEvent, setResult, reset,
  } = usePipelineStore();

  const handleSubmit = async (b: CampaignBrief) => {
    setError(null);
    try {
      const { run_id } = await startPipeline(b);
      startRun(run_id, b);

      subscribeToPipeline(
        run_id,
        (event) => pushEvent(event),
        async () => {
          // Pipeline completed — fetch final result
          const fullResult = await getPipelineResult(run_id);
          setResult(fullResult);
        },
        (err) => setError(err.message),
      );
    } catch (e: any) {
      setError(e.message || "Failed to start pipeline");
    }
  };

  return (
    <main className="relative z-10 max-w-7xl mx-auto px-6 py-8">
      {/* Header */}
      <header className="flex items-center justify-between mb-8 pb-6 border-b border-border-default">
        <div className="flex items-center gap-4">
          <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-accent-primary to-accent-glow flex items-center justify-center">
            <Zap size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-xl font-medium tracking-tight">AEGIS</h1>
            <p className="text-xs text-text-tertiary">Autonomous Engagement & Generative Intelligence System</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {pipelineStatus !== "idle" && (
            <button onClick={reset} className="btn-ghost text-xs flex items-center gap-1.5">
              <RotateCcw size={12} />
              New run
            </button>
          )}
          <div className="flex items-center gap-2 text-xs text-text-tertiary font-mono">
            <span className="h-1.5 w-1.5 rounded-full bg-accent-success animate-pulse" />
            v1.0.0
          </div>
        </div>
      </header>

      {error && (
        <div className="panel-padded border-accent-danger/40 mb-4 text-sm text-accent-danger">
          Error: {error}
        </div>
      )}

      {/* Workflow */}
      {!runId ? (
        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-2">
            <BriefForm onSubmit={handleSubmit} />
          </div>
          <div className="space-y-4">
            <div className="panel-padded">
              <p className="label-eyebrow mb-3">System Architecture</p>
              <p className="text-sm text-text-secondary leading-relaxed mb-3">
                AEGIS orchestrates 5 specialized AI agents in a directed pipeline. Three run in parallel for speed; scoring and synthesis run sequentially for context.
              </p>
              <ul className="text-xs text-text-secondary space-y-1.5">
                <li><span className="text-accent-primary font-mono">[01]</span> Trend Intelligence — live web search</li>
                <li><span className="text-accent-purple font-mono">[02]</span> Audience Psychology — 9-axis profiling</li>
                <li><span className="text-accent-teal font-mono">[03]</span> Creative Strategy — 3 multi-modal concepts</li>
                <li><span className="text-accent-warning font-mono">[04]</span> Evaluation — 8-dimension scoring + self-critique</li>
                <li><span className="text-accent-glow font-mono">[05]</span> Supervisor — cross-agent synthesis (Opus)</li>
              </ul>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Pipeline status banner */}
          <div className="panel-padded flex items-center justify-between">
            <div>
              <p className="label-eyebrow mb-1">
                {pipelineStatus === "completed" ? "Run complete" : pipelineStatus === "failed" ? "Run failed" : "Run in progress"}
              </p>
              <p className="text-sm text-text-secondary">{pipelineThought || "Initializing..."}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-text-muted font-mono">{runId.slice(0, 8)}</p>
              <p className="text-xs text-text-secondary mt-0.5">{brief?.brand}</p>
            </div>
          </div>

          {/* Pipeline graph */}
          <PipelineGraph agents={agents} />

          {/* Agent cards */}
          <div>
            <p className="label-eyebrow mb-3">Agent State</p>
            <div className="grid grid-cols-3 gap-4">
              <AgentCard {...agents.trend_agent} accentColor="blue" />
              <AgentCard {...agents.audience_agent} accentColor="purple" />
              <AgentCard {...agents.creative_agent} accentColor="teal" />
              <AgentCard {...agents.scoring_agent} accentColor="warning" />
              <AgentCard {...agents.supervisor} accentColor="blue" />
            </div>
          </div>

          {/* Streaming thoughts */}
          <StreamingThoughts events={events} />

          {/* Results */}
          {result && <ResultsPanel result={result} />}
        </div>
      )}
    </main>
  );
}
