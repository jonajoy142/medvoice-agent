import React from 'react';
import { Headphones, PlayCircle, Settings2 } from 'lucide-react';
import { LANGUAGES, VOICE_PERSONAS, VOICE_PROVIDERS } from '../config/voicePersonas';

export function VoiceSettingsPanel({
  voiceProvider,
  setVoiceProvider,
  personaId,
  setPersonaId,
  language,
  setLanguage,
  voiceType,
  setVoiceType,
  llmProvider,
  onPreview,
  disabled,
}) {
  return (
    <section className="glass-card p-5">
      <div className="mb-4 flex items-center gap-2">
        <Settings2 className="h-4 w-4 text-cyan-200" aria-hidden="true" />
        <h2 className="text-sm font-semibold text-white">Voice settings</h2>
      </div>
      <div className="space-y-4">
        <SelectRow label="Voice provider" value={voiceProvider} onChange={setVoiceProvider} options={VOICE_PROVIDERS} />
        <SelectRow label="Language" value={language} onChange={setLanguage} options={LANGUAGES} />
        <SelectRow label="Voice persona" value={personaId} onChange={setPersonaId} options={VOICE_PERSONAS} />
        <SelectRow
          label="Voice type"
          value={voiceType}
          onChange={setVoiceType}
          options={[
            { id: 'female', label: 'Female' },
            { id: 'male', label: 'Male' },
          ]}
        />
      </div>

      <div className="mt-5 rounded-2xl border border-white/10 bg-slate-950/45 p-4">
        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-slate-500">
          <Headphones className="h-4 w-4" aria-hidden="true" />
          LLM provider
        </div>
        <p className="mt-2 text-sm font-semibold text-white">{(llmProvider?.active || llmProvider?.requested || 'deterministic').toUpperCase()}</p>
        <p className="mt-1 text-xs leading-5 text-slate-400">Used only for safe phrasing on generic turns. Clinical workflows stay deterministic.</p>
      </div>

      <button type="button" onClick={onPreview} disabled={disabled} className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-cyan-300/25 bg-cyan-300/10 px-4 py-3 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-300/15 disabled:opacity-50">
        <PlayCircle className="h-4 w-4" aria-hidden="true" />
        Preview voice persona
      </button>
    </section>
  );
}

function SelectRow({ label, value, onChange, options }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-400">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2.5 text-sm text-slate-100 outline-none transition focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-300/10">
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
