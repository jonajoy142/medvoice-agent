import React from 'react';
import { Mic, Radio, Volume2 } from 'lucide-react';

const stageCopy = {
  idle: { label: 'Ready', icon: Radio },
  listening: { label: 'Listening', icon: Mic },
  transcribing: { label: 'Transcribing', icon: Radio },
  thinking: { label: 'Thinking', icon: Radio },
  speaking: { label: 'Speaking', icon: Volume2 },
};

export function VoiceOrb({ stage = 'idle', partialTranscript, onStart, onStop, isBusy, speakCancelled }) {
  const active = stage !== 'idle';
  const Icon = stageCopy[stage]?.icon || Radio;

  return (
    <section className="glass-card relative overflow-hidden p-5 sm:p-6">
      <div className="flex flex-col gap-6 xl:flex-row xl:items-center">
        <div className="flex flex-1 flex-col items-center gap-5 text-center">
          <div className={`voice-orb ${active ? 'voice-orb-active' : ''}`} aria-label={`Voice state: ${stage}`}>
            <div className="voice-orb-core">
              <Icon className="h-10 w-10 text-white" aria-hidden="true" />
            </div>
          </div>
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-cyan-200">{stageCopy[stage]?.label || stage}</p>
            <p className="mt-2 min-h-[24px] text-sm text-slate-300">{partialTranscript || 'System ready for the next patient turn.'}</p>
            {speakCancelled ? <p className="mt-2 text-xs text-amber-200">Speaking cancelled by operator</p> : null}
          </div>
        </div>

        <div className="flex flex-1 flex-col gap-4">
          <div className="grid grid-cols-5 gap-2" aria-label="Voice pipeline status">
            {['idle', 'listening', 'transcribing', 'thinking', 'speaking'].map((item) => (
              <div key={item} className={`stage-chip ${stage === item ? 'stage-chip-active' : ''}`}>
                {item}
              </div>
            ))}
          </div>
          <div className="waveform" aria-hidden="true">
            {Array.from({ length: 28 }).map((_, index) => (
              <span key={index} style={{ animationDelay: `${index * 55}ms` }} className={active ? 'wavebar-active' : ''} />
            ))}
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <button type="button" onClick={onStart} disabled={isBusy} className="primary-action">
              {isBusy ? 'Processing turn' : 'Start voice turn'}
            </button>
            <button type="button" onClick={onStop} className="secondary-action">
              Stop speaking
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
