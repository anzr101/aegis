"use client";
import { useState } from "react";
import { CampaignBrief } from "@/lib/api";
import { Sparkles } from "lucide-react";

interface Props {
  onSubmit: (brief: CampaignBrief) => void;
  disabled?: boolean;
}

const PRESETS: { label: string; brief: CampaignBrief }[] = [
  {
    label: "Ezor — modeling agency",
    brief: {
      brand: "Ezor",
      industry: "Marketing & Modeling Agency",
      product_or_service: "Talent management and brand campaign services for emerging Indian models",
      campaign_goal: "Position Ezor as the most ambitious modeling agency in India for Gen Z talent and drive 200+ inbound model applications in 30 days",
      target_audience: "Aspiring Indian models aged 18-26, urban metros, fashion-conscious, active on Instagram",
      budget_tier: "moderate",
      geographic_focus: "India",
      extra_context: "Agency is mid-size, building brand authority. Differentiator: AI-driven model-brand matching.",
    },
  },
  {
    label: "Indie SaaS launch",
    brief: {
      brand: "Notch",
      industry: "Productivity SaaS",
      product_or_service: "AI-powered note-taking app that auto-organizes thoughts into a knowledge graph",
      campaign_goal: "Drive 5,000 free trial signups in the first month after launch",
      target_audience: "Knowledge workers, students, researchers — heavy note-takers frustrated with existing tools",
      budget_tier: "lean",
      geographic_focus: "Global, English-speaking",
      extra_context: "Launching on Product Hunt. Strong Twitter/X presence as primary acquisition channel.",
    },
  },
];

export default function BriefForm({ onSubmit, disabled }: Props) {
  const [brief, setBrief] = useState<CampaignBrief>({
    brand: "",
    industry: "",
    product_or_service: "",
    campaign_goal: "",
    target_audience: "",
    budget_tier: "moderate",
    geographic_focus: "India",
    extra_context: "",
  });

  const update = <K extends keyof CampaignBrief>(k: K, v: CampaignBrief[K]) =>
    setBrief((b) => ({ ...b, [k]: v }));

  const isValid =
    brief.brand && brief.industry && brief.product_or_service && brief.campaign_goal && brief.target_audience;

  return (
    <div className="panel-padded animate-fade-in">
      <div className="flex items-center justify-between mb-5">
        <div>
          <p className="label-eyebrow mb-1">Stage 0 · Brief Intake</p>
          <h2 className="text-lg font-medium">Campaign brief</h2>
        </div>
        <div className="flex gap-2">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              onClick={() => setBrief(p.brief)}
              className="text-xs px-3 py-1.5 border border-border-default rounded-md text-text-secondary hover:bg-bg-tertiary transition-colors"
              disabled={disabled}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Brand">
          <input className="input-field" value={brief.brand} onChange={(e) => update("brand", e.target.value)} placeholder="Ezor" disabled={disabled} />
        </Field>
        <Field label="Industry">
          <input className="input-field" value={brief.industry} onChange={(e) => update("industry", e.target.value)} placeholder="Marketing & Modeling Agency" disabled={disabled} />
        </Field>

        <Field label="Product or service" full>
          <input className="input-field" value={brief.product_or_service} onChange={(e) => update("product_or_service", e.target.value)} placeholder="Talent management and brand campaign services" disabled={disabled} />
        </Field>

        <Field label="Campaign goal" full>
          <textarea className="input-field min-h-[72px]" value={brief.campaign_goal} onChange={(e) => update("campaign_goal", e.target.value)} placeholder="What outcome should this campaign drive?" disabled={disabled} />
        </Field>

        <Field label="Target audience" full>
          <textarea className="input-field min-h-[72px]" value={brief.target_audience} onChange={(e) => update("target_audience", e.target.value)} placeholder="Describe the audience as specifically as possible" disabled={disabled} />
        </Field>

        <Field label="Budget tier">
          <select className="input-field" value={brief.budget_tier} onChange={(e) => update("budget_tier", e.target.value as any)} disabled={disabled}>
            <option value="lean">Lean</option>
            <option value="moderate">Moderate</option>
            <option value="premium">Premium</option>
            <option value="enterprise">Enterprise</option>
          </select>
        </Field>

        <Field label="Geographic focus">
          <input className="input-field" value={brief.geographic_focus} onChange={(e) => update("geographic_focus", e.target.value)} disabled={disabled} />
        </Field>

        <Field label="Extra context (optional)" full>
          <textarea className="input-field min-h-[60px]" value={brief.extra_context || ""} onChange={(e) => update("extra_context", e.target.value)} placeholder="Anything else worth knowing?" disabled={disabled} />
        </Field>
      </div>

      <button
        onClick={() => isValid && onSubmit(brief)}
        disabled={!isValid || disabled}
        className="btn-primary mt-6 flex items-center gap-2 w-full justify-center"
      >
        <Sparkles size={16} />
        Initialize pipeline
      </button>
    </div>
  );
}

function Field({ label, full, children }: { label: string; full?: boolean; children: React.ReactNode }) {
  return (
    <div className={full ? "col-span-2" : ""}>
      <label className="text-xs text-text-secondary mb-1.5 block">{label}</label>
      {children}
    </div>
  );
}
