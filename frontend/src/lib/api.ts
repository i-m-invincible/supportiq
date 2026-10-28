let workspaceKey = '';
export function setWorkspaceKey(key: string) { workspaceKey = key; }
export class ApiError extends Error { constructor(message: string, public status: number) { super(message); } }
const base = import.meta.env.VITE_API_BASE_URL || '';
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${base}/api/v1${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(workspaceKey ? { 'X-API-Key': workspaceKey } : {}), ...options.headers },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const detail = typeof error.detail === 'string' ? error.detail : error.detail?.[0]?.msg;
    throw new ApiError(detail || `Request failed (${response.status}).`, response.status);
  }
  return response.json();
}
export function mutation<T>(path: string, method: string, body: unknown) { return api<T>(path, { method, body: JSON.stringify(body) }); }
export async function exportCSV() {
  const response = await fetch(`${base}/api/v1/export/tickets.csv`, { headers: workspaceKey ? { 'X-API-Key': workspaceKey } : {} });
  if (!response.ok) throw new Error('Export failed. Check your workspace connection.');
  const url = URL.createObjectURL(await response.blob());
  const a = document.createElement('a'); a.href = url; a.download = 'supportiq-tickets.csv'; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
