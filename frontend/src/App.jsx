import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  CalendarPlus,
  Clock3,
  HeartPulse,
  Languages,
  Search,
  ShieldAlert,
  Stethoscope,
} from 'lucide-react';
import { getHealth, processVoice, runDemoScenario } from './services/api';
import { DashboardLayout } from './components/DashboardLayout';
import { VoiceOrb } from './components/VoiceOrb';
import { TranscriptPanel } from './components/TranscriptPanel';
import { ScenarioCard } from './components/ScenarioCard';
import { ResultCard } from './components/ResultCard';
import { VoiceSettingsPanel } from './components/VoiceSettingsPanel';
import { GuardrailPanel } from './components/GuardrailPanel';
import { LatencyCard } from './components/LatencyCard';
import { PipelineCard } from './components/PipelineCard';
import { StatusPill } from './components/StatusPill';

const DEMO_SCENARIOS = [
  {
    id: 'book_cardiology_appointment',
    title: 'Book appointment',
    description: 'Cardiology request with verified OPID context.',
    icon: CalendarPlus,
    tone: 'emerald',
  },
  {
    id: 'doctor_availability',
    title: 'Doctor availability',
    description: 'Check dermatologist slots from verified data.',
    icon: Stethoscope,
    tone: 'cyan',
  },
  {
    id: 'verified_patient_lookup',
    title: 'Patient chart lookup',
    description: 'Lookup record only when an identifier is present.',
    icon: Search,
    tone: 'amber',
  },
  {
    id: 'visiting_hours_faq',
    title: 'Visiting hours FAQ',
    description: 'Static hospital FAQ without LLM dependency.',
    icon: Clock3,
    tone: 'cyan',
  },
  {
    id: 'emergency_escalation',
    title: 'Emergency escalation',
    description: 'Urgent symptoms trigger safe escalation.',
    icon: ShieldAlert,
    tone: 'rose',
  },
  {
    id: 'hindi_english_appointment',
    title: 'Hindi-English demo',
    description: 'Bilingual appointment flow with persona settings.',
    icon: Languages,
    tone: 'emerald',
  },
];

const emptyHealth = {
  status: 'checking',
  database_connected: false,
  provider_active: 'local',
  provider_requested: 'local',
  llm_provider: { active: 'deterministic', requested: 'deterministic', available: true },
};

function App() {
  const [sessionId] = useState(`session_${Date.now()}`);
  const [workflowStage, setWorkflowStage] = useState('idle');
  const [messages, setMessages] = useState([]);
  const [partialTranscript, setPartialTranscript] = useState('');
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState('');
  const [health, setHealth] = useState(emptyHealth);
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
    timelineRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, partialTranscript]);

  async function refreshHealth() {
    try {
      setError('');
      const data = await getHealth();
      setHealth({ ...emptyHealth, ...data });
      if (data.provider_requested) setVoiceProvider(data.provider_requested);
    } catch (caught) {
      setError('Backend health check failed. Start the FastAPI backend and try again.');
      setHealth((previous) => ({ ...previous, status: 'offline' }));
    }
  }

  async function handleVoiceCapture() {
    if (isBusy) return;
    setIsBusy(true);
    setError('');
    setSpeakCancelled(false);
    setWorkflowStage('listening');

    try {
      setPartialTranscript('Listening to patient voice...');
      const recording = await recordMicrophoneAudio(4500);
      setWorkflowStage('transcribing');
      setPartialTranscript('Transcribing audio...');

      const result = await processVoice({
        session_id: sessionId,
        audio: recording.blob,
        audioName: recording.fileName,
        voice: voiceType,
        voice_provider: voiceProvider,
        persona_id: personaId,
        language,
      });
      handleResponse(result);
    } catch (caught) {
      const permissionDenied = caught?.name === 'NotAllowedError' || caught?.name === 'SecurityError';
      setError(
        permissionDenied
          ? 'Microphone permission was denied. Allow microphone access in the browser and retry.'
          : 'Voice processing failed. Check microphone permissions and backend availability.'
      );
      pushAssistant('I could not process the voice turn. Please try again.');
    } finally {
      await wait(600);
      setPartialTranscript('');
      setIsBusy(false);
      setWorkflowStage('idle');
    }
  }

  async function runScenario(scenarioId) {
    if (isBusy) return;
    const scenario = DEMO_SCENARIOS.find((item) => item.id === scenarioId);
    setIsBusy(true);
    setError('');
    setSpeakCancelled(false);
    setWorkflowStage('thinking');
    setPartialTranscript(`Running ${scenario?.title || 'demo scenario'}...`);

    try {
      const result = await runDemoScenario({
        scenario: scenarioId,
        session_id: sessionId,
        voice_provider: voiceProvider,
        persona_id: personaId,
        language,
      });
      handleResponse(result);
    } catch (caught) {
      setError('Demo scenario failed. Confirm the backend is running.');
      pushAssistant('Demo scenario failed. Please retry.');
    } finally {
      await wait(650);
      setPartialTranscript('');
      setIsBusy(false);
      setWorkflowStage('idle');
    }
  }

  function handleResponse(result) {
    setWorkflowStage('thinking');
    if (result.user_input) pushUser(result.user_input);
    setLastResult(result);
    setHealth((previous) => ({ ...previous, provider_active: result.provider || previous.provider_active }));
    setWorkflowStage('speaking');
    pushAssistant(result.display_response || result.response || 'No response returned.');
  }

  function pushUser(content) {
    setMessages((previous) => [...previous, { role: 'user', content, ts: new Date().toISOString() }]);
  }

  function pushAssistant(content) {
    setMessages((previous) => [...previous, { role: 'assistant', content, ts: new Date().toISOString() }]);
  }

  function stopSpeaking() {
    setSpeakCancelled(true);
    setWorkflowStage('idle');
  }

  function previewPersona() {
    runScenario('voice_persona_preview');
  }

  const timings = lastResult.stage_timings || {};
  const latencyCards = useMemo(
    () => [
      { label: 'STT', value: `${timings.stt_latency_ms || 0} ms` },
      { label: 'LLM', value: `${timings.llm_latency_ms || 0} ms`, accent: 'emerald' },
      { label: 'TTS', value: `${timings.tts_latency_ms || 0} ms` },
      { label: 'Total', value: `${timings.total_latency_ms || lastResult.latency_ms || 0} ms`, accent: 'emerald' },
    ],
    [lastResult.latency_ms, timings.llm_latency_ms, timings.stt_latency_ms, timings.total_latency_ms, timings.tts_latency_ms]
  );

  return (
    <DashboardLayout health={health} onRefreshHealth={refreshHealth}>
      <section className="space-y-5 lg:col-span-8">
        <div className="glass-card p-5 sm:p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-emerald-200/80">Live command center</p>
              <h2 className="mt-2 max-w-3xl text-3xl font-semibold text-white sm:text-4xl">
                Patient calls, guarded workflows, and voice AI in one production-grade console.
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
                MedVoice routes healthcare tasks through deterministic guardrails first, then uses optional LLM providers only for safe phrasing.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <StatusPill label="Session" value={sessionId.slice(-8)} tone="muted" />
              <StatusPill label="Safe to speak" value={lastResult.safe_to_speak === false ? 'NO' : 'YES'} tone={lastResult.safe_to_speak === false ? 'danger' : 'online'} />
            </div>
          </div>
          {error ? (
            <div className="mt-5 flex items-start gap-3 rounded-2xl border border-amber-300/25 bg-amber-300/10 p-4 text-sm text-amber-100">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <p>{error}</p>
            </div>
          ) : null}
        </div>

        <VoiceOrb
          stage={workflowStage}
          partialTranscript={partialTranscript}
          onStart={handleVoiceCapture}
          onStop={stopSpeaking}
          isBusy={isBusy}
          speakCancelled={speakCancelled}
        />

        <TranscriptPanel messages={messages} />

        <section className="glass-card p-5">
          <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white">Demo scenarios</h2>
              <p className="mt-1 text-sm text-slate-400">One-click recruiter walkthroughs that exercise real API paths.</p>
            </div>
            <span className="w-fit rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-xs text-slate-300">
              {isBusy ? 'Scenario running' : 'Ready'}
            </span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {DEMO_SCENARIOS.map((scenario) => (
              <ScenarioCard
                key={scenario.id}
                title={scenario.title}
                description={scenario.description}
                icon={scenario.icon}
                tone={scenario.tone}
                disabled={isBusy}
                onClick={() => runScenario(scenario.id)}
              />
            ))}
          </div>
        </section>

        <PipelineCard currentStage={workflowStage} />
      </section>

      <aside className="space-y-5 lg:col-span-4">
        <VoiceSettingsPanel
          voiceProvider={voiceProvider}
          setVoiceProvider={setVoiceProvider}
          personaId={personaId}
          setPersonaId={setPersonaId}
          language={language}
          setLanguage={setLanguage}
          voiceType={voiceType}
          setVoiceType={setVoiceType}
          llmProvider={health.llm_provider}
          onPreview={previewPersona}
          disabled={isBusy}
        />

        <div className="grid grid-cols-2 gap-3">
          {latencyCards.map((card) => (
            <LatencyCard key={card.label} {...card} />
          ))}
        </div>

        <ResultCard result={lastResult} />
        <GuardrailPanel result={lastResult} />

        <section className="glass-card p-5">
          <div className="mb-4 flex items-center gap-2">
            <HeartPulse className="h-4 w-4 text-emerald-200" aria-hidden="true" />
            <h2 className="text-sm font-semibold text-white">Conversation timeline</h2>
          </div>
          <div className="max-h-[360px] space-y-3 overflow-y-auto pr-1">
            {messages.length === 0 ? (
              <p className="rounded-2xl border border-dashed border-white/15 bg-slate-950/35 p-4 text-sm leading-6 text-slate-400">
                Empty state: launch a voice turn or select a scenario to populate the live timeline.
              </p>
            ) : (
              messages.map((message, index) => (
                <div key={`${message.ts}-${index}`} className={`timeline-bubble ${message.role}`}>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] opacity-70">
                    {message.role === 'user' ? 'Patient' : 'MedVoice AI'}
                  </p>
                  <p className="mt-1 text-sm leading-6">{message.content}</p>
                </div>
              ))
            )}
            <div ref={timelineRef} />
          </div>
        </section>
      </aside>
    </DashboardLayout>
  );
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function recordMicrophoneAudio(durationMs = 4500) {
  if (!navigator.mediaDevices?.getUserMedia) {
    return Promise.reject(new Error('This browser does not support microphone capture.'));
  }
  if (!window.MediaRecorder) {
    return Promise.reject(new Error('This browser does not support MediaRecorder.'));
  }

  return navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
    const mimeType = getSupportedAudioMimeType();
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    const chunks = [];

    return new Promise((resolve, reject) => {
      recorder.ondataavailable = (event) => {
        if (event.data?.size) chunks.push(event.data);
      };
      recorder.onerror = () => {
        stopTracks(stream);
        reject(recorder.error || new Error('Microphone recording failed.'));
      };
      recorder.onstop = () => {
        stopTracks(stream);
        const type = recorder.mimeType || mimeType || 'audio/webm';
        const blob = new Blob(chunks, { type });
        if (!blob.size) {
          reject(new Error('No microphone audio was recorded.'));
          return;
        }
        resolve({ blob, fileName: `voice-turn.${audioExtension(type)}` });
      };

      recorder.start();
      window.setTimeout(() => {
        if (recorder.state !== 'inactive') recorder.stop();
      }, durationMs);
    });
  });
}

function getSupportedAudioMimeType() {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus'];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || '';
}

function audioExtension(mimeType) {
  if (mimeType.includes('mp4')) return 'mp4';
  if (mimeType.includes('ogg')) return 'ogg';
  if (mimeType.includes('wav')) return 'wav';
  return 'webm';
}

function stopTracks(stream) {
  stream.getTracks().forEach((track) => track.stop());
}

export default App;
