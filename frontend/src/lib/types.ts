export type Category = 'credit_card' | 'bank_account' | 'money_transfer' | 'credit_reporting' | 'debt_collection' | 'loan' | 'other';
export type Priority = 'critical' | 'high' | 'medium' | 'low';
export type Status = 'open' | 'in_review' | 'approved' | 'resolved';
export type View = 'overview' | 'inbox' | 'knowledge' | 'analytics' | 'models';
export interface Analysis {
  category: Category; suggested_category: Category; confidence: number; needs_review: boolean;
  top_features: { term: string; contribution: number }[]; probabilities: Record<string, number>;
  priority: Priority; priority_reasons: string[]; sentiment: string; threshold: number;
  human_category_override?: Category;
}
export interface Citation { policy_id: string; title: string; category: Category; content: string; chunk_id: string; version: number; source: string; score: number }
export interface Ticket {
  id: string; customer_name: string; subject: string; body: string; channel: string;
  status: Status; assignee: string; category: Category; priority: Priority; sentiment: string;
  analysis: Analysis; created_at: string; updated_at: string; due_at: string; version: number;
  draft_text: string | null; approved_by: string | null; approved_at: string | null;
  draft_meta: { provider: string; citations: Citation[]; grounded: boolean; fallback_reason: string | null; warning: string } | null;
}
export interface Policy { id: string; title: string; category: Category; body: string; source: string; active: boolean; version: number; updated_at: string }
export interface Analytics {
  total: number; active: number; awaiting_review: number; critical: number; overdue: number; approved: number; resolved: number; mean_confidence: number;
  categories: Record<string, number>; priorities: Record<string, number>; sentiments: Record<string, number>; statuses: Record<string, number>;
  trend: { date: string; total: number; negative: number }[];
}
export interface Evaluation { samples: number; accuracy: number; macro_f1: number; coverage_at_threshold: number; accuracy_on_accepted: number | null; confusion_matrix: number[][] }
export interface Meta { demo_data: boolean; draft_provider: string; auth_enabled: boolean; classification_threshold: number; classifier: { model: string; dataset_kind: string; train_samples: number; sklearn_version: string; test: Evaluation; validation: Evaluation; caveat: string } }
export interface Audit { id: number; action: string; actor: string; details: Record<string, unknown>; created_at: string }
export const categories: Record<Category, string> = { credit_card: 'Card & billing', bank_account: 'Accounts & access', money_transfer: 'Payments & transfers', credit_reporting: 'Credit reporting', debt_collection: 'Debt collection', loan: 'Loans & mortgages', other: 'Needs classification' };
export const statuses: Record<Status, string> = { open: 'Open', in_review: 'In review', approved: 'Approved', resolved: 'Resolved' };
export const palette = ['#287c65', '#839f93', '#c5a67b', '#9e91b2', '#7d9fb8', '#d1c594', '#d1d5d1'];
export const categoryLabel = (value: string) => categories[value as Category] || value;
export const percent = (value: number) => `${Math.round(value * 100)}%`;
export const formatDate = (value: string) => new Date(value).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
export function relativeDate(value: string) {
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60000));
  return minutes < 60 ? `${minutes}m ago` : minutes < 1440 ? `${Math.floor(minutes / 60)}h ago` : `${Math.floor(minutes / 1440)}d ago`;
}
export function slaLabel(ticket: Ticket) {
  if (['approved', 'resolved'].includes(ticket.status)) return 'Reviewed';
  const minutes = Math.ceil((new Date(ticket.due_at).getTime() - Date.now()) / 60000);
  return minutes < 0 ? 'SLA overdue' : minutes < 60 ? `${minutes}m remaining` : `${Math.ceil(minutes / 60)}h remaining`;
}
