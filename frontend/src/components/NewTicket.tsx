import { useState, type FormEvent } from 'react';
import { ArrowUpRight, Sparkles } from 'lucide-react';
import { mutation } from '../lib/api';
import type { Ticket } from '../lib/types';
import { ErrorBox, Modal, Spinner } from './Common';

export default function NewTicket({ onClose, onCreated }: { onClose: () => void; onCreated: (ticket: Ticket) => void }) {
  const [form, setForm] = useState({ customer_name: '', subject: '', body: '', channel: 'email' });
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const update = (field: string, value: string) => setForm(f => ({ ...f, [field]: value }));
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('');
    try { onCreated(await mutation<Ticket>('/tickets', 'POST', form)); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  return <Modal title="New conversation" onClose={onClose} busy={busy}><form className="form-body" onSubmit={submit}>
    <div className="modal-title-icon"><Sparkles size={23} /></div><h2>Make the next step clear.</h2><p className="muted">Add a complaint. SupportIQ will classify it and surface review priorities.</p>
    {error && <ErrorBox message={error} />}
    <div className="form-grid"><label>Customer name<input required minLength={2} maxLength={100} value={form.customer_name} onChange={e => update('customer_name', e.target.value)} placeholder="e.g. Jordan Lee" /></label><label>Channel<select value={form.channel} onChange={e => update('channel', e.target.value)}><option value="email">Email</option><option value="chat">Live chat</option><option value="web">Web form</option><option value="phone">Phone</option></select></label></div>
    <label>Subject<input required minLength={5} maxLength={180} value={form.subject} onChange={e => update('subject', e.target.value)} placeholder="A short summary of the issue" /></label>
    <label>Complaint<textarea required minLength={20} maxLength={10000} rows={6} value={form.body} onChange={e => update('body', e.target.value)} placeholder="Describe what happened. Use synthetic information for this demo." /></label>
    <div className="form-note"><Sparkles size={15} /><span>Automatic category, sentiment and urgency analysis. Responses always require a person to approve.</span></div>
    <div className="modal-actions"><button type="button" className="button secondary" onClick={onClose} disabled={busy}>Cancel</button><button className="button primary" disabled={busy}>{busy ? <Spinner /> : <ArrowUpRight size={16} />}Create & analyze</button></div>
  </form></Modal>;
}
