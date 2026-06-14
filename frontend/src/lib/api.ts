const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

import type { Source, SourceDetail, SourceCreate, SourceTest, Stats } from './types';

export const api = {
  getSources: (params?: { status?: string; source_type?: string }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set('status', params.status);
    if (params?.source_type) qs.set('source_type', params.source_type);
    const q = qs.toString();
    return request<Source[]>(`/api/sources${q ? `?${q}` : ''}`);
  },
  createSource: (data: SourceCreate) =>
    request<Source>('/api/sources', { method: 'POST', body: JSON.stringify(data) }),
  getSource: (id: string) => request<SourceDetail>(`/api/sources/${id}`),
  deleteSource: (id: string) => request<void>(`/api/sources/${id}`, { method: 'DELETE' }),
  testSource: (id: string) => request<SourceTest>(`/api/sources/${id}/test`, { method: 'POST' }),
  getStats: () => request<Stats>('/api/stats'),
  health: () => request<{ status: string; version: string }>('/api/health'),
};
