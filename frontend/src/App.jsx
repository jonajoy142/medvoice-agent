import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Activity, AlertTriangle, Calendar, Database, Mic, Shield, Stethoscope, Volume2 } from 'lucide-react';
import { getHealth, processVoice, runDemoScenario } from './services/api';
import { LANGUAGES, VOICE_PERSONAS, VOICE_PROVIDERS } from './config/voicePersonas';
import { StateBadge } from './components/StateBadge';

const DEMO_SCENARIOS = [
  { id: 'book_cardiology_appointment', label: 'Book Cardiology' },
  { id: 'doctor_availability', label: 'Doctor Availability' },
  { id: 'verified_patient_lookup', label: 'Verified Patient Lookup' },
  { id: 'visiting_hours_faq', label: 'Visiting Hours FAQ' },
  { id: 'emergency_escalation', label: 'Emergency Escalation' },
  { id: 'hindi_english_appointment', label: 'Hindi-English Booking' },
  { id: 'voice_persona_preview', label: 'Persona Preview' },
  { id: 'database_provider_fallback', label: 'Provider Fallback Demo' },
];

const WORKFLOW_STAGES = ['idle', 'listening', 'transcribing', 'thinking', 'speaking'];

function App() {
  const [sessionId, setSessionId] = useState(`session_${Date.now()}`);
  const [workflowStage, setWorkflowStage] = useState('idle');
  const [messages, setMessages] = useState([]);
  const [partialTranscript, setPartialTranscript] = useState('');
  const [isBusy, setIsBusy] = useState(false);
  const [health, setHealth] = useState({ database_connected: false, provider_active: 'local' });
  const [voiceType, setVoiceType] = useState('female');
  const [voiceProvider, setVoiceProvider] = useState('local');
  const [personaId, setPersonaId] = useState('female_warm_indian');
  const [language, setLanguage] = useState('en-IN');
  const [lastResult, setLastResult] = useState({});
  const [speakCancelled, setSpeakCancelled] = useState(false);
  const timelineRef = useRef(null);

  useEffect(() => {
    refreshHealth();
  }, []);

  useEffect(() => {
    timelineRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, partialTranscript]);

  async function refreshHealth() {
    try {
      const data = await getHealth();
      setHealth(data);
      if (data.provider_requested) {
        setVoiceProvider(data.provider_requested);
      }
    } catch (error) {
      console.error(error);
    }
  }

  async function handleVoiceCapture() {
    if (isBusy) return;
    setIsBusy(true);
    setSpeakCancelled(false);
    setWorkflowStage('listening');
    setPartialTranscript('Listening to patient voice...');
    await wait(450);
    setWorkflowStage('transcribing');
    setPartialTranscript('Transcribing audio...');
    try {
      const result = await processVoice({
        session_id: sessionId,
        voice: voiceType,
        voice_provider: voiceProvider,
        persona_id: personaId,
        language,
      });
      handleResponse(result);
    } catch (error) {
      pushAssistant('I encountered an issue while processing voice. Please try again.');
    } finally {
      setPartialTranscript('');
      setIsBusy(false);
      setWorkflowStage('idle');
    }
  }

  async function runScenario(scenarioId) {
    if (isBusy) return;
    setIsBusy(true);
    setSpeakCancelled(false);
    setWorkflowStage('thinking');
    setPartialTranscript(`Running demo scenario: ${scenarioId}`);
    try {
      const result = await runDemoScenario({
        scenario: scenarioId,
        session_id: sessionId,
        voice_provider: voiceProvider,
        persona_id: personaId,
        language,
      });
      handleResponse(result);
    } catch (error) {
      pushAssistant('Demo scenario failed. Please retry.');
    } finally {
      setPartialTranscript('');
      setIsBusy(false);
      setWorkflowStage('idle');
    }
  }

  function handleResponse(result) {
    setWorkflowStage('thinking');
    if (result.user_input) pushUser(result.user_input);
    setWorkflowStage('speaking');
    pushAssistant(result.display_response || result.response || 'No response');
    setLastResult(result);
    setHealth((prev) => ({ ...prev, provider_active: result.provider || prev.provider_active }));
  }

  function pushUser(content) {
    setMessages((prev) => [...prev, { role: 'user', content, ts: new Date().toISOString() }]);
  }

  function pushAssistant(content) {
    setMessages((prev) => [...prev, { role: 'assistant', content, ts: new Date().toISOString() }]);
  }

  function stopSpeaking() {
    setSpeakCancelled(true);
    setWorkflowStage('idle');
  }

  const timings = lastResult.stage_timings || {};
  const trustIndicators = useMemo(
    () => [
      { label: 'Verified DB Only', value: health.database_connected ? 'Connected' : 'Mock Fallback' },
      { label: 'Guardrails', value: lastResult.guardrail_status || 'active' },
      { label: 'Provider Fallback', value: (lastResult.provider || health.provider_active || 'local').toUpperCase() },
      { label: 'PHI-safe Logging', value: 'Enabled' },
      { label: 'Emergency Escalation', value: 'Enabled' },
    ],
    [health, lastResult]
  );

  return (
    <div className="min-h-screen bg-dark-50 text-gray-100">
      <header className="border-b border-dark-200 bg-dark-100/90 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-primary-600 flex items-center justify-center"><Stethoscope className="w-6 h-6 text-white" /></div>
            <div>
              <h1 className="text-xl font-semibold">MedVoice Flagship Console</h1>
              <p className="text-xs text-gray-400">AI hospital receptionist platform</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={refreshHealth} className="px-3 py-2 rounded-lg bg-dark-200 text-sm">Refresh Health</button>
            <StateBadge label="Active Provider" value={(health.provider_active || 'local').toUpperCase()} />
            <StateBadge label="DB" value={health.database_connected ? 'POSTGRES' : 'MOCK'} />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-4 grid grid-cols-1 xl:grid-cols-4 gap-4">
        <aside className="xl:col-span-1 space-y-4">
          <section className="panel">
            <h2 className="panel-title"><Mic className="w-4 h-4" /> Voice Config</h2>
            <div className="space-y-2">
              <SelectRow label="Provider" value={voiceProvider} onChange={setVoiceProvider} options={VOICE_PROVIDERS} />
              <SelectRow label="Persona" value={personaId} onChange={setPersonaId} options={VOICE_PERSONAS} />
              <SelectRow label="Language" value={language} onChange={setLanguage} options={LANGUAGES} />
              <SelectRow
                label="Voice Type"
                value={voiceType}
                onChange={setVoiceType}
                options={[{ id: 'female', label: 'Female' }, { id: 'male', label: 'Male' }]}
              />
            </div>
          </section>
          <section className="panel">
            <h2 className="panel-title"><Shield className="w-4 h-4" /> Trust & Safety</h2>
            <div className="space-y-2">
              {trustIndicators.map((item) => <StateBadge key={item.label} label={item.label} value={item.value} />)}
            </div>
          </section>
          <section className="panel">
            <h2 className="panel-title"><Activity className="w-4 h-4" /> Demo Scenarios</h2>
            <div className="grid grid-cols-1 gap-2">
              {DEMO_SCENARIOS.map((s) => (
                <button key={s.id} onClick={() => runScenario(s.id)} className="scenario-btn" disabled={isBusy}>{s.label}</button>
              ))}
            </div>
          </section>
        </aside>

        <section className="xl:col-span-2 panel">
          <div className="flex items-center justify-between mb-3">
            <h2 className="panel-title"><Volume2 className="w-4 h-4" /> Realtime Voice Console</h2>
            <div className="status-pill">{workflowStage.toUpperCase()}</div>
          </div>
          <div className="wave-wrap mb-3">
            <div className={`wave ${workflowStage !== 'idle' ? 'active' : ''}`} />
            <p className="text-sm text-gray-300">{partialTranscript || 'System ready for next patient turn.'}</p>
          </div>
          <div className="flex items-center gap-3 mb-4">
            <button onClick={handleVoiceCapture} disabled={isBusy} className="mic-button">{isBusy ? 'Processing...' : 'Start Voice Turn'}</button>
            <button onClick={stopSpeaking} className="px-4 py-2 rounded-lg bg-dark-200 text-sm">Stop / Cancel Speaking</button>
            {speakCancelled && <span className="text-xs text-yellow-300">Speaking cancelled</span>}
          </div>

          <div className="grid grid-cols-5 gap-2 mb-4">
            {WORKFLOW_STAGES.map((s) => (
              <div key={s} className={`stage-chip ${workflowStage === s ? 'active' : ''}`}>{s}</div>
            ))}
          </div>

          <div className="timeline">
            {messages.length === 0 ? (
              <div className="text-sm text-gray-400 py-8 text-center">No interactions yet. Use microphone or demo scenarios.</div>
            ) : (
              messages.map((m, idx) => (
                <div key={`${m.ts}-${idx}`} className={`timeline-item ${m.role}`}>
                  <p className="text-xs opacity-70 mb-1">{m.role === 'user' ? 'Patient' : 'MedVoice AI'}</p>
                  <p>{m.content}</p>
                </div>
              ))
            )}
            <div ref={timelineRef} />
          </div>
        </section>

        <aside className="xl:col-span-1 space-y-4">
          <section className="panel">
            <h2 className="panel-title"><Database className="w-4 h-4" /> Latency & State</h2>
            <div className="space-y-2">
              <StateBadge label="Intent" value={lastResult.intent || '-'} />
              <StateBadge label="Confidence" value={lastResult.confidence ?? '-'} />
              <StateBadge label="STT" value={`${timings.stt_latency_ms || 0} ms`} />
              <StateBadge label="LLM" value={`${timings.llm_latency_ms || 0} ms`} />
              <StateBadge label="TTS" value={`${timings.tts_latency_ms || 0} ms`} />
              <StateBadge label="Total" value={`${timings.total_latency_ms || lastResult.latency_ms || 0} ms`} />
            </div>
          </section>
          <section className="panel">
            <h2 className="panel-title"><Calendar className="w-4 h-4" /> Structured Result</h2>
            <pre className="text-xs bg-dark-200 p-3 rounded-lg overflow-auto max-h-64">{JSON.stringify(lastResult.structured_data || {}, null, 2)}</pre>
          </section>
          <section className="panel">
            <h2 className="panel-title"><AlertTriangle className="w-4 h-4 text-yellow-300" /> Emergency Guidance</h2>
            <p className="text-sm text-gray-300">In emergency phrases, MedVoice escalates immediately and avoids diagnosis.</p>
          </section>
        </aside>
      </main>
    </div>
  );
}

function SelectRow({ label, value, onChange, options }) {
  return (
    <div>
      <label className="text-xs text-gray-400">{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)} className="input-select">
        {options.map((opt) => <option key={opt.id} value={opt.id}>{opt.label}</option>)}
      </select>
    </div>
  );
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export default App;
