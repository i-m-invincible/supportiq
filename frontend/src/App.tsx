import { useEffect, useState, type FormEvent } from 'react';
import { Activity, ArrowDownToLine, ArrowRight, ArrowUpRight, BookOpen, ChartNoAxesCombined, CheckCheck, ChevronDown, ChevronRight, Clock3, Command, Inbox as InboxIcon, LayoutDashboard, Menu, MessageSquareText, Plus, Search, Settings2, ShieldCheck, Sparkles, X } from 'lucide-react';
import { api, exportCSV, setWorkspaceKey } from './lib/api';
import { statuses, type Analytics, type Meta, type Status, type Ticket, type View } from './lib/types';
import { Avatar, Empty, ErrorBox, Modal, Spinner, TicketTable } from './components/Common';
import { CategoryChart, Distribution, TrendChart } from './components/Charts';
import Inbox from './components/Inbox';
import Knowledge from './components/Knowledge';
import ModelLab from './components/ModelLab';
import NewTicket from './components/NewTicket';
import TicketDetail from './components/TicketDetail';

const navigation = [{ id: 'overview', label: 'Overview', icon: LayoutDashboard }, { id: 'inbox', label: 'Inbox', icon: InboxIcon }, { id: 'knowledge', label: 'Knowledge base', icon: BookOpen }, { id: 'analytics', label: 'Analytics', icon: ChartNoAxesCombined }, { id: 'models', label: 'Model lab', icon: Sparkles }] as const;
const descriptions = {
  overview: ['Support, in focus.', 'A clear view of your conversations, priorities, and next steps.'],
  inbox: ['Every conversation counts.', 'Triage the queue. Review the evidence. Make the next step clear.'],
  knowledge: ['Knowledge that answers.', 'The policies and evidence behind every suggested response.'],
  analytics: ['Signals into perspective.', 'Understand complaint patterns across your workspace.'],
  models: ['Inside the intelligence.', 'Explore predictions, inspect evidence, and understand limitations.'],
};

export default function App() {
  const [view, setView] = useState<View>('overview'); const [mobileNav, setMobileNav] = useState(false);
  const [revision, setRevision] = useState(0); const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [recent, setRecent] = useState<Ticket[]>([]); const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState(''); const [loading, setLoading] = useState(true); const [toast, setToast] = useState('');
  const [selected, setSelected] = useState<string | null>(null); const [newTicket, setNewTicket] = useState(false);
  const [settings, setSettings] = useState(false); const [search, setSearch] = useState('');
  const [inboxPreset, setInboxPreset] = useState<{ status: Status | ''; query: string; key: number }>({ status: '', query: '', key: 0 });
  const [exporting, setExporting] = useState(false);
  useEffect(() => {
    let active = true;
    Promise.all([api<Analytics>('/analytics'), api<{ items: Ticket[] }>('/tickets?limit=5'), api<Meta>('/meta')])
      .then(([a, t, m]) => { if (active) { setAnalytics(a); setRecent(t.items); setMeta(m); setError(''); } })
      .catch(e => { if (active) setError(e.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [revision]);
  useEffect(() => { if (!toast) return; const timer = setTimeout(() => setToast(''), 4500); return () => clearTimeout(timer); }, [toast]);
  function navigate(next: View) { setView(next); setMobileNav(false); }
  function showInbox(status: Status | '' = '', query = '') { setInboxPreset(p => ({ status, query, key: p.key + 1 })); navigate('inbox'); }
  function globalSearch(event: FormEvent) { event.preventDefault(); showInbox('', search); }
  async function download() { setExporting(true); try { await exportCSV(); setToast('Conversation report downloaded.'); } catch (e) { setToast((e as Error).message); } finally { setExporting(false); } }
  const date = new Date().toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  return <div className="app-shell">
    {mobileNav && <div className="mobile-shade" onClick={() => setMobileNav(false)} />}
    <aside className={`sidebar ${mobileNav ? 'mobile-open' : ''}`}>
      <button className="brand" onClick={() => navigate('overview')} aria-label="SupportIQ home"><span className="brand-mark"><MessageSquareText size={24} strokeWidth={1.8} /></span><span>support<span className="brand-iq">iq</span><small>CUSTOMER INTELLIGENCE</small></span></button>
      <button className="workspace-switch" onClick={() => setSettings(true)}><span className="workspace-logo">S</span><span><b>Support workspace</b><small>Demo environment</small></span><ChevronDown size={14} /></button>
      <span className="sidebar-label">WORKSPACE</span>
      <nav aria-label="Main navigation">{navigation.map(item => <button key={item.id} className={`nav-item ${view === item.id ? 'active' : ''}`} onClick={() => item.id === 'inbox' ? showInbox() : navigate(item.id)} aria-current={view === item.id ? 'page' : undefined}><item.icon size={19} strokeWidth={1.7} /><span>{item.label}</span>{item.id === 'inbox' && analytics && <b className="nav-count">{analytics.active}</b>}{item.id === 'models' && <span className="nav-lab">LAB</span>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="workspace-note"><span className="sidebar-note-icon"><ShieldCheck size={19} /></span><h4>Intelligence. With oversight.</h4><p>Every suggested response stays in your hands.</p><button onClick={() => navigate('models')}>Explore the model <ArrowUpRight size={14} /></button></div><button className="nav-item settings-nav" onClick={() => setSettings(true)}><Settings2 size={19} /><span>Workspace settings</span></button><div className="sidebar-person"><Avatar name="Support Agent" small /><div><b>Support agent</b><span>Local workspace</span></div><span className="online-dot" /></div></div>
    </aside>
    <div className="main-shell"><header className="topbar"><div className="breadcrumb"><button className="icon-button mobile-menu" onClick={() => setMobileNav(true)} aria-label="Open navigation"><Menu size={21} /></button><span>Workspace</span><ChevronRight size={14} /><strong>{navigation.find(n => n.id === view)?.label}</strong></div><div className="topbar-right"><form className="global-search" onSubmit={globalSearch}><Search size={16} /><input value={search} onChange={e => setSearch(e.target.value)} maxLength={200} aria-label="Search all conversations" placeholder="Search conversations…" /><button type="submit" aria-label="Run search"><ArrowRight size={14} /></button></form><span className="demo-indicator"><i />Demo workspace</span><button className="profile-button" onClick={() => setSettings(true)} aria-label="Workspace settings"><Avatar name="Support Agent" small /></button></div></header>
      <main className="page"><div className="page-heading"><div><div className="eyebrow page-eyebrow">YOUR SUPPORT COMMAND CENTER</div><h1>{descriptions[view][0]}</h1><p>{descriptions[view][1]}</p></div><div className="heading-actions"><button className="button secondary" onClick={() => void download()} disabled={exporting}>{exporting ? <Spinner /> : <ArrowDownToLine size={16} />}Export</button><button className="button primary" onClick={() => setNewTicket(true)}><Plus size={17} />New conversation</button></div></div>
      {error && <ErrorBox message={error + ' If the workspace requires a key, enter it in settings.'} onRetry={() => setRevision(x => x + 1)} />}
      {loading ? <div className="loading-panel"><Spinner /> Connecting to your workspace…</div> : <>
      {view === 'overview' && analytics && <>
        <div className="overview-kicker"><span><i className="live-dot" />Workspace overview</span><span className="muted">{date}<span className="dot-divider">·</span>All conversations</span></div>
        <div className="stats-grid"><Stat label="Total conversations" value={analytics.total} note="Across all channels" icon={InboxIcon} onClick={() => showInbox()} /><Stat label="Awaiting approval" value={analytics.awaiting_review} note="Your review makes the difference" icon={ShieldCheck} accent onClick={() => showInbox('in_review')} /><Stat label="Critical priority" value={analytics.critical} note={`${analytics.overdue} active tickets past review SLA`} icon={Activity} warning onClick={() => showInbox()} /><Stat label="Resolved conversations" value={analytics.resolved} note="Human-reviewed resolutions" icon={CheckCheck} onClick={() => showInbox('resolved')} /></div>
        {analytics.awaiting_review > 0 && <button className="review-nudge" onClick={() => showInbox('in_review')}><span className="nudge-icon"><Sparkles size={19} /></span><span><b>A little attention goes a long way.</b> {analytics.awaiting_review} suggested responses are waiting for your review.</span><span className="nudge-link">Review queue <ArrowRight size={16} /></span></button>}
        <div className="dashboard-charts"><section className="card"><div className="card-heading"><div><h3>Conversation pulse</h3><p>Incoming volume and customer sentiment</p></div><span className="subtle-tag">Last 7 days</span></div><TrendChart data={analytics.trend} /></section><section className="card"><div className="card-heading"><div><h3>What customers need</h3><p>Conversations by category</p></div><ChartNoAxesCombined size={19} /></div><CategoryChart counts={analytics.categories} /></section></div>
        <section className="card recent-card"><div className="card-heading"><div className="section-title-line"><h3>Recent conversations</h3><span className="subtle-tag">{analytics.total} total</span></div><button className="text-button" onClick={() => showInbox()}>View inbox <ArrowUpRight size={15} /></button></div>{recent.length ? <TicketTable compact tickets={recent} onSelect={setSelected} /> : <Empty title="A fresh start.">Create a conversation to begin.</Empty>}<div className="recent-footer"><span><Sparkles size={14} />Automatically analyzed. Thoughtfully reviewed.</span><span>{analytics.active} active conversations</span></div></section>
      </>}
      {view === 'inbox' && <Inbox key={inboxPreset.key} initialStatus={inboxPreset.status} initialQuery={inboxPreset.query} revision={revision} onSelect={setSelected} />}
      {view === 'knowledge' && <Knowledge />}
      {view === 'models' && <ModelLab meta={meta} />}
      {view === 'analytics' && analytics && <><div className="stats-grid"><Stat label="Open work" value={analytics.active} note="Open and in-review tickets" icon={InboxIcon} onClick={() => showInbox()} /><Stat label="Review SLA overdue" value={analytics.overdue} note="Active tickets beyond their deadline" icon={Clock3} warning onClick={() => showInbox()} /><Stat label="Approved responses" value={analytics.approved} note="Reviewed, ready for resolution" icon={ShieldCheck} accent onClick={() => showInbox('approved')} /><Stat label="Resolved" value={analytics.resolved} note="Completed conversation workflow" icon={CheckCheck} onClick={() => showInbox('resolved')} /></div><div className="dashboard-charts"><section className="card"><div className="card-heading"><div><h3>Daily conversation volume</h3><p>Seven calendar days · UTC</p></div></div><TrendChart data={analytics.trend} /></section><section className="card"><div className="card-heading"><h3>Category mix</h3></div><CategoryChart counts={analytics.categories} /></section></div><div className="three-columns"><section className="card"><div className="card-heading"><h3>Priority</h3></div><Distribution values={analytics.priorities} /></section><section className="card"><div className="card-heading"><h3>Sentiment signals</h3></div><Distribution values={analytics.sentiments} /><p className="card-caption">Keyword heuristic, not a trained sentiment model.</p></section><section className="card"><div className="card-heading"><h3>Workflow status</h3></div><Distribution values={analytics.statuses} labels={statuses} /></section></div></>}
      </>}
      <footer className="page-footer"><span><span className="live-dot" />{meta?.draft_provider === 'openai' ? 'LLM drafting configured' : 'Local intelligence'}<span className="dot-divider">·</span>{meta?.classifier.dataset_kind === 'cfpb' ? 'CFPB classifier' : 'Synthetic demo data'}</span><span>Built for better conversations.</span></footer>
      </main>
    </div>
    {selected && <TicketDetail key={selected} id={selected} onClose={() => setSelected(null)} onChanged={() => setRevision(x => x + 1)} />}
    {newTicket && <NewTicket onClose={() => setNewTicket(false)} onCreated={ticket => { setNewTicket(false); setRevision(x => x + 1); setSelected(ticket.id); setToast('Conversation created and analyzed.'); }} />}
    {settings && <WorkspaceSettings meta={meta} onClose={() => setSettings(false)} onSaved={() => { setSettings(false); setRevision(x => x + 1); setToast('Workspace connection updated.'); }} />}
    {toast && <div className="toast" role="status"><CheckCheck size={17} />{toast}<button className="icon-button" aria-label="Dismiss notification" onClick={() => setToast('')}><X size={15} /></button></div>}
  </div>;
}

function Stat({ label, value, note, icon: Icon, accent, warning, onClick }: { label: string; value: number; note: string; icon: typeof InboxIcon; accent?: boolean; warning?: boolean; onClick: () => void }) {
  return <button className={`stat-card ${accent ? 'stat-accent' : ''}`} onClick={onClick}><div className="stat-label"><span>{label}</span><Icon size={18} strokeWidth={1.7} /></div><div className="stat-value">{String(value).padStart(2, '0')}<ArrowUpRight size={20} /></div><span className={`stat-note ${warning ? 'warning-note' : ''}`}>{warning && <span className="dot" />}{note}</span></button>;
}

function WorkspaceSettings({ meta, onClose, onSaved }: { meta: Meta | null; onClose: () => void; onSaved: () => void }) {
  const [key, setKey] = useState('');
  return <Modal title="Workspace settings" onClose={onClose}><form className="form-body" onSubmit={e => { e.preventDefault(); setWorkspaceKey(key.trim()); onSaved(); }}><div className="modal-title-icon"><Command size={25} /></div><h2>Your local workspace.</h2><p className="muted">A single-workspace portfolio application. Demo customers and sample policies are fictional.</p><dl className="model-specs"><div><dt>API protection</dt><dd>{meta?.auth_enabled ? 'Workspace key enabled' : 'Local demo mode'}</dd></div><div><dt>Outbound delivery</dt><dd>Not connected</dd></div><div><dt>Response approval</dt><dd>Always required</dd></div></dl><label>Workspace API key<input type="password" autoComplete="off" value={key} onChange={e => setKey(e.target.value)} placeholder="Only needed if API_KEY is configured" /></label><p className="fine-print">Kept in memory for this browser tab; cleared on reload. This is the workspace key, not an LLM provider key. Leave blank to clear it.</p><div className="modal-actions"><button type="button" className="button secondary" onClick={onClose}>Cancel</button><button className="button primary">Apply connection</button></div></form></Modal>;
}
