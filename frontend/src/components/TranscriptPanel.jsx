import React from 'react';
import { MessageCircle, Sparkles } from 'lucide-react';

export function TranscriptPanel({ messages }) {
  const lastUser = [...messages].reverse().find((message) => message.role === 'user');
  const lastAssistant = [...messages].reverse().find((message) => message.role === 'assistant');

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Panel title="Transcript" icon={MessageCircle} empty="No patient transcript yet. Run a scenario or start a voice turn.">
        {lastUser ? <p className="text-base leading-7 text-white">{lastUser.content}</p> : null}
      </Panel>
      <Panel title="AI response" icon={Sparkles} empty="MedVoice response will appear here after processing.">
        {lastAssistant ? <p className="text-base leading-7 text-white">{lastAssistant.content}</p> : null}
      </Panel>
    </div>
  );
}

function Panel({ title, icon: Icon, empty, children }) {
  const hasContent = Boolean(children);
  return (
    <section className="glass-card p-5">
      <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-200">
        <Icon className="h-4 w-4 text-cyan-200" aria-hidden="true" />
        {title}
      </div>
      <div className="min-h-[132px] rounded-2xl border border-white/10 bg-slate-950/45 p-4">
        {hasContent ? children : <p className="text-sm leading-6 text-slate-400">{empty}</p>}
      </div>
    </section>
  );
}
