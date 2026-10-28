import { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, Search, SlidersHorizontal } from 'lucide-react';
import { api } from '../lib/api';
import { categories, statuses, type Status, type Ticket } from '../lib/types';
import { Empty, ErrorBox, Spinner, TicketTable } from './Common';

export default function Inbox({ revision, onSelect, initialStatus = '', initialQuery = '' }: { revision: number; onSelect: (id: string) => void; initialStatus?: Status | ''; initialQuery?: string }) {
  const [q, setQ] = useState(initialQuery); const [status, setStatus] = useState<string>(initialStatus);
  const [priority, setPriority] = useState(''); const [category, setCategory] = useState('');
  const [offset, setOffset] = useState(0); const [items, setItems] = useState<Ticket[]>([]); const [total, setTotal] = useState(0);
  const [error, setError] = useState(''); const [busy, setBusy] = useState(true); const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setBusy(true);
    const timer = setTimeout(() => {
      const params = new URLSearchParams({ q, offset: String(offset), limit: '10' });
      if (status) params.set('status', status); if (priority) params.set('priority', priority); if (category) params.set('category', category);
      api<{ items: Ticket[]; total: number }>(`/tickets?${params}`, { signal: controller.signal })
        .then(result => { setItems(result.items); setTotal(result.total); setError(''); })
        .catch(e => { if (e.name !== 'AbortError') setError(e.message); })
        .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    }, 200);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [q, status, priority, category, offset, revision, retry]);
  return <div className="card inbox-card"><div className="inbox-tabs"><button className={!status ? 'active' : ''} onClick={() => { setStatus(''); setOffset(0); }}>All conversations</button>{Object.entries(statuses).map(([value, label]) => <button key={value} className={status === value ? 'active' : ''} onClick={() => { setStatus(value); setOffset(0); }}>{label}</button>)}</div>
    <div className="inbox-filters"><label className="search-field"><Search size={17} /><input aria-label="Search conversations" value={q} maxLength={200} onChange={e => { setQ(e.target.value); setOffset(0); }} placeholder="Search subject, customer, or ticket…" /></label><div className="filter-selects"><SlidersHorizontal size={16} /><select aria-label="Filter priority" value={priority} onChange={e => { setPriority(e.target.value); setOffset(0); }}><option value="">All priorities</option>{['critical', 'high', 'medium', 'low'].map(p => <option key={p}>{p}</option>)}</select><select aria-label="Filter category" value={category} onChange={e => { setCategory(e.target.value); setOffset(0); }}><option value="">All categories</option>{Object.entries(categories).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select></div></div>
    {error ? <ErrorBox message={error} onRetry={() => setRetry(x => x + 1)} /> : busy ? <div className="loading-panel"><Spinner /> Finding conversations…</div> : items.length ? <TicketTable tickets={items} onSelect={onSelect} /> : <Empty title="No conversations match.">Try another search or clear your filters.</Empty>}
    <div className="table-footer"><span>{total === 0 ? '0 conversations' : `${offset + 1}–${Math.min(offset + 10, total)} of ${total} conversations`}</span><div><button className="icon-button bordered" aria-label="Previous page" disabled={busy || offset === 0} onClick={() => setOffset(x => Math.max(0, x - 10))}><ChevronLeft size={16} /></button><button className="icon-button bordered" aria-label="Next page" disabled={busy || offset + 10 >= total} onClick={() => setOffset(x => x + 10)}><ChevronRight size={16} /></button></div></div>
  </div>;
}
