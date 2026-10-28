import { useEffect, useRef, type ReactNode } from 'react';
import { AlertCircle, LoaderCircle, X, ArrowUpRight } from 'lucide-react';
import type { Priority, Status, Ticket } from '../lib/types';
import { categories, statuses, relativeDate, slaLabel } from '../lib/types';

export function PriorityBadge({ value }: { value: Priority }) { return <span className={`badge priority ${value}`}><span className="dot" />{value}</span>; }
export function StatusBadge({ value }: { value: Status }) { return <span className={`badge status ${value}`}>{statuses[value]}</span>; }
export function Spinner() { return <LoaderCircle size={17} className="spin" aria-label="Loading" />; }
export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) { return <div role="alert" className="error-box"><AlertCircle size={18} /><span>{message}</span>{onRetry && <button className="text-button" onClick={onRetry}>Retry</button>}</div>; }
export function Empty({ title, children }: { title: string; children?: ReactNode }) { return <div className="empty-state"><div className="empty-symbol">↗</div><h3>{title}</h3><p>{children}</p></div>; }
export function Avatar({ name, small = false }: { name: string; small?: boolean }) { return <span className={`avatar ${small ? 'small' : ''}`}>{name.split(' ').map(s => s[0]).slice(0, 2).join('')}</span>; }
export function Modal({ title, onClose, children, wide = false, busy = false }: { title: string; onClose: () => void; children: ReactNode; wide?: boolean; busy?: boolean }) {
  const root = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose); closeRef.current = onClose;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    root.current?.focus();
    function key(event: KeyboardEvent) {
      if (event.key === 'Escape' && !busy) closeRef.current();
      if (event.key !== 'Tab') return;
      const elements = Array.from(root.current?.querySelectorAll<HTMLElement>('button:not([disabled]), a[href], input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex="0"]') || []).filter(el => el.offsetParent !== null);
      const first = elements[0], last = elements[elements.length - 1];
      if (event.shiftKey && (document.activeElement === first || document.activeElement === root.current)) { event.preventDefault(); last?.focus(); }
      if (!event.shiftKey && (document.activeElement === last || document.activeElement === root.current)) { event.preventDefault(); first?.focus(); }
    }
    document.addEventListener('keydown', key);
    return () => { document.removeEventListener('keydown', key); document.body.style.overflow = overflow; previous?.focus(); };
  }, [busy]);
  return <div className={`modal-backdrop ${wide ? 'drawer-backdrop' : ''}`} onMouseDown={e => { if (e.target === e.currentTarget && !busy) onClose(); }}>
    <div ref={root} role="dialog" aria-modal="true" aria-label={title} tabIndex={-1} className={wide ? 'drawer' : 'modal'}>
      <div className="modal-heading"><span className="eyebrow">{title}</span><button className="icon-button" aria-label="Close dialog" onClick={onClose} disabled={busy}><X size={20} /></button></div>
      {children}
    </div>
  </div>;
}
export function TicketTable({ tickets, onSelect, compact = false }: { tickets: Ticket[]; onSelect: (id: string) => void; compact?: boolean }) {
  return <div className="table-scroll"><table className="ticket-table"><thead><tr><th>Conversation</th><th>Category</th><th>Priority</th><th>Status</th>{!compact && <th>Review SLA</th>}<th className="align-right">Received</th></tr></thead><tbody>
    {tickets.map(ticket => <tr key={ticket.id}>
      <td><div className="ticket-cell"><Avatar name={ticket.customer_name} /><div><button className="ticket-link" onClick={() => onSelect(ticket.id)}>{ticket.subject}<ArrowUpRight size={13} /></button><span className="ticket-byline">{ticket.customer_name}<span>·</span>{ticket.id}</span></div></div></td>
      <td><span className="category-text">{categories[ticket.category]}</span></td><td><PriorityBadge value={ticket.priority} /></td><td><StatusBadge value={ticket.status} /></td>
      {!compact && <td className={slaLabel(ticket) === 'SLA overdue' ? 'text-danger' : 'muted'}>{slaLabel(ticket)}</td>}
      <td className="align-right muted nowrap">{relativeDate(ticket.created_at)}</td>
    </tr>)}
  </tbody></table></div>;
}
