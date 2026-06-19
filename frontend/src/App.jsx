import React, { useEffect, useState } from 'react';
import {
  Activity, AlertTriangle, BarChart3, BookOpen, Building2, CheckCircle2, ChevronRight, ClipboardList,
  CreditCard, FlaskConical, Gauge, Headphones, KeyRound, LifeBuoy, LogOut,
  Mic, PhoneCall, Plug, Plus, Receipt, RefreshCw, Search, Settings,
  ShieldCheck, User
} from 'lucide-react';
import {
  approveOnboarding, createAgent, createHospital, deleteKnowledgeDocument,
  ensureFreshSession,
  getAgents, getCallDetail, getCalls, getDashboardMetrics, getKnowledgeBase, getMe,
  getHealth, getOnboardingRequests, getReports, getSettings, getStoredSession, getSuperHospitals,
  getSuperOverview, login, logout, processVoiceTurn, register, testAgent, updateAgent, updateSettings,
  uploadKnowledgeDocument
} from './services/api';

const navHospital = [
  ['Dashboard', '/dashboard', Gauge], ['Voice Team', '/voice-team', Headphones], ['Voice Playground', '/voice-playground', FlaskConical], ['Calls', '/calls', PhoneCall],
  ['Analytics', '/analytics', BarChart3], ['Knowledge Base', '/knowledge-base', BookOpen],
  ['Integrations', '/integrations', Plug], ['Billing', '/billing', CreditCard],
  ['Settings', '/settings', Settings]
];
const navStaff = [
  ['Dashboard', '/dashboard', Gauge], ['Voice Playground', '/voice-playground', FlaskConical], ['Calls', '/calls', PhoneCall],
  ['Analytics', '/analytics', BarChart3], ['Knowledge Base', '/knowledge-base', BookOpen]
];
const navSuper = [
  ['Admin', '/admin', Gauge], ['Hospitals', '/admin/hospitals', Building2],
  ['Usage', '/reports', BarChart3], ['Billing', '/billing', CreditCard]
];

export default function App() {
  const [session, setSession] = useState(getStoredSession());
  const [profile, setProfile] = useState(null);
  const [authLoading, setAuthLoading] = useState(Boolean(session));
  const [route, setRoute] = useState(currentRoute());

  useEffect(() => {
    const onPop = () => setRoute(currentRoute());
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  useEffect(() => {
    if (!session?.access_token) { setAuthLoading(false); return; }
    setAuthLoading(true);
    ensureFreshSession().then(() => getMe()).then((data) => {
      setProfile(data.profile || data.user || data);
      if (route === '/login' || route === '/register' || route === '/') navigate(data.redirect_to || '/dashboard', false);
    }).catch(() => {
      setSession(null);
      setProfile(null);
      navigate('/login', false);
    }).finally(() => setAuthLoading(false));
  }, [session?.access_token]);

  useEffect(() => {
    if (!profile) return;
    if (route.startsWith('/admin') && profile.role !== 'super_admin') navigate('/dashboard', false);
    if (route.startsWith('/agents')) navigate('/voice-team', false);
    if (profile.role === 'staff' && (route.startsWith('/settings') || route.startsWith('/billing') || route.startsWith('/voice-team'))) navigate('/dashboard', false);
  }, [profile?.role, route]);

  function navigate(path, push = true) {
    if (push) window.history.pushState({}, '', path);
    else window.history.replaceState({}, '', path);
    setRoute(path);
  }

  async function handleLogout() {
    await logout();
    setSession(null);
    setProfile(null);
    navigate('/login');
  }

  if (authLoading) return <FullScreenState title="Opening your workspace" detail="Checking your secure session and access level." />;
  if (!session?.access_token || route === '/login' || route === '/register') {
    return <AuthPage mode={route === '/register' ? 'register' : 'login'} navigate={navigate} onLogin={(data) => { setSession(data.session); setProfile(data.profile || data.user); navigate(data.redirect_to || '/dashboard'); }} />;
  }
  if (!profile) return <FullScreenState title="Preparing MedVoice" detail="Loading your hospital workspace." />;

  if (route.startsWith('/admin') && profile.role !== 'super_admin') return <FullScreenState title="Redirecting" detail="Opening your dashboard." />;
  if (profile.role === 'staff' && (route.startsWith('/settings') || route.startsWith('/billing') || route.startsWith('/voice-team'))) return <FullScreenState title="Redirecting" detail="Opening your dashboard." />;

  return (
    <Shell profile={profile} route={route} navigate={navigate} onLogout={handleLogout}>
      {renderPage(route, profile, navigate)}
    </Shell>
  );
}

function renderPage(route, profile, navigate) {
  if (profile.role === 'super_admin' && route.startsWith('/admin/hospitals')) return <HospitalsPage />;
  if (profile.role === 'super_admin' && route.startsWith('/admin')) return <SuperAdminPage />;
  if (route.startsWith('/voice-team') || route.startsWith('/agents')) return <VoiceTeamPage profile={profile} navigate={navigate} />;
  if (route.startsWith('/voice-playground')) return <VoicePlaygroundPage profile={profile} />;
  if (route.startsWith('/calls')) return <CallsPage />;
  if (route.startsWith('/analytics') || route.startsWith('/reports')) return <ReportsPage />;
  if (route.startsWith('/knowledge-base')) return <KnowledgeBasePage profile={profile} />;
  if (route.startsWith('/integrations')) return <IntegrationsPage />;
  if (route.startsWith('/contacts')) return <ContactsPage />;
  if (route.startsWith('/settings')) return <SettingsPage profile={profile} />;
  if (route.startsWith('/billing')) return <BillingPage />;
  return <DashboardPage profile={profile} />;
}

function AuthPage({ mode, navigate, onLogin }) {
  const [form, setForm] = useState({ email: '', password: '', full_name: '', hospital_name: '', phone: '' });
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const isRegister = mode === 'register';

  useEffect(() => {
    setError('');
    setSuccess('');
    setLoading(false);
  }, [mode]);

  async function submit(event) {
    event.preventDefault();
    setLoading(true); setError(''); setSuccess('');
    try {
      if (isRegister) {
        const result = await register({
          email: form.email,
          password: form.password,
          full_name: form.full_name,
          hospital_name: form.hospital_name,
          phone: form.phone || null,
        }, { remember });
        if (result.session) {
          onLogin(result);
          return;
        }
        setSuccess(result.requires_email_confirmation ? 'Check your email to confirm your account, then sign in.' : 'Workspace created. You can sign in now.');
      } else {
        onLogin(await login(form.email, form.password, { remember }));
      }
    } catch (err) {
      setError(authErrorMessage(err, isRegister));
    } finally { setLoading(false); }
  }

  function update(key, value) { setForm({ ...form, [key]: value }); }

  return (
    <main className="auth-canvas min-h-screen px-4 py-6 text-ink sm:px-6 lg:px-10">
      <header className="mx-auto flex max-w-6xl items-center justify-between">
        <BrandLockup />
        <div className="hidden items-center gap-2 sm:flex">
          <button className="ghost-pill" onClick={() => navigate('/login')}>Login</button>
          <button className="dark-pill" onClick={() => navigate('/register')}>Create workspace</button>
        </div>
      </header>

      <div className="auth-shell">
        <section className="auth-positioning auth-copy-lock">
          <p className="eyebrow">MedVoice</p>
          <h1>Your front desk, always on.</h1>
          <p>Manage calls, appointments, handoffs and follow-ups from one quiet workspace.</p>
          <p className="auth-note">Built for clinics that need every patient call answered with care.</p>
        </section>

        <section className="auth-panel-slot" aria-live="polite">
          <form onSubmit={submit} className="auth-card">
            <div className={`auth-tabs ${isRegister ? 'register' : 'login'}`}>
              <button type="button" className={!isRegister ? 'active' : ''} onClick={() => navigate('/login')}>Sign in</button>
              <button type="button" className={isRegister ? 'active' : ''} onClick={() => navigate('/register')}>Register</button>
            </div>
            <div className="form-viewport">
              <div key={mode} className={`auth-form-content ${isRegister ? 'register' : 'login'}`}>
                <h2>{isRegister ? 'Start with MedVoice.' : 'Welcome back.'}</h2>
                <p>{isRegister ? 'Create your clinic workspace and invite your team later.' : 'Access your MedVoice workspace.'}</p>

                {isRegister ? <>
                  <label className="field-label">Full name</label>
                  <input className="input compact" value={form.full_name} onChange={(e) => update('full_name', e.target.value)} required />
                  <label className="field-label mt-3">Hospital or clinic</label>
                  <input className="input compact" value={form.hospital_name} onChange={(e) => update('hospital_name', e.target.value)} required />
                  <label className="field-label mt-3">Work email</label>
                  <input className="input compact" type="email" value={form.email} onChange={(e) => update('email', e.target.value)} required />
                  <label className="field-label mt-3">Phone</label>
                  <input className="input compact" value={form.phone} onChange={(e) => update('phone', e.target.value)} />
                </> : <>
                  <label className="field-label">Work email</label>
                  <input className="input" value={form.email} onChange={(e) => update('email', e.target.value)} type="email" autoComplete="email" required />
                </>}
                <label className={`field-label ${isRegister ? 'mt-3' : 'mt-4'}`}>Password</label>
                <input className={`input ${isRegister ? 'compact' : ''}`} value={form.password} onChange={(e) => update('password', e.target.value)} type="password" autoComplete={isRegister ? 'new-password' : 'current-password'} minLength={isRegister ? 8 : undefined} required />
                {!isRegister ? <label className="remember-row"><input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} /> Remember me</label> : null}
                {success ? <Notice tone="success" text={success} /> : null}
                {error ? <Notice tone="danger" text={error} /> : null}
                <button className="primary-action mt-5 w-full" disabled={loading}>{loading ? (isRegister ? 'Creating workspace...' : 'Signing in...') : 'Continue'}</button>
                <p className="auth-switch-copy">{isRegister ? <>Have an account? <button type="button" className="link" onClick={() => navigate('/login')}>Sign in</button>.</> : <>New here? <button type="button" className="link" onClick={() => navigate('/register')}>Create workspace</button>.</>}</p>
              </div>
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}

function Shell({ profile, route, navigate, onLogout, children }) {
  const nav = profile.role === 'super_admin' ? navSuper : profile.role === 'staff' ? navStaff : navHospital;
  const [accountOpen, setAccountOpen] = useState(false);
  useEffect(() => {
    if (!accountOpen) return undefined;
    function onKey(event) { if (event.key === 'Escape') setAccountOpen(false); }
    function onClick(event) { if (!event.target.closest?.('[data-account-menu]')) setAccountOpen(false); }
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onClick);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onClick);
    };
  }, [accountOpen]);
  function go(path) {
    setAccountOpen(false);
    navigate(path);
  }
  return (
    <main className="app-canvas min-h-screen text-ink">
      <aside className="side-rail hidden lg:flex">
        <BrandLockup compact />
        <nav className="mt-9 flex-1 space-y-1">{nav.map(([label, path, Icon]) => <button key={path} onClick={() => navigate(path)} className={`nav-item ${route === path || (path !== '/dashboard' && route.startsWith(path)) ? 'nav-active' : ''}`}><Icon className="h-4 w-4" />{label}</button>)}</nav>
        <div className="profile-card-wrap" data-account-menu>
          <button className="profile-card" onClick={() => setAccountOpen((open) => !open)} aria-expanded={accountOpen} aria-haspopup="menu">
            <div className="avatar">{initial(profile)}</div>
            <div className="min-w-0 text-left"><p className="truncate text-sm font-semibold">{profile.full_name || profile.email}</p><p className="truncate text-xs capitalize text-[#7a7a7a]">{profile.role.replace('_', ' ')} · {profile.hospital_name || 'MedVoice'}</p></div>
            <ChevronRight className="h-4 w-4 text-[#7a7a7a]" />
          </button>
          {accountOpen ? <AccountMenu profile={profile} go={go} onLogout={onLogout} align="rail" /> : null}
        </div>
      </aside>
      <section className="lg:pl-[18.5rem]">
        <header className="top-bar">
          <div>
            <p className="top-kicker">{profile.hospital_name || 'MedVoice internal'}</p>
            <h1>{pageTitle(route, profile.role)}</h1>
          </div>
          <div className="top-actions">
            {profile.role === 'super_admin' ? <button className="hospital-switcher"><Building2 className="h-4 w-4" /> All hospitals</button> : null}
            <div className="global-search"><Search className="h-4 w-4" /><span>Search calls, receptionists, contacts</span></div>
            <span className="env-pill">Live</span>
            <div className="account-anchor" data-account-menu>
              <button onClick={() => setAccountOpen((open) => !open)} className="user-menu" aria-expanded={accountOpen} aria-haspopup="menu">{initial(profile)}</button>
              {accountOpen ? <AccountMenu profile={profile} go={go} onLogout={onLogout} /> : null}
            </div>
          </div>
          <div className="mobile-nav lg:hidden">{nav.map(([label, path]) => <button key={path} onClick={() => navigate(path)} className={`mobile-tab ${route === path ? 'mobile-tab-active' : ''}`}>{label}</button>)}</div>
        </header>
        <div className="px-4 py-8 sm:px-6 lg:px-10">
          <div key={route} className="content-transition">{children}</div>
        </div>
      </section>
    </main>
  );
}

function AccountMenu({ profile, go, onLogout, align }) {
  const items = [
    ['My Profile', '/settings', User],
    ['Organization', '/settings', Building2],
    ['Users & Permissions', '/settings', ShieldCheck],
    ['Billing', '/billing', CreditCard],
    ['Invoices', '/billing', Receipt],
    ['Usage', '/analytics', Activity],
    ['Audit Log', '/settings', ClipboardList],
    ['API Keys', '/integrations', KeyRound],
    ['Settings', '/settings', Settings],
    ['Support', '/settings', LifeBuoy],
  ];
  return (
    <div className={`account-menu ${align === 'rail' ? 'account-menu-rail' : ''}`} role="menu">
      <div className="account-menu-head">
        <div className="avatar small">{initial(profile)}</div>
        <div className="min-w-0">
          <p>{profile.full_name || profile.email}</p>
          <span>{profile.hospital_name || 'MedVoice'} · {profile.role.replace('_', ' ')}</span>
        </div>
      </div>
      <div className="account-menu-list">
        {items.map(([label, path, Icon]) => <button type="button" role="menuitem" key={label} onClick={() => go(path)}><Icon className="h-4 w-4" />{label}</button>)}
      </div>
      <button type="button" role="menuitem" className="account-logout" onClick={onLogout}><LogOut className="h-4 w-4" />Logout</button>
    </div>
  );
}

function DashboardPage({ profile }) {
  const metrics = useLoader(getDashboardMetrics, []);
  const calls = useLoader(() => getCalls({}), []);
  const agents = useLoader(getAgents, []);
  if (metrics.loading || calls.loading || agents.loading) return <PageLoading />;
  if (metrics.error) return <PageError error={metrics.error} onRetry={metrics.refresh} />;
  if (calls.error) return <PageError error={calls.error} onRetry={calls.refresh} />;
  if (agents.error) return <PageError error={agents.error} onRetry={agents.refresh} />;
  const data = metrics.data;
  const recentCalls = (calls.data || []).slice(0, 6);
  const firstName = (profile?.full_name || profile?.email || 'John').split(/[ @]/)[0] || 'John';
  return <PageStack>
    <section className="dashboard-hero">
      <p>Good morning, {firstName}.</p>
      <h2>Today's activity</h2>
      <div className="activity-line">
        <ActivityStat label="Calls" value={data.today.calls_received} />
        <ActivityStat label="Bookings" value={data.today.appointments_booked} />
        <ActivityStat label="Revenue" value={money(data.business_impact.estimated_revenue_influenced)} />
      </div>
    </section>
    <TwoCol wideLeft>
      <Panel title="Recent calls"><Table columns={['Time', 'Caller', 'Receptionist', 'Outcome', 'Duration', 'Revenue']} rows={recentCalls.map((c) => [dateTime(c.started_at), c.caller_phone || 'Unknown', c.agent_name || 'Unassigned', c.outcome || 'Pending', `${c.duration_seconds || 0}s`, money(c.revenue_estimate)])} empty="No calls yet." /></Panel>
      <Panel title="Pipeline"><KeyValue rows={[[ 'AI handled', `${data.business_impact.ai_handled_percentage}%`], ['Escalation rate', `${data.performance.escalation_rate}%`], ['Avg call duration', `${data.performance.average_call_duration}s`], ['Conversion', `${data.month.conversion_rate}%`]]} /></Panel>
    </TwoCol>
    <Panel title="Voice team performance"><Table columns={['Receptionist', 'Language', 'Voice', 'Status', 'Calls', 'Success']} rows={(agents.data || []).map((a) => [a.name, a.language, a.voice_name || a.voice || 'Default', a.status, a.calls_handled || 0, `${Math.round((a.conversion_rate || 0) * 100)}%`])} empty="No receptionists yet." /></Panel>
  </PageStack>;
}

function VoiceTeamPage({ profile, navigate }) {
  const { data: agents, error, loading, refresh } = useLoader(getAgents, []);
  const [selected, setSelected] = useState(null);
  const [saveState, setSaveState] = useState({ loading: false, success: '', error: '' });
  const canManage = ['super_admin', 'hospital_admin'].includes(profile.role);
  const displayAgents = agents?.length ? agents : defaultAgents();
  useEffect(() => {
    if (!displayAgents.length) return;
    setSelected((current) => {
      if (current && displayAgents.some((agent) => (agent.id && agent.id === current.id) || agent.name === current.name)) return current;
      return displayAgents[0];
    });
  }, [agents?.length]);
  async function saveAgent(payload) {
    setSaveState({ loading: true, success: '', error: '' });
    try {
      const saved = selected?.id ? await updateAgent(selected.id, payload) : await createAgent(payload);
      await refresh();
      setSelected(saved);
      setSaveState({ loading: false, success: 'Changes saved.', error: '' });
    } catch (err) {
      setSaveState({ loading: false, success: '', error: err?.response?.data?.detail || 'Could not save changes.' });
    }
  }
  function openPlayground() {
    const key = active?.id || active?.name || '';
    navigate(`/voice-playground${key ? `?receptionist=${encodeURIComponent(key)}` : ''}`);
  }
  if (loading) return <PageLoading />;
  if (error) return <PageError error={error} onRetry={refresh} />;
  const active = selected || displayAgents[0];
  return <PageStack>
    <section className="voice-team-layout">
      <aside className="voice-team-list">
        <div className="voice-team-heading">
          <div>
            <h2>Voice Team</h2>
            <p>Manage the receptionists that answer calls for this clinic.</p>
          </div>
          {canManage ? <button className="secondary-action compact-action" onClick={() => setSelected(blankAgent())}><Plus className="h-4 w-4" />Add</button> : null}
        </div>
        <div className="agent-list">
          {displayAgents.map((agent) => <button key={agent.id || agent.name} className={`agent-card ${active?.name === agent.name ? 'agent-card-active' : ''}`} onClick={() => setSelected(agent)}>
            <span className="agent-copy"><strong>{agent.name}</strong><small>{agentRole(agent)}</small><em>{languageLabel(agent.language)} · {statusLabel(agent.status)}</em></span>
          </button>)}
        </div>
      </aside>

      <section className="voice-team-detail">
        <div className="detail-heading">
          <div>
            <p className="section-kicker">Selected Receptionist</p>
            <h2>{active?.name || 'New receptionist'}</h2>
          </div>
          <button className="secondary-action" onClick={openPlayground}>Test in Voice Playground</button>
        </div>
        <AgentForm agent={active} disabled={!canManage} onSubmit={saveAgent} saveState={saveState} onOpenPlayground={openPlayground} />
      </section>
    </section>
  </PageStack>;
}

function VoicePlaygroundPage({ profile }) {
  const { data: agents, error, loading, refresh } = useLoader(getAgents, []);
  const health = useLoader(getHealth, []);
  const displayAgents = agents?.length ? agents : defaultAgents();
  const [selectedId, setSelectedId] = useState('');
  const [language] = useState('en-IN');
  const [callState, setCallState] = useState('idle');
  const [sessionId] = useState(() => `playground_${Date.now()}`);
  const [messages, setMessages] = useState([]);
  const [debug, setDebug] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [level, setLevel] = useState(0);
  const selected = displayAgents.find((agent) => String(agent.id || agent.name) === selectedId) || displayAgents[0];
  const sarvamConfigured = Boolean(health.data?.sarvamConfigured ?? health.data?.sarvam_configured);
  const providerMode = sarvamConfigured ? 'sarvam' : 'browser_fallback';
  const firstName = (profile?.full_name || profile?.email || 'there').split(/[ @]/)[0] || 'there';
  const clinic = profile?.hospital_name || 'your clinic';
  const greeting = `Hello ${firstName}. I'm ${selected?.name || 'Emma'}, the ${agentRole(selected).toLowerCase()} for ${clinic}. How can I help you today?`;

  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get('receptionist');
    if (requested && displayAgents.some((agent) => String(agent.id || agent.name) === requested)) {
      setSelectedId(requested);
      return;
    }
    if (!selectedId && displayAgents[0]) setSelectedId(String(displayAgents[0].id || displayAgents[0].name));
  }, [displayAgents.length, selectedId]);

  useEffect(() => {
    setMessages([{ speaker: 'receptionist', name: selected?.name || 'Emma', text: greeting }]);
    setDebug(null);
    setErrorMessage('');
  }, [selected?.id, selected?.name, firstName, clinic]);

  async function startCallTurn() {
    if (callState !== 'idle') return;
    if (!sarvamConfigured) {
      await startBrowserVoiceTurn();
      return;
    }
    setErrorMessage('');
    let recorder;
    let stream;
    let meterFrame;
    let audioContext;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setCallState('listening');
      audioContext = new AudioContext();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      const data = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteFrequencyData(data);
        const avg = data.reduce((sum, value) => sum + value, 0) / data.length;
        setLevel(Math.min(1, avg / 128));
        meterFrame = requestAnimationFrame(tick);
      };
      tick();
      const chunks = [];
      recorder = new MediaRecorder(stream, { mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : undefined });
      recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
      const stopped = new Promise((resolve) => { recorder.onstop = resolve; });
      recorder.start();
      await wait(4200);
      recorder.stop();
      await stopped;
      setCallState('processing');
      const audio = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
      const result = await processVoiceTurn({
        agentId: selected?.id,
        audio,
        sessionId,
        voice: selected?.voice_name || 'female',
        voiceProvider: selected?.voice_provider || 'sarvam',
        personaId: selected?.voice_persona,
        language: selected?.language || language,
      });
      if (result.status === 'error') {
        throw new Error(result.structured_data?.error || 'Voice service failed.');
      }
      const userText = result.user_input || result.transcript || 'Audio received.';
      const response = result.spoken_response || result.display_response || result.response;
      setMessages((items) => [...items, { speaker: 'caller', name: 'You', text: userText }, { speaker: 'receptionist', name: selected?.name || 'Emma', text: response }]);
      setDebug({ ...result, selected_tts_voice: selected?.voice_name || result.voice || 'Sarvam voice' });
      if (result.audio?.audio_base64 || result.audio?.audio_url) {
        setCallState('speaking');
        await playGeneratedAudio(result.audio);
      }
      setCallState('idle');
    } catch (err) {
      setErrorMessage(err?.message || 'Could not complete the voice turn.');
      setCallState('idle');
    } finally {
      if (meterFrame) cancelAnimationFrame(meterFrame);
      if (audioContext) audioContext.close();
      if (stream) stream.getTracks().forEach((track) => track.stop());
      setLevel(0);
    }
  }

  async function startBrowserVoiceTurn() {
    setErrorMessage('');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setErrorMessage('Browser voice mode is not supported in this browser. Try Chrome to test without Sarvam.');
      return;
    }
    let stream;
    let meterFrame;
    let audioContext;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContext = new AudioContext();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      const data = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteFrequencyData(data);
        const avg = data.reduce((sum, value) => sum + value, 0) / data.length;
        setLevel(Math.min(1, avg / 128));
        meterFrame = requestAnimationFrame(tick);
      };
      tick();
      setCallState('listening');
      const transcript = await recognizeBrowserSpeech(SpeechRecognition, selected?.language || language);
      if (!transcript) throw new Error('I could not hear that clearly. Please try again.');
      setCallState('processing');
      if (!selected?.id) throw new Error('Save this receptionist before using browser voice mode.');
      const result = await testAgent(selected.id, transcript, sessionId);
      const response = result.response || result.display_response || result.spoken_response;
      setMessages((items) => [...items, { speaker: 'caller', name: 'You', text: transcript }, { speaker: 'receptionist', name: selected?.name || 'Emma', text: response }]);
      setCallState('speaking');
      const speech = await speakBrowserResponse(response, selected?.language || language, selected?.name);
      setDebug({ ...result, user_input: transcript, intent: result.detected_intent || result.intent, provider: 'browser_fallback', selected_tts_voice: speech.voiceName, confidence: result.confidence, stage_timings: { total_latency_ms: result.latency_ms || 0 } });
      setCallState('idle');
    } catch (err) {
      setErrorMessage(err?.message || 'Browser voice mode could not complete this turn.');
      setCallState('idle');
    } finally {
      if (meterFrame) cancelAnimationFrame(meterFrame);
      if (audioContext) audioContext.close();
      if (stream) stream.getTracks().forEach((track) => track.stop());
      setLevel(0);
    }
  }

  if (loading || health.loading) return <PageLoading />;
  if (error) return <PageError error={error} onRetry={refresh} />;
  if (health.error) return <PageError error={health.error} onRetry={health.refresh} />;
  return <PageStack>
    <section className="voice-call-stage">
      <div className="receptionist-header">
        <div className="receptionist-avatar">{selected?.name?.slice(0, 1) || 'E'}</div>
        <div>
          <h2>{selected?.name || 'Emma'}</h2>
          <p>{agentRole(selected)}</p>
        </div>
        <span className={`call-status ${callState}`}>{stateLabel(callState)}</span>
      </div>

      <div className="conversation-stage">
        {messages.map((item, index) => <div key={`${item.speaker}-${index}`} className={`voice-message ${item.speaker}`}>
          <span>{item.name}</span>
          <p>{item.text}</p>
        </div>)}
        {callState === 'listening' ? <div className="voice-message caller live"><span>You</span><p>Listening...</p><Waveform level={level} /></div> : null}
        {callState === 'processing' ? <div className="voice-message receptionist live"><span>{selected?.name || 'Emma'}</span><p>Thinking<span className="thinking-dots">...</span></p></div> : null}
        {callState === 'speaking' ? <div className="voice-message receptionist live"><span>{selected?.name || 'Emma'}</span><p>Speaking</p><PlaybackWaveform /></div> : null}
      </div>

      {!sarvamConfigured ? <div className="voice-mode-note">Browser voice mode · Production voice is not connected yet.</div> : <div className="voice-mode-note">Sarvam voice connected</div>}
      {errorMessage ? <Notice tone="danger" text={errorMessage} /> : null}

      <div className="call-controls">
        <button className={`call-button ${callState}`} disabled={callState !== 'idle'} onClick={startCallTurn} aria-label="Call your AI receptionist">
          <Mic className="h-7 w-7" />
        </button>
        <p>{controlCopy(callState, providerMode)}</p>
      </div>

      <details className="debug-drawer">
        <summary>Advanced details</summary>
        {debug ? <KeyValue rows={[
          ['Transcript', debug.user_input || '-'],
          ['Intent', debug.intent || '-'],
          ['Current intent', debug.current_intent || '-'],
          ['Workflow state', debug.workflow_state || '-'],
          ['Session', debug.session_id || '-'],
          ['Slots', debug.slots ? JSON.stringify(debug.slots) : '-'],
          ['Missing slots', debug.missing_slots?.length ? debug.missing_slots.join(', ') : '-'],
          ['Next action', debug.next_action || debug.action || '-'],
          ['Selected TTS voice', debug.selected_tts_voice || '-'],
          ['Last user text', debug.user_input || '-'],
          ['Last assistant text', debug.response || debug.display_response || debug.spoken_response || '-'],
          ['Confidence', debug.confidence != null ? `${Math.round(debug.confidence * 100)}%` : '-'],
          ['Provider', debug.provider || '-'],
          ['STT', `${debug.stage_timings?.stt_latency_ms || 0}ms`],
          ['TTS', `${debug.stage_timings?.tts_latency_ms || 0}ms`],
          ['Total latency', `${debug.latency_ms || 0}ms`],
        ]} /> : <Empty text="Advanced call details appear after a live voice turn." />}
      </details>
    </section>
  </PageStack>;
}

function CallsPage() {
  const [filters, setFilters] = useState({});
  const { data: calls, error, loading, refresh } = useLoader(() => getCalls(filters), [JSON.stringify(filters)]);
  const [detail, setDetail] = useState(null);
  async function openCall(call) { setDetail(await getCallDetail(call.id)); }
  if (loading) return <PageLoading />;
  if (error) return <PageError error={error} onRetry={refresh} />;
  return <PageStack><PageIntro kicker="Calls" title="Every conversation, searchable and auditable" detail="Inspect outcomes, appointment status, escalation reason, and redacted transcript details without turning MedVoice into medical records storage." />
    <Panel title="Filters"><div className="filter-grid"><input className="input" placeholder="Outcome" onChange={(e) => setFilters({ ...filters, outcome: e.target.value || undefined })} /><input className="input" placeholder="Language" onChange={(e) => setFilters({ ...filters, language: e.target.value || undefined })} /><label className="check"><input type="checkbox" onChange={(e) => setFilters({ ...filters, escalated_only: e.target.checked || undefined })} /> Escalated only</label><label className="check"><input type="checkbox" onChange={(e) => setFilters({ ...filters, booked_only: e.target.checked || undefined })} /> Booked only</label></div></Panel>
    <TwoCol wideLeft><Panel title="Call log"><Table columns={['Time', 'Caller', 'Receptionist', 'Language', 'Duration', 'Outcome', 'Appointment', 'Revenue', 'Escalation']} rows={(calls || []).map((c) => [<button className="link" onClick={() => openCall(c)}>{dateTime(c.started_at)}</button>, c.caller_phone || 'Unknown', c.agent_name || 'Unassigned', c.language, `${c.duration_seconds || 0}s`, c.outcome || 'pending', c.appointment_status || '-', money(c.revenue_estimate), c.escalation_status || '-'])} empty="No calls match these filters." /></Panel><CallDetail detail={detail} /></TwoCol>
  </PageStack>;
}

function ReportsPage() {
  const { data, error, loading, refresh } = useLoader(getReports, []);
  if (loading) return <PageLoading />;
  if (error) return <PageError error={error} onRetry={refresh} />;
  return <PageStack><PageIntro kicker="Analytics" title="Performance trends for owners and operations teams" detail="Track volume, outcomes, appointment funnel, lead conversion, receptionist performance, language coverage, and revenue influence." />
    <TwoCol><Panel title="Call volume over time"><MiniBars rows={data.call_volume || []} label="day" value="calls" /></Panel><Panel title="Outcome breakdown"><SimpleList rows={(data.outcome_breakdown || []).map((x) => [x.outcome, `${x.calls} calls`])} /></Panel></TwoCol>
    <TwoCol><Panel title="Receptionist comparison"><Table columns={['Receptionist', 'Calls', 'Avg duration', 'Revenue']} rows={(data.agent_comparison || []).map((a) => [a.agent, a.calls, `${a.avg_duration}s`, money(a.revenue)])} /></Panel><Panel title="Language performance"><Table columns={['Language', 'Calls', 'Avg duration']} rows={(data.language_performance || []).map((l) => [l.language, l.calls, `${l.avg_duration}s`])} /></Panel></TwoCol>
  </PageStack>;
}

function KnowledgeBasePage({ profile }) {
  const { data: docs, error, loading, refresh } = useLoader(getKnowledgeBase, []);
  const [uploading, setUploading] = useState(false);
  const canManage = ['super_admin', 'hospital_admin'].includes(profile.role);
  async function upload(file) { if (!file) return; setUploading(true); try { await uploadKnowledgeDocument(file); await refresh(); } finally { setUploading(false); } }
  if (loading) return <PageLoading />;
  if (error) return <PageError error={error} onRetry={refresh} />;
  return <PageStack><PageIntro kicker="Knowledge" title="Give receptionists approved answers" detail="Upload FAQs, operational policies, visiting hours, and routing documents. Responses stay grounded in hospital-approved content." />
    <TwoCol><Panel title="Upload document"><input disabled={!canManage || uploading} type="file" accept=".pdf,.docx,.txt,.md,.markdown" onChange={(e) => upload(e.target.files?.[0])} className="input" /><p className="mt-3 text-sm text-[#7a7a7a]">Supported: PDF, DOCX, TXT, Markdown. External source connectors can be added later.</p><div className="mt-4 grid gap-3 sm:grid-cols-2"><ComingSoon title="Drive folder" /><ComingSoon title="Team wiki" /><ComingSoon title="Website pages" /><ComingSoon title="CRM notes" /></div></Panel><Panel title="Documents"><Table columns={['Title', 'Status', 'Chunks', 'Type', 'Action']} rows={(docs || []).map((d) => [d.title, <Badge tone={d.status === 'active' ? 'green' : d.status === 'failed' ? 'red' : 'amber'}>{d.status}</Badge>, d.chunks_count || 0, d.file_type || '-', canManage ? <button className="link" onClick={async () => { await deleteKnowledgeDocument(d.id); await refresh(); }}>Deactivate</button> : '-'])} empty="No documents uploaded." /></Panel></TwoCol>
  </PageStack>;
}

function ContactsPage() {
  const { data: calls, error, loading, refresh } = useLoader(() => getCalls({}), []);
  if (loading) return <PageLoading />;
  if (error) return <PageError error={error} onRetry={refresh} />;
  const contacts = Object.values((calls || []).reduce((acc, call) => {
    const key = call.caller_phone || 'Unknown';
    const current = acc[key] || { caller: key, calls: 0, last_call: call.started_at, last_outcome: call.outcome, appointment_status: call.appointment_status, revenue: 0 };
    current.calls += 1;
    current.revenue += Number(call.revenue_estimate || 0);
    if (!current.last_call || new Date(call.started_at) > new Date(current.last_call)) {
      current.last_call = call.started_at;
      current.last_outcome = call.outcome;
      current.appointment_status = call.appointment_status;
    }
    acc[key] = current;
    return acc;
  }, {}));
  return <PageStack><PageIntro kicker="Contacts" title="Operational caller history" detail="Business contact view built from calls only. No diagnosis, prescription, or clinical notes are stored here." />
    <Panel title="Contacts / Patients"><Table columns={['Caller', 'Calls', 'Last call', 'Last outcome', 'Appointment', 'Revenue influenced']} rows={contacts.map((c) => [c.caller, c.calls, dateTime(c.last_call), c.last_outcome || '-', c.appointment_status || '-', money(c.revenue)])} empty="No caller history yet." /></Panel>
  </PageStack>;
}

function SettingsPage({ profile }) {
  const { data, error, loading, refresh } = useLoader(getSettings, []);
  const [form, setForm] = useState({});
  const canManage = ['super_admin', 'hospital_admin'].includes(profile.role);
  useEffect(() => { if (data) setForm({ hospital_name: data.hospital?.name || '', timezone: data.hospital?.timezone || 'Asia/Kolkata' }); }, [data]);
  async function save() { await updateSettings(form); await refresh(); }
  if (loading) return <PageLoading />;
  if (error) return <PageError error={error} onRetry={refresh} />;
  return <PageStack><PageIntro kicker="Settings" title="Workspace controls" detail="Manage hospital profile, team access, phone routing, voice behavior, AI safety, and audit visibility." />
    <TwoCol><Panel title="General"><label className="field-label">Hospital name</label><input className="input" disabled={!canManage} value={form.hospital_name || ''} onChange={(e) => setForm({ ...form, hospital_name: e.target.value })} /><label className="field-label mt-4">Timezone</label><input className="input" disabled={!canManage} value={form.timezone || ''} onChange={(e) => setForm({ ...form, timezone: e.target.value })} />{canManage ? <button onClick={save} className="primary-action mt-4">Save settings</button> : null}</Panel><Panel title="Team"><Table columns={['Email', 'Name', 'Role', 'Status']} rows={(data.team || []).map((m) => [m.email, m.full_name || '-', m.role, <Badge tone={m.status === 'active' ? 'green' : 'amber'}>{m.status}</Badge>])} /></Panel></TwoCol>
    <div className="grid gap-5 xl:grid-cols-4"><SettingsCard title="Phone routing" rows={['Main number', 'Caller ID', 'Transfer line', 'Callback status']} /><SettingsCard title="Voice" rows={['Default language', 'Voice style', 'Speaking speed', 'Fallback message']} /><SettingsCard title="AI behavior" rows={['Prompt defaults', 'Safe escalation', 'Confidence threshold', 'No-medical-advice rule']} /><SettingsCard title="Security" rows={['Role visibility', 'Transcript access', 'Audit trail', 'Sensitive data limits']} /></div>
  </PageStack>;
}

function IntegrationsPage() {
  return <PageStack><PageIntro kicker="Integrations" title="Connect the systems your front desk already uses" detail="Keep the surface quiet: phone, calendar, CRM, and knowledge connectors are tracked here without adding dashboard clutter." />
    <div className="integration-grid">
      {['Telephony', 'Calendar', 'CRM', 'Knowledge'].map((name) => <article className="integration-item" key={name}><Plug className="h-5 w-5" /><div><h3>{name}</h3><p>Not connected</p></div><button className="secondary-action">Configure</button></article>)}
    </div>
  </PageStack>;
}

function SuperAdminPage() {
  const { data, error, loading, refresh } = useLoader(getSuperOverview, []);
  if (loading) return <PageLoading />;
  if (error) return <PageError error={error} onRetry={refresh} />;
  return <PageStack><PageIntro kicker="Platform overview" title="Hospital workspace health" detail="Review hospital growth, usage, minutes handled, and workspace setup from one place." /><MetricGrid items={[[ 'Total hospitals', data.total_hospitals, '', Building2], ['Active hospitals', data.active_hospitals, '', CheckCircle2], ['Total calls', data.total_calls, '', PhoneCall], ['Total minutes', data.total_minutes, '', BarChart3], ['Needs attention', data.failed_integrations, '', AlertTriangle]]} /><OnboardingPanel /></PageStack>;
}

function OnboardingPanel() {
  const { data: rows, error, loading, refresh } = useLoader(getOnboardingRequests, []);
  async function approve(row) { await approveOnboarding(row.id, { plan: 'pilot', status: 'active' }); await refresh(); }
  if (loading) return <Panel title="Workspace requests"><p className="text-sm text-[#7a7a7a]">Loading requests...</p></Panel>;
  if (error) return <Panel title="Workspace requests"><Notice tone="danger" text={error} /></Panel>;
  return <Panel title="Workspace requests"><Table columns={['Hospital', 'Admin', 'Phone', 'Status', 'Requested', 'Action']} rows={(rows || []).map((r) => [r.hospital_name, r.work_email, r.phone || '-', <Badge tone={r.status === 'approved' ? 'green' : 'amber'}>{r.status}</Badge>, dateTime(r.created_at), r.status === 'pending' ? <button className="primary-action py-2" onClick={() => approve(r)}>Approve</button> : 'Approved'])} empty="No workspace requests yet." /></Panel>;
}

function HospitalsPage() {
  const { data: hospitals, error, loading, refresh } = useLoader(getSuperHospitals, []);
  const [form, setForm] = useState({ name: '', slug: '', admin_email: '', plan: 'pilot', status: 'active' });
  async function submit(e) { e.preventDefault(); await createHospital(form); setForm({ name: '', slug: '', admin_email: '', plan: 'pilot', status: 'active' }); await refresh(); }
  if (loading) return <PageLoading />;
  if (error) return <PageError error={error} onRetry={refresh} />;
  return <PageStack><PageIntro kicker="Hospitals" title="Manage hospital workspaces" detail="Create and monitor approved hospital workspaces across MedVoice." />
    <TwoCol><Panel title="Create workspace"><form onSubmit={submit} className="grid gap-3"><input className="input" placeholder="Hospital name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /><input className="input" placeholder="Short URL slug" value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} required /><input className="input" placeholder="Admin email" value={form.admin_email} onChange={(e) => setForm({ ...form, admin_email: e.target.value })} /><button className="primary-action">Create workspace</button></form></Panel><Panel title="Workspace list"><Table columns={['Hospital', 'Status', 'Plan', 'Calls month', 'Admin']} rows={(hospitals || []).map((h) => [h.name, <Badge tone={h.status === 'active' ? 'green' : 'amber'}>{h.status}</Badge>, h.plan, h.calls_this_month, h.admin_email || '-'])} /></Panel></TwoCol>
  </PageStack>;
}

function BillingPage() {
  return <PageStack>
    <PageIntro kicker="Billing" title="Plan, usage and invoices" detail="Monitor subscription state, call volume, voice minutes, invoices, and usage limits from one account center." />
    <MetricGrid compact items={[[ 'Plan', 'Pilot', 'Subscription active', CreditCard], ['Voice minutes', '1,240', '760 remaining this cycle', Activity], ['Calls', '430', 'This billing cycle', PhoneCall], ['Invoices', '3', 'No overdue invoices', Receipt]]} />
    <TwoCol>
      <Panel title="Subscription"><KeyValue rows={[[ 'Current plan', 'Pilot' ], ['Status', 'Trialing' ], ['Billing email', 'admin@demo.com' ], ['Renewal', 'Monthly' ]]} /></Panel>
      <Panel title="Usage"><KeyValue rows={[[ 'Included minutes', '2,000' ], ['Used minutes', '1,240' ], ['Included calls', '1,000' ], ['Used calls', '430' ]]} /></Panel>
    </TwoCol>
    <Panel title="Invoices"><Table columns={['Invoice', 'Period', 'Amount', 'Status']} rows={[['INV-1003', 'June 2026', '₹0', 'Draft'], ['INV-1002', 'May 2026', '₹0', 'Paid'], ['INV-1001', 'April 2026', '₹0', 'Paid']]} /></Panel>
  </PageStack>;
}

function AgentForm({ agent, disabled, onSubmit, saveState, onOpenPlayground }) {
  const [form, setForm] = useState(blankAgent());
  useEffect(() => setForm(agent ? { ...blankAgent(), ...agent } : blankAgent()), [agent?.id, agent?.name]);
  function change(key, value) { setForm({ ...form, [key]: value }); }
  async function submit(event) {
    event.preventDefault();
    if (saveState?.loading) return;
    await onSubmit(form);
  }
  return <form className="config-form" onSubmit={submit}>
    <ConfigSection title="Basics">
      <div className="form-grid">
        <Field label="Name"><input className="input" disabled={disabled} placeholder="Emma" value={form.name} onChange={(e) => change('name', e.target.value)} required /></Field>
        <Field label="Role"><input className="input" disabled={disabled} placeholder="Front Desk Receptionist" value={form.description || ''} onChange={(e) => change('description', e.target.value)} /></Field>
        <Field label="Status"><select className="input" disabled={disabled} value={form.status} onChange={(e) => change('status', e.target.value)}><option>draft</option><option>active</option><option>inactive</option></select></Field>
      </div>
    </ConfigSection>
    <ConfigSection title="Voice">
      <div className="form-grid two">
        <Field label="Language"><input className="input" disabled={disabled} value={form.language} onChange={(e) => change('language', e.target.value)} /></Field>
        <Field label="Voice"><input className="input" disabled={disabled} value={form.voice_name || ''} onChange={(e) => change('voice_name', e.target.value)} placeholder="Anaya" /></Field>
      </div>
    </ConfigSection>
    <ConfigSection title="Greeting">
      <Field label="First message callers hear"><textarea className="input textarea-compact" disabled={disabled} placeholder="Hi, this is Emma from the front desk..." value={form.greeting || ''} onChange={(e) => change('greeting', e.target.value)} /></Field>
    </ConfigSection>
    <ConfigSection title="Call Rules">
      <Field label="When to book or transfer"><textarea className="input textarea-compact" disabled={disabled} placeholder="Book appointment requests. Transfer clinical, urgent, billing, or unclear questions." value={form.system_prompt || ''} onChange={(e) => change('system_prompt', e.target.value)} /></Field>
      <div className="form-grid two">
        <Field label="Transfer phone"><input className="input" disabled={disabled} placeholder="+91..." value={form.transfer_phone_number || ''} onChange={(e) => change('transfer_phone_number', e.target.value)} /></Field>
        <Field label="Fallback behavior"><input className="input" disabled={disabled} placeholder="Collect details and ask staff to call back" value={form.fallback_behavior || ''} onChange={(e) => change('fallback_behavior', e.target.value)} /></Field>
      </div>
    </ConfigSection>
    <ConfigSection title="Working Hours">
      <Field label="Availability"><input className="input" disabled value={workingHoursLabel(form)} /></Field>
    </ConfigSection>
    {saveState?.success ? <Notice tone="success" text={saveState.success} /> : null}
    {saveState?.error ? <Notice tone="danger" text={saveState.error} /> : null}
    {!disabled ? <div className="form-actions"><button className="primary-action" disabled={saveState?.loading}>{saveState?.loading ? 'Saving...' : 'Save changes'}</button><button type="button" onClick={onOpenPlayground} className="secondary-action">Test in Voice Playground</button></div> : <Notice tone="warn" text="Staff can view reception configuration but cannot change hospital-wide settings." />}
  </form>;
}
function blankAgent() { return { name: '', description: '', status: 'draft', language: 'en-IN', voice_provider: 'sarvam', voice_name: 'Anaya', tts_pace: 1, greeting: '', system_prompt: '', transfer_phone_number: '', fallback_behavior: '' }; }

function CallDetail({ detail }) { return <Panel title="Call detail">{!detail ? <Empty text="Select a call to inspect summary, timeline, transcript, analytics, and recording status." /> : <div className="call-detail-stack"><DetailSection title="Summary"><p>{detail.summary?.discussed || detail.call?.summary || 'No stored summary.'}</p></DetailSection><DetailSection title="Timeline"><KeyValue rows={[[ 'Outcome', detail.call?.outcome || '-' ], ['Appointment', detail.call?.appointment_status || '-' ], ['Escalation', detail.escalation?.reason || 'None' ]]} /></DetailSection><DetailSection title="Transcript"><div className="transcript-list">{(detail.conversation || []).map((t) => <div className="transcript-turn" key={t.id}><span>{t.speaker}</span><p>{t.redacted_text || t.text}</p></div>)}</div></DetailSection><DetailSection title="Analytics"><KeyValue rows={[[ 'Revenue estimate', money(detail.call?.revenue_estimate)], ['Duration', `${detail.call?.duration_seconds || 0}s`], ['Language', detail.call?.language || '-' ]]} /></DetailSection><DetailSection title="Recording player"><p>{detail.call?.recording_url ? 'Recording available' : 'No recording attached to this call.'}</p></DetailSection></div>}</Panel>; }

function Waveform({ level = 0 }) {
  return <div className="voice-wave" aria-hidden="true">{Array.from({ length: 18 }).map((_, index) => <span key={index} style={{ transform: `scaleY(${0.25 + Math.max(level, 0.12) * (((index % 5) + 1) / 5) * 2.8})` }} />)}</div>;
}

function PlaybackWaveform() {
  return <div className="voice-wave playback" aria-hidden="true">{Array.from({ length: 18 }).map((_, index) => <span key={index} style={{ animationDelay: `${index * 45}ms` }} />)}</div>;
}

function stateLabel(state) {
  return ({ idle: 'Online', listening: 'Listening', processing: 'Processing', speaking: 'Speaking' }[state] || 'Online');
}

function controlCopy(state, providerMode = 'sarvam') {
  if (state === 'idle' && providerMode === 'browser_fallback') return 'Tap to talk. Testing with browser voice.';
  return ({ idle: 'Tap to talk to your receptionist.', listening: 'Listening now. Speak naturally.', processing: 'Preparing the response.', speaking: 'Playing the receptionist response.' }[state] || 'Tap to talk.');
}

function recognizeBrowserSpeech(SpeechRecognition, language) {
  return new Promise((resolve, reject) => {
    const recognition = new SpeechRecognition();
    recognition.lang = language || 'en-IN';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => resolve(event.results?.[0]?.[0]?.transcript || '');
    recognition.onerror = () => reject(new Error('Browser voice mode could not hear you clearly.'));
    recognition.onend = () => resolve('');
    recognition.start();
  });
}

let activeBrowserUtterance = null;

async function speakBrowserResponse(text, language, receptionistName) {
  const voices = await loadBrowserVoices();
  const voice = selectBrowserVoice(voices, language, receptionistName);
  return new Promise((resolve) => {
    if (!text || !window.speechSynthesis) { resolve({ voiceName: '-' }); return; }
    if (window.speechSynthesis.speaking || window.speechSynthesis.pending) window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = language || 'en-IN';
    utterance.rate = 1;
    utterance.pitch = preferredVoiceGender(receptionistName) === 'female' ? 1.05 : 1;
    utterance.volume = 1;
    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang || utterance.lang;
    }
    activeBrowserUtterance = utterance;
    const finish = () => {
      window.setTimeout(() => {
        if (activeBrowserUtterance === utterance) activeBrowserUtterance = null;
        resolve({ voiceName: voice?.name || 'Browser default' });
      }, 300);
    };
    utterance.onend = finish;
    utterance.onerror = finish;
    window.speechSynthesis.speak(utterance);
  });
}

function loadBrowserVoices() {
  return new Promise((resolve) => {
    if (!window.speechSynthesis) { resolve([]); return; }
    const current = window.speechSynthesis.getVoices();
    if (current.length) { resolve(current); return; }
    const timer = window.setTimeout(() => resolve(window.speechSynthesis.getVoices()), 500);
    window.speechSynthesis.onvoiceschanged = () => {
      window.clearTimeout(timer);
      resolve(window.speechSynthesis.getVoices());
    };
  });
}

function selectBrowserVoice(voices, language, receptionistName) {
  const desiredGender = preferredVoiceGender(receptionistName);
  const lang = (language || 'en-IN').toLowerCase();
  const scored = voices.map((voice) => {
    const name = voice.name.toLowerCase();
    const voiceLang = (voice.lang || '').toLowerCase();
    let score = 0;
    if (voiceLang === lang) score += 60;
    else if (voiceLang.startsWith(lang.split('-')[0])) score += 30;
    if (voiceGenderScore(name, desiredGender)) score += 25;
    if (name.includes('google') || name.includes('microsoft') || name.includes('natural') || name.includes('neural')) score += 15;
    if (voice.default) score += 3;
    return { voice, score };
  });
  scored.sort((a, b) => b.score - a.score);
  return scored[0]?.voice || null;
}

function preferredVoiceGender(name = '') {
  const lowered = name.toLowerCase();
  if (['sarah', 'sara', 'emma', 'maya', 'priya'].some((candidate) => lowered.includes(candidate))) return 'female';
  if (['david', 'daniel', 'thomas'].some((candidate) => lowered.includes(candidate))) return 'male';
  return 'female';
}

function voiceGenderScore(voiceName, desiredGender) {
  const femaleHints = ['female', 'woman', 'zira', 'susan', 'samantha', 'karen', 'moira', 'veena', 'lekha', 'raveena', 'asha', 'heera', 'natasha'];
  const maleHints = ['male', 'man', 'david', 'mark', 'daniel', 'ravi', 'alex', 'fred', 'thomas'];
  const hints = desiredGender === 'female' ? femaleHints : maleHints;
  return hints.some((hint) => voiceName.includes(hint));
}

function playGeneratedAudio(audio) {
  return new Promise((resolve) => {
    const source = audio?.audio_url || (audio?.audio_base64 ? `data:${audio.mime_type || 'audio/wav'};base64,${audio.audio_base64}` : null);
    if (!source) { resolve(); return; }
    const player = new Audio(source);
    player.onended = resolve;
    player.onerror = resolve;
    player.play().catch(resolve);
  });
}

function BrandLockup({ compact }) { return <div className="flex items-center gap-3"><div className="mv-logo" aria-hidden="true"><span /><span /><span /><span /></div>{!compact ? <div><p className="brand-name">MedVoice</p><p className="brand-caption">Voice operations platform</p></div> : <div><p className="brand-name">MedVoice</p><p className="brand-caption">Voice operations</p></div>}</div>; }
function authErrorMessage(err, isRegister) {
  const detail = err?.response?.data?.detail;
  if (detail) return detail;
  if (err?.code === 'ERR_NETWORK' || !err?.response) {
    return 'Backend is not reachable at http://localhost:8000. Start the backend, then try again.';
  }
  return isRegister ? 'Registration failed. Check backend and Supabase configuration.' : 'We could not sign you in. Check your email and password.';
}
function useLoader(fn, deps) { const [data, setData] = useState(null); const [error, setError] = useState(''); const [loading, setLoading] = useState(true); async function refresh() { setLoading(true); setError(''); try { setData(await fn()); } catch (e) { setError(e?.response?.data?.detail || 'Request failed.'); } finally { setLoading(false); } } useEffect(() => { refresh(); }, deps); return { data, error, loading, refresh }; }
function PageStack({ children }) { return <div className="mx-auto flex max-w-7xl flex-col gap-5">{children}</div>; }
function ActivityStat({ label, value }) { return <div><span>{label}</span><strong>{value}</strong></div>; }
function PageIntro({ kicker, title, detail, action }) { return <section className="page-intro"><div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between"><div><p className="section-kicker">{kicker}</p><h2>{title}</h2><p>{detail}</p></div>{action}</div></section>; }
function Panel({ title, children }) { return <section className="panel"><h3>{title}</h3>{children}</section>; }
function TwoCol({ children, wideLeft }) { return <div className={`grid gap-5 ${wideLeft ? 'xl:grid-cols-[1.35fr_0.9fr]' : 'xl:grid-cols-2'}`}>{children}</div>; }
function MetricGrid({ items, compact }) { return <div className={`grid gap-4 ${compact ? 'sm:grid-cols-2 xl:grid-cols-3' : 'sm:grid-cols-2 xl:grid-cols-5'}`}>{items.map(([label, value, detail, Icon]) => <article className="metric-card" key={label}><div className="metric-icon"><Icon className="h-5 w-5" /></div><p>{label}</p><strong>{value}</strong>{detail ? <span>{detail}</span> : null}</article>)}</div>; }
function Table({ columns, rows = [], empty = 'No rows yet.' }) { if (!rows.length) return <Empty text={empty} />; return <div className="overflow-x-auto"><table className="data-table"><thead><tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr></thead><tbody>{rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j}>{cell}</td>)}</tr>)}</tbody></table></div>; }
function KeyValue({ rows }) { return <div className="mt-4 grid gap-2">{rows.map(([k, v]) => <div className="kv-row" key={k}><span>{k}</span><strong>{v || '-'}</strong></div>)}</div>; }
function SimpleList({ rows }) { return <div className="space-y-2">{rows.length ? rows.map(([a, b]) => <div className="kv-row" key={a}><span>{a}</span><strong>{b}</strong></div>) : <Empty text="No report data yet." />}</div>; }
function MiniBars({ rows, label, value }) { const max = Math.max(1, ...rows.map((r) => r[value] || 0)); return <div className="space-y-3">{rows.length ? rows.map((r) => <div key={r[label]}><div className="flex justify-between text-xs text-[#7a7a7a]"><span>{r[label]}</span><span>{r[value]}</span></div><div className="mt-1 h-2 overflow-hidden rounded-full bg-[#fafafa]"><div className="h-full rounded-full bg-[#111111]" style={{ width: `${((r[value] || 0) / max) * 100}%` }} /></div></div>) : <Empty text="No report data yet." />}</div>; }
function Badge({ tone, children }) { return <span className={`status ${tone === 'red' ? 'status-red' : tone === 'amber' ? 'status-amber' : 'status-green'}`}>{children}</span>; }
function Notice({ tone, text }) { return <div className={`notice ${tone === 'success' ? 'notice-success' : tone === 'danger' ? 'notice-danger' : 'notice-warn'}`}>{text}</div>; }
function Empty({ text }) { return <p className="empty-state">{text}</p>; }
function PageLoading() { return <Panel title="Loading"><p className="text-sm text-[#7a7a7a]">Loading workspace data...</p></Panel>; }
function PageError({ error, onRetry }) { return <Panel title="Could not load page"><Notice tone="danger" text={error} /><button className="secondary-action mt-4" onClick={onRetry}><RefreshCw className="h-4 w-4" /> Retry</button></Panel>; }
function FullScreenState({ title, detail }) { return <main className="auth-canvas flex min-h-screen items-center justify-center px-4"><div className="panel max-w-md p-8 text-center"><div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-[#eaeaea] text-[#111111]"><RefreshCw className="h-5 w-5 animate-spin" /></div><h1 className="text-2xl font-semibold">{title}</h1><p className="mt-2 text-sm text-[#7a7a7a]">{detail}</p></div></main>; }
function SettingsCard({ title, rows }) { return <Panel title={title}><ul className="space-y-2">{rows.map((r) => <li className="flex items-center gap-2 text-sm text-[#7a7a7a]" key={r}><ChevronRight className="h-4 w-4 text-[#111111]" />{r}</li>)}</ul></Panel>; }
function ComingSoon({ title }) { return <div className="rounded-[20px] border border-dashed border-[#eaeaea] p-3 text-sm text-[#7a7a7a]">{title} · coming soon</div>; }
function ConfigSection({ title, children }) { return <section className="config-section"><h4>{title}</h4>{children}</section>; }
function Field({ label, children }) { return <label className="field-stack"><span>{label}</span>{children}</label>; }
function DetailSection({ title, children }) { return <section className="detail-section"><h4>{title}</h4>{children}</section>; }
function PreviewItem({ icon: Icon, label, value }) { return <div><Icon className="h-4 w-4" /><span>{label}</span><strong>{value || '-'}</strong></div>; }
function defaultAgents() { return [
  { name: 'Emma', description: 'Front Desk Receptionist', voice_name: 'Anaya', language: 'en-IN', status: 'active', greeting: 'Hi, this is Emma from Demo Dental. I can help you book, reschedule, or reach the front desk.' },
  { name: 'Maya', description: 'Appointment Coordinator', voice_name: 'Meera', language: 'en-IN', status: 'active', greeting: 'Hi, this is Maya. I can help find an appointment time and confirm the next step.' },
  { name: 'Sarah', description: 'Patient Follow-up Specialist', voice_name: 'Kavya', language: 'en-IN', status: 'active', greeting: 'Hi, this is Sarah. I can help with reminders, confirmations, and follow-up calls.' },
  { name: 'David', description: 'Department Routing Assistant', voice_name: 'Arjun', language: 'en-IN', status: 'active', greeting: 'Hi, this is David. I can understand what you need and connect you to the right department.' },
  { name: 'Priya', description: 'Patient Support Assistant', voice_name: 'Rohan', language: 'en-IN', status: 'active', greeting: 'Hi, this is Priya. I can answer front desk questions or arrange a staff callback.' },
]; }
function agentRole(agent) { return agent?.description || ({ Emma: 'Front Desk Receptionist', Maya: 'Appointment Coordinator', Sarah: 'Patient Follow-up Specialist', David: 'Department Routing Assistant', Priya: 'Patient Support Assistant' }[agent?.name] || 'Reception'); }
function workingHoursLabel(agent) { const hours = agent?.working_hours; return hours && Object.keys(hours).length ? Object.values(hours).join(', ') : 'Mon-Fri, 9:00-18:00'; }
function languageLabel(language) { return ({ 'en-IN': 'English', 'hi-IN': 'Hindi', 'ml-IN': 'Malayalam', 'ta-IN': 'Tamil', 'te-IN': 'Telugu' }[language] || language || 'English'); }
function statusLabel(status) { return status === 'active' ? 'Active' : status === 'inactive' ? 'Inactive' : 'Draft'; }
function pageTitle(route, role) { const path = route.split('?')[0]; if (role === 'super_admin' && path.startsWith('/admin')) return path.includes('hospitals') ? 'Hospitals' : 'Admin'; return ({ '/overview': 'Dashboard', '/dashboard': 'Dashboard', '/voice-team': 'Voice Team', '/voice-playground': 'Voice Playground', '/agents': 'Voice Team', '/calls': 'Calls', '/analytics': 'Analytics', '/reports': 'Analytics', '/knowledge-base': 'Knowledge Base', '/integrations': 'Integrations', '/contacts': 'Contacts', '/settings': 'Settings', '/billing': 'Billing' }[path] || 'Dashboard'); }
function initial(profile) { return (profile?.full_name || profile?.email || 'M').slice(0, 1).toUpperCase(); }
function currentRoute() { const path = `${window.location.pathname}${window.location.search}`; return path === '/' ? '/dashboard' : path; }
function wait(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
function dateTime(value) { return value ? new Date(value).toLocaleString() : '-'; }
function money(value) { return `₹${Number(value || 0).toLocaleString('en-IN')}`; }
