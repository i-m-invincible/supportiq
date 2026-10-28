import { useEffect, useState, type FormEvent } from 'react';
import { BookOpen, FileText, Pencil, Plus, Search, ShieldCheck } from 'lucide-react';
import { api, mutation } from '../lib/api';
import { categories, percent, type Category, type Citation, type Policy } from '../lib/types';
import { Empty, ErrorBox, Modal, Spinner } from './Common';

export default function Knowledge() {
  const [items, setItems] = useState<Policy[]>([]); const [matches, setMatches] = useState<Citation[]>([]);
  const [query, setQuery] = useState(''); const [searched, setSearched] = useState(false); const [error, setError] = useState(''); const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Policy | 'new' | null>(null); const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true);
    const timer = setTimeout(() => {
      api<{ items: Policy[]; matches: Citation[] }>(`/policies?q=${encodeURIComponent(query)}`, { signal: controller.signal })
        .then(r => { setItems(r.items); setMatches(r.matches); setSearched(!!query.trim()); setError(''); })
        .catch(e => { if (e.name !== 'AbortError') setError(e.message); })
        .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    }, 200);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [query, revision]);
  return <>
    <div className="knowledge-intro"><div className="knowledge-icon"><BookOpen size={27} /></div><div><h3>Better answers begin with trusted sources.</h3><p>Search the handbook, inspect retrieval matches, or add your own policies.</p></div><button className="button primary" onClick={() => setEditing('new')}><Plus size={16} />Add policy</button></div>
    <div className="callout neutral"><ShieldCheck size={17} /><span>The 12 sample policies are fictional. Replace them with reviewed organizational policies before using real customer data.</span></div>
    <div className="knowledge-toolbar"><label className="search-field"><Search size={17} /><input value={query} maxLength={500} onChange={e => setQuery(e.target.value)} placeholder="Try ‘duplicate card charge’ or ‘locked out of banking’" aria-label="Search policy knowledge base" /></label><span className="muted">{items.filter(p => p.active).length} active policies</span></div>
    {error && <ErrorBox message={error} onRetry={() => setRevision(x => x + 1)} />}
    {loading ? <div className="loading-panel"><Spinner /> Searching knowledge…</div> : searched ? <div className="retrieval-results"><h3>Relevant policy excerpts <span className="subtle-tag">{matches.length} matches</span></h3>{matches.length ? matches.map(match => <article className="card policy-match" key={match.chunk_id}><div className="policy-card-top"><span className="policy-category">{categories[match.category]}</span><span className="subtle-tag">{percent(match.score)} similarity</span></div><h3>{match.title}</h3><p>{match.content}</p><div className="policy-card-bottom"><span>{match.policy_id} · v{match.version}</span><button className="text-button" onClick={() => setEditing(items.find(p => p.id === match.policy_id) || null)}><Pencil size={14} />View / edit</button></div></article>) : <Empty title="No relevant policy found.">Try a more specific phrase, or add a policy that covers this topic.</Empty>}</div> : <div className="policy-grid">{items.map(policy => <article className={`card policy-card ${!policy.active ? 'inactive-policy' : ''}`} key={policy.id}><div className="policy-card-top"><span className="policy-file-icon"><FileText size={20} /></span><span className="subtle-tag">{policy.active ? `v${policy.version} · Active` : 'Inactive'}</span></div><span className="policy-category">{categories[policy.category]}</span><h3>{policy.title}</h3><p>{policy.body.split('\n')[0]}</p><div className="policy-card-bottom"><span>{policy.id}</span><button className="text-button" onClick={() => setEditing(policy)}><Pencil size={14} />View / edit</button></div></article>)}</div>}
    {editing && <PolicyEditor policy={editing === 'new' ? null : editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); setRevision(x => x + 1); }} />}
  </>;
}

function PolicyEditor({ policy, onClose, onSaved }: { policy: Policy | null; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({ title: policy?.title || '', category: policy?.category || 'credit_card' as Category, body: policy?.body || '', source: policy?.source || 'Internal knowledge base', active: policy?.active ?? true });
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  async function submit(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError('');
    try {
      const { active, ...create } = form;
      await mutation(`/policies${policy ? '/' + policy.id : ''}`, policy ? 'PUT' : 'POST', policy ? { ...form, expected_version: policy.version } : create);
      onSaved();
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <Modal title={policy ? `Policy / ${policy.id}` : 'Add a policy'} onClose={onClose} busy={busy}><form className="form-body" onSubmit={submit}><h2>{policy ? 'Keep your sources current.' : 'Add a trusted source.'}</h2><p className="muted">Use plain-language policy text. Blank lines create retrieval chunks.</p>{error && <ErrorBox message={error} />}<label>Title<input required minLength={5} maxLength={180} value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></label><label>Category<select value={form.category} onChange={e => setForm({ ...form, category: e.target.value as Category })}>{Object.entries(categories).map(([key, name]) => <option key={key} value={key}>{name}</option>)}</select></label><label>Policy text<textarea required minLength={40} maxLength={12000} rows={9} value={form.body} onChange={e => setForm({ ...form, body: e.target.value })} /></label><label>Source / document reference<input required maxLength={240} minLength={2} value={form.source} onChange={e => setForm({ ...form, source: e.target.value })} /></label>{policy && <label className="checkbox-label"><input type="checkbox" checked={form.active} onChange={e => setForm({ ...form, active: e.target.checked })} />Active and available for retrieval</label>}<p className="fine-print">A policy update prevents approval of older drafts that cite it until they are regenerated.</p><div className="modal-actions"><button type="button" className="button secondary" onClick={onClose} disabled={busy}>Cancel</button><button className="button primary" disabled={busy}>{busy ? <Spinner /> : <ShieldCheck size={16} />}Save policy</button></div></form></Modal>;
}
