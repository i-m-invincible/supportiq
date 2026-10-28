import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api, mutation } from '../lib/api';
import type { Ticket } from '../lib/types';
import NewTicket from '../components/NewTicket';
import Inbox from '../components/Inbox';
import TicketDetail from '../components/TicketDetail';
import ModelLab from '../components/ModelLab';
import Knowledge from '../components/Knowledge';

vi.mock('../lib/api', () => ({ api: vi.fn(), mutation: vi.fn() }));

const ticket: Ticket = {
  id: 'T-TEST', customer_name: 'Demo Customer', subject: 'Duplicate card purchase', body: 'My credit card was charged twice for a purchase and I need the duplicate transaction reviewed.',
  channel: 'email', status: 'in_review', assignee: 'Unassigned', category: 'credit_card', priority: 'medium', sentiment: 'negative',
  analysis: { category: 'credit_card', suggested_category: 'credit_card', confidence: 0.8, needs_review: false, top_features: [{ term: 'card', contribution: 0.4 }], probabilities: { credit_card: 0.8, bank_account: 0.2 }, priority: 'medium', priority_reasons: ['Standard review'], sentiment: 'negative', threshold: 0.45 },
  created_at: new Date().toISOString(), updated_at: new Date().toISOString(), due_at: new Date(Date.now() + 86400000).toISOString(), version: 2,
  draft_text: 'Please use the secure card dispute form for a duplicate charge. [POL-CARD-01]',
  approved_by: null, approved_at: null,
  draft_meta: { provider: 'extractive', grounded: true, fallback_reason: null, warning: 'Review policy relevance.', citations: [{ policy_id: 'POL-CARD-01', title: 'Card disputes', category: 'credit_card', content: 'Use the secure card dispute form.', chunk_id: 'POL-CARD-01:1', version: 1, source: 'demo', score: 0.6 }] },
};
beforeEach(() => vi.resetAllMocks());

describe('support workflow', () => {
  it('creates a complaint and returns the analyzed ticket', async () => {
    vi.mocked(mutation).mockResolvedValue(ticket);
    const created = vi.fn();
    render(<NewTicket onClose={vi.fn()} onCreated={created} />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Customer name'), 'Jordan Lee');
    await user.type(screen.getByLabelText('Subject'), 'Duplicate card payment');
    await user.type(screen.getByLabelText('Complaint'), 'My card was charged twice for the same purchase yesterday.');
    await user.click(screen.getByRole('button', { name: 'Create & analyze' }));
    expect(mutation).toHaveBeenCalledWith('/tickets', 'POST', { customer_name: 'Jordan Lee', subject: 'Duplicate card payment', body: 'My card was charged twice for the same purchase yesterday.', channel: 'email' });
    await waitFor(() => expect(created).toHaveBeenCalledWith(ticket));
  });

  it('shows an API error without claiming a successful creation', async () => {
    vi.mocked(mutation).mockRejectedValue(new Error('Workspace key required.'));
    render(<NewTicket onClose={vi.fn()} onCreated={vi.fn()} />);
    fireEvent.change(screen.getByLabelText('Customer name'), { target: { value: 'Test Person' } });
    fireEvent.change(screen.getByLabelText('Subject'), { target: { value: 'A valid subject' } });
    fireEvent.change(screen.getByLabelText('Complaint'), { target: { value: 'This complaint has more than twenty characters.' } });
    fireEvent.submit(screen.getByRole('button', { name: 'Create & analyze' }).closest('form')!);
    expect(await screen.findByRole('alert')).toHaveTextContent('Workspace key required.');
  });

  it('filters the inbox through the API and opens a ticket', async () => {
    vi.mocked(api).mockResolvedValue({ items: [ticket], total: 1 });
    const select = vi.fn(); render(<Inbox revision={0} onSelect={select} />);
    await screen.findByRole('button', { name: 'Duplicate card purchase' });
    fireEvent.change(screen.getByLabelText('Filter priority'), { target: { value: 'critical' } });
    await waitFor(() => expect(api).toHaveBeenLastCalledWith(expect.stringContaining('priority=critical'), expect.any(Object)));
    await screen.findByRole('button', { name: 'Duplicate card purchase' });
    await userEvent.click(screen.getByRole('button', { name: 'Duplicate card purchase' }));
    expect(select).toHaveBeenCalledWith('T-TEST');
  });

  it('requires a reviewer and saved edits before approval', async () => {
    vi.mocked(api).mockImplementation(async (path) => path.endsWith('/audit') ? [] : ticket);
    vi.mocked(mutation).mockResolvedValue({ ...ticket, status: 'approved', approved_by: 'Jordan Lee', version: 3 });
    render(<TicketDetail id="T-TEST" onClose={vi.fn()} onChanged={vi.fn()} />);
    const approve = await screen.findByRole('button', { name: 'Approve response' });
    expect(approve).toBeDisabled();
    await userEvent.type(screen.getByLabelText('Your name'), 'Jordan Lee');
    expect(approve).toBeEnabled();
    fireEvent.change(screen.getByLabelText('Response draft'), { target: { value: ticket.draft_text + ' Thank you.' } });
    expect(approve).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Save edits' })).toBeEnabled();
    fireEvent.change(screen.getByLabelText('Response draft'), { target: { value: ticket.draft_text } });
    await userEvent.click(approve);
    expect(mutation).toHaveBeenCalledWith('/tickets/T-TEST/review', 'POST', { expected_version: 2, decision: 'approve', reviewer: 'Jordan Lee', note: '' });
    expect(await screen.findByText('Approved by Jordan Lee')).toBeInTheDocument();
    expect(screen.getByText('Response reviewed. No message has been sent.')).toBeInTheDocument();
  });

  it('keeps approval disabled when retrieval found no sources', async () => {
    vi.mocked(api).mockImplementation(async path => path.endsWith('/audit') ? [] : { ...ticket, draft_meta: { ...ticket.draft_meta, citations: [], grounded: false } });
    render(<TicketDetail id="T-TEST" onClose={vi.fn()} onChanged={vi.fn()} />);
    await screen.findByLabelText('Your name');
    await userEvent.type(screen.getByLabelText('Your name'), 'Jordan Lee');
    expect(screen.getByRole('button', { name: 'Approve response' })).toBeDisabled();
  });

  it('shows classification probabilities in the model playground', async () => {
    vi.mocked(mutation).mockResolvedValue(ticket.analysis);
    render(<ModelLab meta={null} />);
    await userEvent.click(screen.getByRole('button', { name: 'Analyze complaint' }));
    expect(await screen.findByText('Top model score: 80%. This is not a calibrated probability of correctness.')).toBeInTheDocument();
    expect(mutation).toHaveBeenCalledWith('/analyze', 'POST', expect.objectContaining({ text: expect.any(String) }));
  });

  it('opens policy editing and saves a versioned update', async () => {
    const policy = { id: 'POL-CARD-01', title: 'Disputed card charges', body: 'Use the secure dispute form to request review of a duplicate card charge.', category: 'credit_card', source: 'Demo handbook', active: true, version: 1, updated_at: new Date().toISOString() };
    vi.mocked(api).mockResolvedValue({ items: [policy], matches: [] }); vi.mocked(mutation).mockResolvedValue({ ...policy, version: 2 });
    render(<Knowledge />);
    await userEvent.click(await screen.findByRole('button', { name: 'View / edit' }));
    await userEvent.type(screen.getByLabelText('Title'), ' updated');
    await userEvent.click(screen.getByRole('button', { name: 'Save policy' }));
    expect(mutation).toHaveBeenCalledWith('/policies/POL-CARD-01', 'PUT', expect.objectContaining({ expected_version: 1, title: 'Disputed card charges updated' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });
});
