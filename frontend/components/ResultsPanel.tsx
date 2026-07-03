"use client";
import { motion } from "framer-motion";
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer } from "recharts";
import { Trophy, AlertTriangle, ArrowRight, Target, Shield, Zap } from "lucide-react";

interface Props {
  result: any;
}

export default function ResultsPanel({ result }: Props) {
  if (!result) return null;

  const finalBrief = result.final_brief;
  const evaluation = result.evaluation;
  const trend = result.trend_intelligence;
  const audience = result.audience_psychology;
  const creative = result.creative_strategy;

  if (!finalBrief && !creative) {
    return (
      <div className="panel-padded">
        <p className="text-text-secondary">Pipeline failed to produce a final brief. Check the reasoning stream above for details.</p>
      </div>
    );
  }

  const recommendedConcept = creative?.campaigns?.find(
    (c: any) => c.title === finalBrief?.recommended_concept
  ) || creative?.campaigns?.[0];

  const recommendedEval = evaluation?.evaluations?.find(
    (e: any) => e.concept_title === recommendedConcept?.title
  );

  const radarData = recommendedEval ? Object.entries(recommendedEval.scores).map(([k, v]) => ({
    metric: k.replace(/_/g, " "),
    score: v as number,
  })) : [];

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      {/* Executive summary */}
      {finalBrief && (
        <div className="panel-padded">
          <div className="flex items-center gap-2 mb-3">
            <Trophy size={16} className="text-accent-success" />
            <p className="label-eyebrow text-accent-success">Final Synthesis</p>
            {typeof finalBrief.confidence_estimate === "number" && (
              <span className="ml-auto text-xs font-mono text-text-secondary">
                Confidence: {(finalBrief.confidence_estimate * 100).toFixed(0)}%
              </span>
            )}
          </div>
          <h2 className="text-2xl font-medium mb-2">{finalBrief.recommended_concept}</h2>
          <p className="text-text-secondary leading-relaxed mb-4">{finalBrief.executive_summary}</p>

          <div className="grid grid-cols-2 gap-4 mt-4">
            <div>
              <p className="label-eyebrow mb-2">Rationale</p>
              <p className="text-sm text-text-secondary leading-relaxed">{finalBrief.rationale}</p>
            </div>
            <div>
              <p className="label-eyebrow mb-2">Success Metrics</p>
              <ul className="text-sm space-y-1.5">
                {finalBrief.success_metrics?.map((m: string, i: number) => (
                  <li key={i} className="flex gap-2 text-text-secondary">
                    <Target size={12} className="text-accent-primary mt-0.5 flex-shrink-0" />
                    <span>{m}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Two-column: radar + concept details */}
      <div className="grid grid-cols-2 gap-4">
        {radarData.length > 0 && (
          <div className="panel-padded">
            <p className="label-eyebrow mb-3">Concept Scoring · 8 Dimensions</p>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#1E2841" />
                  <PolarAngleAxis dataKey="metric" tick={{ fill: "#9AA5BD", fontSize: 10 }} />
                  <PolarRadiusAxis domain={[0, 10]} tick={{ fill: "#6B7793", fontSize: 9 }} />
                  <Radar
                    name="Score"
                    dataKey="score"
                    stroke="#5B8DEF"
                    fill="#5B8DEF"
                    fillOpacity={0.3}
                    strokeWidth={2}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            {recommendedEval && (
              <div className="mt-2 text-center">
                <span className="text-xs text-text-secondary">Final score: </span>
                <span className="text-lg font-mono text-accent-success font-medium">
                  {recommendedEval.final_score.toFixed(1)}/10
                </span>
              </div>
            )}
          </div>
        )}

        {recommendedConcept && (
          <div className="panel-padded">
            <p className="label-eyebrow mb-3">Recommended Concept Details</p>
            <h3 className="text-lg font-medium mb-2">{recommendedConcept.title}</h3>
            <p className="text-sm text-text-secondary mb-3">{recommendedConcept.core_mechanism}</p>

            <div className="space-y-2 text-xs">
              <DetailRow label="Platform" value={recommendedConcept.platform_strategy?.primary_platform} />
              <DetailRow label="Aesthetic" value={recommendedConcept.visual_language?.aesthetic} />
              <DetailRow label="Emotion" value={recommendedConcept.emotional_arc?.dominant_emotion} />
              <DetailRow label="Virality" value={recommendedConcept.virality_mechanism?.type} />
            </div>
          </div>
        )}
      </div>

      {/* Multi-modal content examples */}
      {recommendedConcept && (
        <div className="panel-padded">
          <p className="label-eyebrow mb-4">Multi-Modal Content Direction</p>
          <div className="grid grid-cols-2 gap-3">
            <ContentBlock label="Reel Concept" content={recommendedConcept.reel_concept} />
            <ContentBlock label="Meme Format" content={recommendedConcept.meme_format} />
            <ContentBlock label="Carousel Structure" content={recommendedConcept.carousel_structure} />
            <ContentBlock label="Cinematic Ad" content={recommendedConcept.cinematic_ad_idea} />
            <ContentBlock label="Influencer Strategy" content={recommendedConcept.influencer_strategy} />
            <ContentBlock label="UGC Strategy" content={recommendedConcept.ugc_strategy} />
          </div>
        </div>
      )}

      {/* Conflicts & weak evidence */}
      {finalBrief && (finalBrief.cross_agent_conflicts?.length > 0 || finalBrief.weak_evidence_flags?.length > 0) && (
        <div className="panel-padded border-accent-warning/30">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle size={14} className="text-accent-warning" />
            <p className="label-eyebrow text-accent-warning">Cross-Agent Reasoning · Conflicts & Caveats</p>
          </div>

          {finalBrief.cross_agent_conflicts?.length > 0 && (
            <div className="mb-4">
              <p className="text-xs text-text-secondary mb-2 font-medium">Detected conflicts</p>
              <div className="space-y-2">
                {finalBrief.cross_agent_conflicts.map((c: any, i: number) => (
                  <div key={i} className="bg-bg-tertiary rounded p-3 text-xs">
                    <div className="flex gap-2 mb-1.5">
                      {c.agents_involved?.map((a: string) => (
                        <span key={a} className="px-1.5 py-0.5 bg-accent-warning/10 text-accent-warning rounded font-mono text-[10px]">
                          {a}
                        </span>
                      ))}
                    </div>
                    <p className="text-text-primary mb-1">{c.nature_of_conflict}</p>
                    <p className="text-text-secondary"><strong className="text-text-primary">Resolved:</strong> {c.resolution}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {finalBrief.weak_evidence_flags?.length > 0 && (
            <div>
              <p className="text-xs text-text-secondary mb-2 font-medium">Weak evidence flags</p>
              <ul className="space-y-1">
                {finalBrief.weak_evidence_flags.map((f: string, i: number) => (
                  <li key={i} className="text-xs text-text-secondary flex gap-2">
                    <Shield size={11} className="text-accent-warning mt-0.5 flex-shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Next actions */}
      {finalBrief?.next_actions?.length > 0 && (
        <div className="panel-padded">
          <div className="flex items-center gap-2 mb-3">
            <Zap size={14} className="text-accent-primary" />
            <p className="label-eyebrow">Next Actions</p>
          </div>
          <ol className="space-y-2">
            {finalBrief.next_actions.map((a: string, i: number) => (
              <li key={i} className="flex gap-3 text-sm">
                <span className="font-mono text-xs text-accent-primary mt-0.5">{String(i + 1).padStart(2, "0")}</span>
                <span className="text-text-secondary">{a}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Self-critique */}
      {recommendedEval?.self_critique && (
        <div className="panel-padded">
          <p className="label-eyebrow mb-3">Self-Critique · Evaluation Engine</p>
          <div className="grid grid-cols-3 gap-4 text-xs">
            <CritiqueColumn title="Weaknesses" items={recommendedEval.self_critique.weaknesses} />
            <CritiqueColumn title="Failure Risks" items={recommendedEval.self_critique.failure_risks} />
            <CritiqueColumn title="Improvements" items={recommendedEval.self_critique.possible_improvements} />
          </div>
        </div>
      )}

      {/* Run metadata */}
      <div className="flex items-center justify-end gap-6 pt-2 text-xs text-text-muted font-mono">
        <span>tokens: {result.total_tokens?.toLocaleString()}</span>
        <span>latency: {((result.total_latency_ms || 0) / 1000).toFixed(1)}s</span>
        <span>run: {result.run_id?.slice(0, 8)}</span>
      </div>
    </motion.div>
  );
}

function DetailRow({ label, value }: { label: string; value?: string }) {
  if (!value) return null;
  return (
    <div className="flex gap-3">
      <span className="text-text-muted w-20 flex-shrink-0">{label}</span>
      <span className="text-text-secondary">{value}</span>
    </div>
  );
}

function ContentBlock({ label, content }: { label: string; content?: string }) {
  if (!content) return null;
  return (
    <div className="bg-bg-tertiary rounded p-3">
      <p className="text-[10px] uppercase tracking-wider text-accent-primary mb-1.5 font-medium">{label}</p>
      <p className="text-xs text-text-secondary leading-relaxed">{content}</p>
    </div>
  );
}

function CritiqueColumn({ title, items }: { title: string; items?: string[] }) {
  return (
    <div>
      <p className="text-text-primary mb-2 font-medium">{title}</p>
      <ul className="space-y-1.5">
        {items?.map((item, i) => (
          <li key={i} className="text-text-secondary leading-relaxed">• {item}</li>
        ))}
      </ul>
    </div>
  );
}
