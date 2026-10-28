import { useEffect, useState } from 'react';
import { Check, CheckCheck, Clock3, FileText, History, RefreshCw, Save, ShieldCheck, Sparkles, UserRound, X, ArrowUpRight } from 'lucide-react';
import { api, mutation } from '../lib/api';
import { categories, formatDate, percent, slaLabel, type Audit, type Category, type Priority, type Ticket } from '../lib/types';
import { Avatar, ErrorBox, Modal, PriorityBadge, Spinner, StatusBadge } from './Common';

export default function TicketDetail({ id, onClose, onChanged }: { id: string; onClose: () => void; onChanged: () => void }) {
  const [ticket, setTicket] = useState<Ticket | null>(null); const [audit, setAudit] = useState<Audit[]>([]);
  const [error, setError] = useState(''); const [busy, setBusy] = useState(''); const [draft, setDraft] = useState('');
  const [reviewer, setReviewer] = useState(''); const [note, setNote] = useState('');
  const [tab, setTab] = useState<'response' | 'activity'>('response');
  const [category, setCategory] = useState<Category>('other'); const [priority, setPriority] = useState<Priority>('medium'); const [assignee, setAssignee] = useState('');
  function receive(t: Ticket) { setTicket(t); setDraft(t.draft_text || ''); setCategory(t.category); setPriority(t.priority); setAssignee(t.assignee); }
  async function refresh() {
    setError('');
    try { const [t, a] = await Promise.all([api<Ticket>(`/tickets/${id}`), api<Audit[]>(`/tickets/${id}/audit`)]); receive(t); setAudit(a); }
    catch (e) { setError((e as Error).message); }
  }
  useEffect(() => { void refresh(); }, [id]);
  async function act(name: string, path: string, method: string, body: object) {
    if (!ticket) return;
    setBusy(name); setError('');
    try {
      const result = await mutation<Ticket>(`/tickets/${id}${path}`, method, { ...body, expected_version: ticket.version });
      receive(result); onChanged(); setAudit(await api<Audit[]>(`/tickets/${id}/audit`));
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(''); }
  }
  const changed = ticket && draft !== (ticket.draft_text || '');
  const triageChanged = ticket && (category !== ticket.category || priority !== ticket.priority || assignee !== ticket.assignee);
  return <Modal title={`Conversation / ${id}`} onClose={onClose} wide busy={!!busy}>
    {error && <div className="drawer-error"><ErrorBox message={error} onRetry={() => void refresh()} /></div>}
    {!ticket ? <div className="loading-panel"><Spinner /> Loading conversation…</div> : <div className="drawer-body">
      <div className="detail-title"><div className="inline-tags"><PriorityBadge value={ticket.priority} /><StatusBadge value={ticket.status} /><span className="muted detail-channel">via {ticket.channel}</span></div><h2>{ticket.subject}</h2><div className="customer-line"><Avatar name={ticket.customer_name} small /><b>{ticket.customer_name}</b><span>·</span><span>{formatDate(ticket.created_at)}</span></div></div>
      <section className="complaint-card"><span className="eyebrow">CUSTOMER MESSAGE</span><p>{ticket.body}</p></section>
      <section className="analysis-card"><div className="section-label"><Sparkles size={16} /><b>Intelligence summary</b><span className="subtle-tag">Local model</span></div><div className="analysis-grid"><div><small>Suggested category</small><strong>{categories[ticket.analysis.suggested_category]}</strong><span>{percent(ticket.analysis.confidence)} model score · uncalibrated</span></div><div><small>Sentiment</small><strong className="capitalize">{ticket.sentiment}</strong><span>Keyword heuristic</span></div><div><small>Review deadline</small><strong className={slaLabel(ticket) === 'SLA overdue' ? 'text-danger' : ''}>{slaLabel(ticket)}</strong><span>{formatDate(ticket.due_at)}</span></div></div>
        {ticket.analysis.needs_review && <div className="callout amber">The classifier is uncertain. Confirm the category before continuing.</div>}
        <div className="reason-list"><Clock3 size={14} /><span>{ticket.analysis.priority_reasons.join(' · ')}</span></div>
        {ticket.analysis.top_features.length > 0 && <div className="feature-tags"><span>Signals</span>{ticket.analysis.top_features.map(f => <span className="feature-tag" key={f.term}>{f.term}</span>)}</div>}
      </section>
      <details className="triage-settings"><summary><UserRound size={16} />Routing & ownership<span>Edit</span></summary><div className="form-grid triage-form"><label>Category<select value={category} onChange={e => setCategory(e.target.value as Category)}>{Object.entries(categories).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select></label><label>Priority<select value={priority} onChange={e => setPriority(e.target.value as Priority)}>{['critical', 'high', 'medium', 'low'].map(p => <option key={p}>{p}</option>)}</select></label><label className="span-two">Assigned to<input minLength={2} maxLength={100} value={assignee} onChange={e => setAssignee(e.target.value)} /></label></div><button className="button secondary small-button" disabled={!!busy || !triageChanged || assignee.trim().length < 2} onClick={() => void act('routing', '', 'PATCH', { category, priority, assignee })}>{busy === 'routing' ? <Spinner /> : <Save size={14} />}Save routing</button><p className="fine-print">Changing category clears the current draft and approval.</p></details>
      <div className="detail-tabs" role="tablist"><button role="tab" aria-selected={tab === 'response'} className={tab === 'response' ? 'active' : ''} onClick={() => setTab('response')}><FileText size={16} />Response workspace</button><button role="tab" aria-selected={tab === 'activity'} className={tab === 'activity' ? 'active' : ''} onClick={() => setTab('activity')}><History size={16} />Activity <span>{audit.length}</span></button></div>
      {tab === 'activity' ? <div className="audit-list">{audit.map(event => <div className="audit-event" key={event.id}><span className="audit-dot"><Check size={12} /></span><div><b className="capitalize">{event.action.replaceAll('_', ' ')}</b><p>{event.actor} · {formatDate(event.created_at)}</p>{typeof event.details.note === 'string' && event.details.note && <blockquote>{event.details.note}</blockquote>}</div></div>)}</div> : <>
        <div className="draft-toolbar"><div><h3>Suggested response</h3><p>{ticket.draft_meta ? `${ticket.draft_meta.provider === 'openai' ? 'LLM-assisted draft' : 'Policy extracts'} · ${ticket.draft_meta.citations.length} sources` : 'Retrieve relevant policies and prepare a draft.'}</p></div><button className="button primary small-button" disabled={!!busy || ticket.status === 'resolved' || !!changed} onClick={() => void act('generate', '/draft', 'POST', {})}>{busy === 'generate' ? <Spinner /> : ticket.draft_text ? <RefreshCw size={15} /> : <Sparkles size={15} />}{ticket.draft_text ? 'Regenerate' : 'Generate draft'}</button></div>
        {!ticket.draft_text ? <div className="draft-empty"><FileText size={30} /><p>Your first draft starts with the right sources.</p><span>Generate a response to inspect its policy evidence.</span></div> : <>
          {ticket.draft_meta?.fallback_reason && <div className="callout amber">{ticket.draft_meta.fallback_reason}</div>}
          <label className="sr-only" htmlFor="draft-editor">Response draft</label><textarea id="draft-editor" className="draft-editor" value={draft} disabled={ticket.status === 'resolved' || !!busy} onChange={e => setDraft(e.target.value)} rows={12} maxLength={10000} />
          <div className="draft-footer"><span><ShieldCheck size={14} />Human approval required · nothing is sent automatically</span>{changed && <button className="text-button" disabled={!!busy || draft.trim().length < 20} onClick={() => void act('save', '/draft', 'PUT', { text: draft })}>{busy === 'save' ? <Spinner /> : <Save size={14} />}Save edits</button>}</div>
          <div className="sources"><span className="eyebrow">POLICY EVIDENCE</span>{ticket.draft_meta?.citations.map(citation => <details className="source-card" key={citation.chunk_id}><summary><FileText size={16} /><div><b>{citation.title}</b><span>{citation.policy_id} · v{citation.version} · {percent(citation.score)} lexical similarity</span></div><ArrowUpRight size={15} /></summary><div className="source-content"><p>{citation.content}</p><small>{citation.source}</small></div></details>)}{ticket.draft_meta?.citations.length === 0 && <p className="muted">No policy matched. Add a relevant policy in Knowledge base and regenerate.</p>}</div>
          {ticket.status === 'in_review' && <section className="review-box"><h3>Ready for a human check.</h3><p>Read the source excerpts and verify every claim before approval. Approval records your review; it does not send a message.</p><label>Your name<input value={reviewer} onChange={e => setReviewer(e.target.value)} minLength={2} maxLength={100} placeholder="Reviewer name" /></label><label>Review note <span className="muted">(optional)</span><input value={note} onChange={e => setNote(e.target.value)} maxLength={2000} placeholder="What did you verify or what needs changing?" /></label><div className="review-actions"><button className="button secondary" disabled={!!busy || !!changed || reviewer.trim().length < 2} onClick={() => void act('reject', '/review', 'POST', { decision: 'reject', reviewer, note })}><X size={15} />Return for revision</button><button className="button primary" disabled={!!busy || !!changed || reviewer.trim().length < 2 || !ticket.draft_meta?.citations.length} onClick={() => void act('approve', '/review', 'POST', { decision: 'approve', reviewer, note })}>{busy === 'approve' ? <Spinner /> : <CheckCheck size={16} />}Approve response</button></div>{changed && <p className="fine-print">Save your edits before reviewing.</p>}</section>}
          {ticket.status === 'approved' && <div className="approved-banner"><ShieldCheck size={20} /><div><b>Approved by {ticket.approved_by}</b><span>Response reviewed. No message has been sent.</span></div><button className="button primary small-button" disabled={!!busy || !!changed} onClick={() => void act('resolve', '', 'PATCH', { status: 'resolved' })}>Mark resolved</button></div>}
        </>}
        {ticket.status === 'resolved' && <div className="approved-banner"><CheckCheck size={22} /><div><b>This conversation is resolved.</b><span>The review history is preserved.</span></div><button className="text-button" disabled={!!busy} onClick={() => void act('reopen', '', 'PATCH', { status: 'open' })}>Reopen</button></div>}
      </>}
    </div>}
  </Modal>;
}
