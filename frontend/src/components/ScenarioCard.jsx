import React from 'react';

export function ScenarioCard({ title, description, icon: Icon, onClick, disabled, tone = 'cyan' }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="group rounded-2xl border border-white/10 bg-white/[0.045] p-4 text-left transition hover:-translate-y-0.5 hover:border-cyan-300/35 hover:bg-white/[0.075] disabled:cursor-not-allowed disabled:opacity-50"
    >
      <div className="flex items-start gap-3">
        <span className={`scenario-icon scenario-icon-${tone}`}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
        <span>
          <span className="block text-sm font-semibold text-white">{title}</span>
          <span className="mt-1 block text-xs leading-5 text-slate-400">{description}</span>
        </span>
      </div>
    </button>
  );
}
