import type {
  Source, SourceDetail, SourceCreate, SourceTest, Stats,
  BenchmarkTitle, BenchmarkTitleCreate, BenchmarkRun, BenchmarkResult,
  ImportResponse, RankedSource,
  DiscoverySeed, DiscoverySeedCreate, DiscoveryRun, DiscoveredSource, DiscoveryStats, DiscoveryRejected,
  DiscoveryBenchmarkResult, AppSetting,
} from './types';

// Always use relative URLs so the browser calls the same host it loaded from.
// Next.js rewrites /api/* → http://backend:8000/api/* on the server side.
const BASE = '';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body?.detail || JSON.stringify(body) || detail;
    } catch {
      try { detail = await res.text() || detail; } catch { /* ignore */ }
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

async function upload<T>(path: string, file: File): Promise<T> {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch(`${BASE}${path}`, { method: 'POST', body: fd });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try { detail = (await res.json())?.detail || detail; } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  // Sources
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
  testSource: (id: string) =>
    request<SourceTest>(`/api/sources/${id}/test`, { method: 'POST' }),
  getStats: () => request<Stats>('/api/stats'),
  health: () => request<{ status: string; version: string }>('/api/health'),

  // Benchmarks
  getBenchmarkTitles: (params?: { category?: string; language_target?: string }) => {
    const qs = new URLSearchParams();
    if (params?.category) qs.set('category', params.category);
    if (params?.language_target) qs.set('language_target', params.language_target);
    const q = qs.toString();
    return request<BenchmarkTitle[]>(`/api/benchmarks/titles${q ? `?${q}` : ''}`);
  },
  createBenchmarkTitle: (data: BenchmarkTitleCreate) =>
    request<BenchmarkTitle>('/api/benchmarks/titles', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  deleteBenchmarkTitle: (id: string) =>
    request<void>(`/api/benchmarks/titles/${id}`, { method: 'DELETE' }),
  importBenchmarkTitles: (file: File) =>
    upload<ImportResponse>('/api/benchmarks/import', file),
  triggerBenchmarkRun: () =>
    request<BenchmarkRun>('/api/benchmarks/run', { method: 'POST' }),
  getBenchmarkRuns: () => request<BenchmarkRun[]>('/api/benchmarks/runs'),
  getBenchmarkResults: (params?: { source_id?: string; run_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.source_id) qs.set('source_id', params.source_id);
    if (params?.run_id) qs.set('run_id', params.run_id);
    const q = qs.toString();
    return request<BenchmarkResult[]>(`/api/benchmarks/results${q ? `?${q}` : ''}`);
  },

  // Rankings
  getRankings: () => request<RankedSource[]>('/api/rankings'),
  getRankingsItalian: () => request<RankedSource[]>('/api/rankings/italian'),
  getRankingsGerman: () => request<RankedSource[]>('/api/rankings/german'),
  getRankingsMovies: () => request<RankedSource[]>('/api/rankings/movies'),
  getRankingsSeries: () => request<RankedSource[]>('/api/rankings/series'),
  getRankingsAnime: () => request<RankedSource[]>('/api/rankings/anime'),

  // Discovery
  getDiscoveryStats: () => request<DiscoveryStats>('/api/discovery/stats'),
  getDiscoverySeeds: () => request<DiscoverySeed[]>('/api/discovery/seeds'),
  createDiscoverySeed: (data: DiscoverySeedCreate) =>
    request<DiscoverySeed>('/api/discovery/seeds', { method: 'POST', body: JSON.stringify(data) }),
  deleteDiscoverySeed: (id: string) =>
    request<void>(`/api/discovery/seeds/${id}`, { method: 'DELETE' }),
  getDiscoveryRuns: () => request<DiscoveryRun[]>('/api/discovery/runs'),
  triggerDiscoveryRun: () =>
    request<DiscoveryRun>('/api/discovery/runs', { method: 'POST' }),
  getDiscoveredSources: (params?: { status?: string; detected_type?: string }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set('status', params.status);
    if (params?.detected_type) qs.set('detected_type', params.detected_type);
    const q = qs.toString();
    return request<DiscoveredSource[]>(`/api/discovery/sources${q ? `?${q}` : ''}`);
  },
  testDiscoveredSource: (id: string) =>
    request<DiscoveredSource>(`/api/discovery/sources/${id}/test`, { method: 'POST' }),
  benchmarkDiscoveredSource: (id: string, mini = true) =>
    request<DiscoveredSource>(`/api/discovery/sources/${id}/benchmark?mini=${mini}`, { method: 'POST' }),
  getSourceBenchmarkHistory: (id: string) =>
    request<DiscoveryBenchmarkResult[]>(`/api/discovery/sources/${id}/benchmarks`),
  approveDiscoveredSource: (id: string) =>
    request<DiscoveredSource>(`/api/discovery/sources/${id}/approve`, { method: 'POST' }),
  rejectDiscoveredSource: (id: string, reason?: string) =>
    request<DiscoveredSource>(`/api/discovery/sources/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason: reason ?? '' }),
    }),
  importDiscoveredSource: (id: string) =>
    request<DiscoveredSource>(`/api/discovery/sources/${id}/import`, { method: 'POST' }),
  ignoreDiscoveredSource: (id: string) =>
    request<DiscoveredSource>(`/api/discovery/sources/${id}/ignore`, { method: 'POST' }),
  getDiscoveryRelationships: () => request<unknown[]>('/api/discovery/relationships'),
  getDiscoveryRejected: (params?: { limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.limit) qs.set('limit', String(params.limit));
    if (params?.offset) qs.set('offset', String(params.offset));
    const q = qs.toString();
    return request<DiscoveryRejected[]>(`/api/discovery/rejected${q ? `?${q}` : ''}`);
  },
  clearDiscoveryRejected: () => request<void>('/api/discovery/rejected', { method: 'DELETE' }),
  triggerCleanup: () => request<{ dispatched: boolean }>('/api/discovery/cleanup', { method: 'POST' }),

  // Settings
  getSettings: () => request<Record<string, string>>('/api/settings'),
  putSetting: (key: string, value: string) =>
    request<{ key: string; value: string }>(`/api/settings/${key}`, {
      method: 'PUT',
      body: JSON.stringify({ value }),
    }),
};
