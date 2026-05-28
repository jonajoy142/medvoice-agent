import React from 'react';
import { ArrowRight, CheckCircle2, Container, DatabaseZap, ShieldCheck } from 'lucide-react';

const pipeline = ['STT', 'Intent', 'Guardrails', 'LLM', 'TTS'];

export function PipelineCard({ currentStage }) {
  return (
    <section className="glass-card p-5">
      <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Why this is production-ready</h2>
          <p className="mt-1 text-sm text-slate-400">Deployment split, deterministic healthcare flows, and provider fallback built in.</p>
        </div>
        <span className="w-fit rounded-full border border-emerald-300/25 bg-emerald-300/10 px-3 py-1 text-xs font-semibold text-emerald-100">Recruiter demo ready</span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {pipeline.map((step, index) => (
          <React.Fragment key={step}>
            <div className={`pipeline-step ${isPipelineActive(step, currentStage) ? 'pipeline-step-active' : ''}`}>{step}</div>
            {index < pipeline.length - 1 ? <ArrowRight className="h-4 w-4 text-slate-600" aria-hidden="true" /> : null}
          </React.Fragment>
        ))}
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <ReadinessBadge icon={Container} title="Container backend" text="FastAPI Dockerfile and root Compose Postgres." />
        <ReadinessBadge icon={DatabaseZap} title="Supabase-ready" text="Postgres URL swap with Alembic migrations." />
        <ReadinessBadge icon={ShieldCheck} title="Safety-first" text="Patient records stay behind verification." />
      </div>
    </section>
  );
}

function ReadinessBadge({ icon: Icon, title, text }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-950/45 p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-white">
        <Icon className="h-4 w-4 text-emerald-200" aria-hidden="true" />
        {title}
      </div>
      <p className="mt-2 text-xs leading-5 text-slate-400">{text}</p>
    </div>
  );
}

function isPipelineActive(step, stage) {
  if (stage === 'listening') return step === 'STT';
  if (stage === 'transcribing') return step === 'STT';
  if (stage === 'thinking') return ['Intent', 'Guardrails', 'LLM'].includes(step);
  if (stage === 'speaking') return step === 'TTS';
  return false;
}
