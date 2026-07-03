// Frontend API client. Uses SSE for streaming agent events.

export type AgentStatus = "idle" | "running" | "completed" | "failed" | "retrying";

export interface AgentEvent {
  timestamp: string;
  agent_name: string;
  status: AgentStatus;
  thought?: string | null;
  tokens_used?: number | null;
  latency_ms?: number | null;
  error?: string | null;
}

export interface CampaignBrief {
  brand: string;
  industry: string;
  product_or_service: string;
  campaign_goal: string;
  target_audience: string;
  budget_tier?: "lean" | "moderate" | "premium" | "enterprise";
  geographic_focus?: string;
  extra_context?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api";

export async function startPipeline(brief: CampaignBrief): Promise<{ run_id: string }> {
  const res = await fetch(`${API_BASE}/pipeline/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(brief),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Pipeline start failed: ${err}`);
  }
  return res.json();
}

export async function getPipelineResult(runId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/pipeline/${runId}`);
  if (!res.ok) {
    if (res.status === 404) return null;
    throw new Error(`Pipeline fetch failed: ${res.statusText}`);
  }
  return res.json();
}

export async function getHistory(limit = 50): Promise<{ runs: any[] }> {
  const res = await fetch(`${API_BASE}/pipeline/history/list?limit=${limit}`);
  if (!res.ok) throw new Error("History fetch failed");
  return res.json();
}

/**
 * Subscribe to live agent events via Server-Sent Events.
 * Returns a cleanup function.
 */
export function subscribeToPipeline(
  runId: string,
  onEvent: (event: AgentEvent) => void,
  onComplete?: () => void,
  onError?: (e: Error) => void,
): () => void {
  const url = `${API_BASE}/pipeline/${runId}/stream`;
  const source = new EventSource(url);

  source.addEventListener("agent_event", (e: MessageEvent) => {
    try {
      const event: AgentEvent = JSON.parse(e.data);
      onEvent(event);
      if (
        event.agent_name === "__pipeline__" &&
        (event.status === "completed" || event.status === "failed")
      ) {
        source.close();
        onComplete?.();
      }
    } catch (err) {
      console.error("SSE parse error", err);
    }
  });

  source.onerror = (e) => {
    console.error("SSE error", e);
    source.close();
    onError?.(new Error("SSE connection error"));
  };

  return () => source.close();
}
