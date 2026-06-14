import type {
  Source, SourceDetail, SourceCreate, SourceTest, Stats,
  BenchmarkTitle, BenchmarkTitleCreate, BenchmarkRun, BenchmarkResult,
  ImportResponse, RankedSource,
} from './types';

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:13001';

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

async function upload<T>(path: string, file: File): Promise<T> {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch(`${BASE}${path}`, { method: 'POST', body: fd });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
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
};
