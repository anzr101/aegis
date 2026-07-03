import { create } from "zustand";
import type { AgentEvent, AgentStatus, CampaignBrief } from "./api";

interface AgentState {
  name: string;
  displayName: string;
  status: AgentStatus;
  lastThought: string | null;
  tokensUsed: number;
  latencyMs: number | null;
  error: string | null;
}

interface PipelineState {
  runId: string | null;
  brief: CampaignBrief | null;
  agents: Record<string, AgentState>;
  events: AgentEvent[];
  pipelineStatus: AgentStatus;
  pipelineThought: string | null;
  result: any | null;
  isStreaming: boolean;

  startRun: (runId: string, brief: CampaignBrief) => void;
  pushEvent: (event: AgentEvent) => void;
  setResult: (result: any) => void;
  reset: () => void;
}

const INITIAL_AGENTS: Record<string, AgentState> = {
  trend_agent: { name: "trend_agent", displayName: "Trend Intelligence", status: "idle", lastThought: null, tokensUsed: 0, latencyMs: null, error: null },
  audience_agent: { name: "audience_agent", displayName: "Audience Psychology", status: "idle", lastThought: null, tokensUsed: 0, latencyMs: null, error: null },
  creative_agent: { name: "creative_agent", displayName: "Creative Strategy", status: "idle", lastThought: null, tokensUsed: 0, latencyMs: null, error: null },
  scoring_agent: { name: "scoring_agent", displayName: "Evaluation Engine", status: "idle", lastThought: null, tokensUsed: 0, latencyMs: null, error: null },
  supervisor: { name: "supervisor", displayName: "Supervisor Synthesis", status: "idle", lastThought: null, tokensUsed: 0, latencyMs: null, error: null },
};

export const usePipelineStore = create<PipelineState>((set) => ({
  runId: null,
  brief: null,
  agents: INITIAL_AGENTS,
  events: [],
  pipelineStatus: "idle",
  pipelineThought: null,
  result: null,
  isStreaming: false,

  startRun: (runId, brief) =>
    set({
      runId,
      brief,
      agents: JSON.parse(JSON.stringify(INITIAL_AGENTS)),
      events: [],
      pipelineStatus: "running",
      pipelineThought: "Initializing pipeline...",
      result: null,
      isStreaming: true,
    }),

  pushEvent: (event) =>
    set((state) => {
      const newEvents = [...state.events, event];
      // Pipeline-level events
      if (event.agent_name === "__pipeline__") {
        return {
          events: newEvents,
          pipelineStatus: event.status,
          pipelineThought: event.thought || state.pipelineThought,
          isStreaming: !(event.status === "completed" || event.status === "failed"),
        };
      }
      // Agent-level events
      const existing = state.agents[event.agent_name];
      if (!existing) return { events: newEvents };
      const updated: AgentState = {
        ...existing,
        status: event.status,
        lastThought: event.thought || existing.lastThought,
        tokensUsed: event.tokens_used ?? existing.tokensUsed,
        latencyMs: event.latency_ms ?? existing.latencyMs,
        error: event.error || existing.error,
      };
      return {
        events: newEvents,
        agents: { ...state.agents, [event.agent_name]: updated },
      };
    }),

  setResult: (result) => set({ result }),

  reset: () => set({
    runId: null,
    brief: null,
    agents: JSON.parse(JSON.stringify(INITIAL_AGENTS)),
    events: [],
    pipelineStatus: "idle",
    pipelineThought: null,
    result: null,
    isStreaming: false,
  }),
}));
