import React from 'react';
import { Brain, Database, Mic2, RefreshCw, Server, ShieldCheck, Stethoscope } from 'lucide-react';
import { StatusPill } from './StatusPill';

export function DashboardLayout({ health, onRefreshHealth, children }) {
  const llm = health?.llm_provider || {};
  const dbConnected = Boolean(health?.database_connected);
  const voiceProvider = health?.provider_active || health?.provider_requested || 'local';

  return (
    <div className="min-h-screen overflow-hidden bg-slate-950 text-slate-100">
      <div className="fixed inset-0 -z-10 bg-[radial-gradient(circle_at_20%_10%,rgba(14,165,233,0.22),transparent_34%),radial-gradient(circle_at_85%_18%,rgba(16,185,129,0.18),transparent_28%),linear-gradient(135deg,#020617_0%,#07111f_45%,#031315_100%)]" />
      <header className="border-b border-white/10 bg-slate-950/72 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-cyan-300/25 bg-cyan-300/10 shadow-[0_0_40px_rgba(34,211,238,0.22)]">
                <Stethoscope className="h-6 w-6 text-cyan-200" aria-hidden="true" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-emerald-200/80">MedVoice</p>
                <h1 className="text-2xl font-semibold text-white sm:text-3xl">AI Hospital Voice Receptionist</h1>
              </div>
            </div>
            <button
              type="button"
              onClick={onRefreshHealth}
              className="inline-flex w-fit items-center gap-2 rounded-full border border-white/10 bg-white/[0.06] px-4 py-2 text-sm text-slate-200 transition hover:border-cyan-300/40 hover:bg-cyan-300/10"
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              Refresh health
            </button>
          </div>

          <div className="flex flex-wrap gap-2">
            <StatusPill label="Backend" value={health?.status || 'checking'} tone={health?.status === 'healthy' ? 'online' : 'warn'} icon={Server} />
            <StatusPill label="DB" value={dbConnected ? 'POSTGRES' : 'MOCK'} tone={dbConnected ? 'online' : 'warn'} icon={Database} />
            <StatusPill label="LLM" value={(llm.active || llm.requested || 'deterministic').toUpperCase()} tone={llm.active === 'deterministic' ? 'info' : 'online'} icon={Brain} />
            <StatusPill label="Voice" value={voiceProvider.toUpperCase()} tone="info" icon={Mic2} />
            <StatusPill label="Guardrails" value="ACTIVE" tone="online" icon={ShieldCheck} />
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl grid-cols-1 gap-5 px-4 py-6 sm:px-6 lg:grid-cols-12 lg:px-8">
        {children}
      </main>
    </div>
  );
}
