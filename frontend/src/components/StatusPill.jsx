import React from 'react';

const toneClasses = {
  online: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-100',
  warn: 'border-amber-400/30 bg-amber-400/10 text-amber-100',
  info: 'border-sky-400/30 bg-sky-400/10 text-sky-100',
  muted: 'border-slate-500/30 bg-white/[0.04] text-slate-200',
  danger: 'border-rose-400/30 bg-rose-400/10 text-rose-100',
};

export function StatusPill({ label, value, tone = 'muted', icon: Icon }) {
  return (
    <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs shadow-sm ${toneClasses[tone] || toneClasses.muted}`}>
      {Icon ? <Icon className="h-3.5 w-3.5" aria-hidden="true" /> : null}
      <span className="text-slate-400">{label}</span>
      <span className="font-semibold tracking-wide text-current">{value}</span>
    </div>
  );
}

export function StateBadge({ label, value }) {
  return <StatusPill label={label} value={value} tone="muted" />;
}
