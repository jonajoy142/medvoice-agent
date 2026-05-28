import React from 'react';

export function LatencyCard({ label, value, accent = 'cyan' }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.045] p-4">
      <p className="text-xs font-medium uppercase tracking-[0.2em] text-slate-500">{label}</p>
      <p className={`mt-2 text-2xl font-semibold ${accent === 'emerald' ? 'text-emerald-200' : 'text-cyan-200'}`}>{value}</p>
    </div>
  );
}
