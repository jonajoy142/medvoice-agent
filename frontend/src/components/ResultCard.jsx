import React from 'react';
import { CalendarCheck, ClipboardCheck, ShieldAlert, Stethoscope } from 'lucide-react';

const resultMeta = {
  appointment_booked: { title: 'Appointment confirmation', icon: CalendarCheck, tone: 'emerald' },
  request_opid: { title: 'Patient verification needed', icon: ClipboardCheck, tone: 'amber' },
  request_patient_verification: { title: 'Patient chart verification', icon: ShieldAlert, tone: 'amber' },
  availability_info: { title: 'Doctor availability', icon: Stethoscope, tone: 'cyan' },
  patient_found: { title: 'Verified patient record', icon: ClipboardCheck, tone: 'emerald' },
  faq_answer: { title: 'Hospital FAQ', icon: ClipboardCheck, tone: 'cyan' },
  emergency_escalation: { title: 'Emergency escalation', icon: ShieldAlert, tone: 'rose' },
};

export function ResultCard({ result }) {
  const action = result?.action || 'empty';
  const meta = resultMeta[action] || { title: 'Structured result', icon: ClipboardCheck, tone: 'slate' };
  const Icon = meta.icon;
  const hasResult = Boolean(result?.response || result?.display_response || result?.structured_data);

  return (
    <section className="glass-card p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className={`result-icon result-icon-${meta.tone}`}>
            <Icon className="h-5 w-5" aria-hidden="true" />
          </span>
          <div>
            <h2 className="text-sm font-semibold text-white">{meta.title}</h2>
            <p className="text-xs text-slate-400">{result?.intent || 'Waiting for a workflow result'}</p>
          </div>
        </div>
        <span className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-xs text-slate-300">{action}</span>
      </div>

      {hasResult ? (
        <div className="space-y-4">
          <p className="rounded-2xl border border-white/10 bg-slate-950/45 p-4 text-sm leading-6 text-slate-100">
            {result.display_response || result.response}
          </p>
          <pre className="max-h-56 overflow-auto rounded-2xl border border-white/10 bg-slate-950/60 p-4 text-xs leading-5 text-cyan-100/90">
            {JSON.stringify(result.structured_data || result.data || {}, null, 2)}
          </pre>
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-white/15 bg-slate-950/35 p-5 text-sm leading-6 text-slate-400">
          Appointment, availability, patient verification, and safety outputs will appear here.
        </div>
      )}
    </section>
  );
}
