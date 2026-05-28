import React from 'react';
import { LockKeyhole, ShieldCheck, Siren, UserCheck } from 'lucide-react';

const guardrails = [
  { label: 'Verified patient identity before chart lookup', icon: UserCheck },
  { label: 'No hallucinated patient records', icon: LockKeyhole },
  { label: 'Emergency phrases escalate immediately', icon: Siren },
  { label: 'Deterministic fallback when LLM is offline', icon: ShieldCheck },
];

export function GuardrailPanel({ result }) {
  return (
    <section className="glass-card p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-white">Guardrail and safety layer</h2>
          <p className="mt-1 text-xs text-slate-400">Healthcare workflows are deterministic first.</p>
        </div>
        <span className="rounded-full border border-emerald-300/25 bg-emerald-300/10 px-3 py-1 text-xs font-semibold text-emerald-100">
          {(result?.guardrail_status || 'active').toUpperCase()}
        </span>
      </div>
      <div className="grid gap-3">
        {guardrails.map(({ label, icon: Icon }) => (
          <div key={label} className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.035] p-3">
            <Icon className="h-4 w-4 text-emerald-200" aria-hidden="true" />
            <p className="text-sm text-slate-200">{label}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
