'use client';
import { useEffect, useState, useCallback, useRef } from 'react';
import { api } from '@/lib/api';
import { DiscoveryStats, DiscoveryRun, DiscoverySeed, DiscoveredSource } from '@/lib/types';
import { Header } from '@/components/layout/Header';
import {
  Search, Plus, Trash2, RefreshCw, Play, Clock, CheckCircle, XCircle,
  Loader2, ExternalLink, Download, Eye, EyeOff, Zap,
} from 'lucide-react';

type Tab = 'candidates' | 'seeds' | 'runs';

const STATUS_COLORS: Record<string, string> = {
  candidate: 'bg-gray-500/20 text-gray-400',
  tested: 'bg-blue-500/20 text-blue-400',
  benchmarked: 'bg-purple-500/20 text-purple-400',
  approved: 'bg-green-500/20 text-green-400',
  imported: 'bg-teal-500/20 text-teal-400',
  ignored: 'bg-gray-500/10 text-gray-600',
  dead: 'bg-red-500/20 text-red-400',
};

const TYPE_COLORS: Record<string, string> = {
  torznab: 'bg-blue-500/20 text-blue-300',
  newznab: 'bg-indigo-500/20 text-indigo-300',
  rss: 'bg-orange-500/20 text-orange-300',
  stremio_manifest: 'bg-pink-500/20 text-pink-300',
  torrentio_family: 'bg-pink-500/20 text-pink-300',
  comet_family: 'bg-violet-500/20 text-violet-300',
  mediafusion_family: 'bg-cyan-500/20 text-cyan-300',
  jackett: 'bg-yellow-500/20 text-yellow-300',
  prowlarr: 'bg-green-500/20 text-green-300',
  nzbhydra: 'bg-teal-500/20 text-teal-300',
  generic_http: 'bg-gray-500/20 text-gray-300',
  unknown: 'bg-gray-500/10 text-gray-600',
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[status] ?? 'bg-gray-500/20 text-gray-400'}`}>
      {status}
    </span>
  );
}

function TypeBadge({ type }: { type: string }) {
  return (
    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${TYPE_COLORS[type] ?? 'bg-gray-500/20 text-gray-400'}`}>
      {type}
    </span>
  );
}

function RunStatusIcon({ status }: { status: string }) {
  if (status === 'running') return <Loader2 size={12} className="animate-spin text-blue-400" />;
  if (status === 'completed') return <CheckCircle size={12} className="text-green-400" />;
  if (status === 'failed') return <XCircle size={12} className="text-red-400" />;
  return <Clock size={12} className="text-gray-400" />;
}

function ScoreCell({ value, label }: { value: number | null | undefined; label: string }) {
  if (value == null) return <span className="text-gray-600 text-xs">—</span>;
  const color = value >= 60 ? 'text-green-400' : value >= 30 ? 'text-yellow-400' : 'text-red-400';
  return (
    <div className="text-right">
      <span className={`text-sm font-semibold ${color}`}>{value.toFixed(0)}</span>
      <span className="text-xs text-gray-600 ml-0.5">{label}</span>
    </div>
  );
}

// ── Stats Row ──────────────────────────────────────────────────────────────

function StatsRow({ stats }: { stats: DiscoveryStats }) {
  const cards = [
    { label: 'Total', value: stats.total_candidates, color: 'text-gray-300' },
    { label: 'Tested', value: stats.tested, color: 'text-blue-400' },
    { label: 'Benchmarked', value: stats.benchmarked, color: 'text-purple-400' },
    { label: 'Approved', value: stats.approved, color: 'text-green-400' },
    { label: 'Imported', value: stats.imported, color: 'text-teal-400' },
    { label: 'Ignored', value: stats.ignored, color: 'text-gray-600' },
    { label: 'Dead', value: stats.dead, color: 'text-red-400' },
  ];
  return (
    <div className="grid grid-cols-4 lg:grid-cols-7 gap-3">
      {cards.map(c => (
        <div key={c.label} className="bg-gray-800 rounded-lg border border-gray-700 p-3 text-center">
          <div className={`text-2xl font-bold ${c.color}`}>{c.value}</div>
          <div className="text-xs text-gray-500 mt-0.5">{c.label}</div>
        </div>
      ))}
    </div>
  );
}

// ── Candidates Table ────────────────────────────────────────────────────────

function CandidatesTab({
  sources, onRefresh,
}: { sources: DiscoveredSource[]; onRefresh: () => void }) {
  const [actingOn, setActingOn] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');

  const filtered = sources.filter(s => {
    if (statusFilter && s.status !== statusFilter) return false;
    if (search && !s.url.toLowerCase().includes(search.toLowerCase()) &&
        !(s.name?.toLowerCase().includes(search.toLowerCase()))) return false;
    return true;
  });

  const act = async (id: string, action: () => Promise<unknown>) => {
    setActingOn(id);
    try { await action(); onRefresh(); } finally { setActingOn(null); }
  };

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <input
          className="bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 w-52"
          placeholder="Search URL or name…"
          value={search} onChange={e => setSearch(e.target.value)}
        />
        <select
          className="bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-300 focus:outline-none"
          value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
        >
          <option value="">All Status</option>
          {['candidate','tested','benchmarked','approved','imported','ignored','dead'].map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <span className="text-xs text-gray-500">{filtered.length} sources</span>
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <Search size={32} className="mx-auto mb-3 opacity-30" />
          <p>No discovered sources yet.</p>
          <p className="text-xs mt-1">Add seeds and run discovery to find sources.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-700">
                <th className="pb-2 font-medium">URL / Name</th>
                <th className="pb-2 font-medium">Type</th>
                <th className="pb-2 font-medium">Status</th>
                <th className="pb-2 font-medium text-right">ITA</th>
                <th className="pb-2 font-medium text-right">GER</th>
                <th className="pb-2 font-medium text-right">Overall</th>
                <th className="pb-2 font-medium text-right">ms</th>
                <th className="pb-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/50">
              {filtered.map(s => (
                <tr key={s.id} className="hover:bg-gray-700/20 transition-colors">
                  <td className="py-2 pr-3 max-w-xs">
                    <div className="font-medium text-white truncate">{s.name || s.url}</div>
                    <a href={s.url} target="_blank" rel="noopener noreferrer"
                      className="text-xs text-gray-500 hover:text-blue-400 flex items-center gap-0.5 transition-colors">
                      <span className="truncate max-w-[200px]">{s.url}</span>
                      <ExternalLink size={9} />
                    </a>
                  </td>
                  <td className="py-2 pr-3"><TypeBadge type={s.detected_type} /></td>
                  <td className="py-2 pr-3"><StatusBadge status={s.status} /></td>
                  <td className="py-2 pr-3"><ScoreCell value={s.italian_score} label="%" /></td>
                  <td className="py-2 pr-3"><ScoreCell value={s.german_score} label="%" /></td>
                  <td className="py-2 pr-3"><ScoreCell value={s.overall_score} label="" /></td>
                  <td className="py-2 pr-3 text-right text-xs text-gray-500">
                    {s.response_time_ms != null ? s.response_time_ms.toFixed(0) : '—'}
                  </td>
                  <td className="py-2">
                    <div className="flex items-center gap-1 justify-end">
                      {s.status === 'candidate' && (
                        <button
                          onClick={() => act(s.id, () => api.testDiscoveredSource(s.id))}
                          disabled={actingOn === s.id}
                          title="Test"
                          className="p-1 text-gray-500 hover:text-blue-400 transition-colors disabled:opacity-40"
                        >
                          <Zap size={13} />
                        </button>
                      )}
                      {(s.status === 'tested') && (
                        <button
                          onClick={() => act(s.id, () => api.benchmarkDiscoveredSource(s.id))}
                          disabled={actingOn === s.id}
                          title="Benchmark"
                          className="p-1 text-gray-500 hover:text-purple-400 transition-colors disabled:opacity-40"
                        >
                          <Play size={13} />
                        </button>
                      )}
                      {(s.status === 'benchmarked') && (
                        <button
                          onClick={() => act(s.id, () => api.approveDiscoveredSource(s.id))}
                          disabled={actingOn === s.id}
                          title="Approve"
                          className="p-1 text-gray-500 hover:text-green-400 transition-colors disabled:opacity-40"
                        >
                          <CheckCircle size={13} />
                        </button>
                      )}
                      {(s.status === 'approved') && (
                        <button
                          onClick={() => act(s.id, () => api.importDiscoveredSource(s.id))}
                          disabled={actingOn === s.id}
                          title="Import to Sources"
                          className="p-1 text-gray-500 hover:text-teal-400 transition-colors disabled:opacity-40"
                        >
                          <Download size={13} />
                        </button>
                      )}
                      {!['ignored','imported','dead'].includes(s.status) && (
                        <button
                          onClick={() => act(s.id, () => api.ignoreDiscoveredSource(s.id))}
                          disabled={actingOn === s.id}
                          title="Ignore"
                          className="p-1 text-gray-500 hover:text-gray-300 transition-colors disabled:opacity-40"
                        >
                          <EyeOff size={13} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Seeds Tab ───────────────────────────────────────────────────────────────

function SeedsTab({ seeds, onRefresh }: { seeds: DiscoverySeed[]; onRefresh: () => void }) {
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ url: '', label: '', seed_type: 'url' });
  const [saving, setSaving] = useState(false);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.createDiscoverySeed(form);
      setForm({ url: '', label: '', seed_type: 'url' });
      setShowForm(false);
      onRefresh();
    } finally {
      setSaving(false);
    }
  };

  const del = async (id: string) => {
    await api.deleteDiscoverySeed(id);
    onRefresh();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm text-gray-400">{seeds.length} seeds configured</span>
        <button
          onClick={() => setShowForm(v => !v)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white rounded text-sm font-medium transition-colors"
        >
          <Plus size={14} /> Add Seed
        </button>
      </div>

      {showForm && (
        <form onSubmit={save} className="bg-gray-900 rounded-lg border border-gray-700 p-4 mb-4 grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="block text-xs text-gray-400 mb-1">Seed URL</label>
            <input
              required
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
              placeholder="https://example.com/indexers"
              value={form.url} onChange={e => setForm(f => ({ ...f, url: e.target.value }))}
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Label (optional)</label>
            <input
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
              placeholder="My indexer list"
              value={form.label} onChange={e => setForm(f => ({ ...f, label: e.target.value }))}
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Seed Type</label>
            <select
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
              value={form.seed_type} onChange={e => setForm(f => ({ ...f, seed_type: e.target.value }))}
            >
              <option value="url">URL (web page to crawl)</option>
              <option value="github">GitHub repo</option>
              <option value="rss">RSS feed</option>
            </select>
          </div>
          <div className="col-span-2 flex gap-2 justify-end">
            <button type="button" onClick={() => setShowForm(false)} className="px-3 py-1.5 text-sm text-gray-400 hover:text-white transition-colors">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-medium transition-colors disabled:opacity-50">
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      )}

      {seeds.length === 0 ? (
        <div className="text-center py-10 text-gray-500">
          <p>No seeds configured.</p>
          <p className="text-xs mt-1">Add a seed URL to start autonomous discovery.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {seeds.map(seed => (
            <div key={seed.id} className="bg-gray-900/60 rounded-lg p-3 flex items-center gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-white text-sm font-medium truncate">{seed.label || seed.url}</span>
                  <span className="text-xs px-1.5 py-0.5 rounded bg-gray-700 text-gray-400">{seed.seed_type}</span>
                  {!seed.enabled && <span className="text-xs text-gray-600">disabled</span>}
                </div>
                {seed.label && <div className="text-xs text-gray-500 truncate mt-0.5">{seed.url}</div>}
                {seed.last_crawled && (
                  <div className="text-xs text-gray-600 mt-0.5">
                    Last crawled: {new Date(seed.last_crawled).toLocaleString()}
                  </div>
                )}
              </div>
              <button
                onClick={() => del(seed.id)}
                className="p-1 text-gray-500 hover:text-red-400 transition-colors shrink-0"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Runs Tab ────────────────────────────────────────────────────────────────

function RunsTab({ runs }: { runs: DiscoveryRun[] }) {
  if (runs.length === 0) {
    return <p className="text-gray-500 text-sm">No discovery runs yet. Click "Run Discovery" to start.</p>;
  }
  return (
    <div className="space-y-3">
      {runs.map(r => (
        <div key={r.id} className="bg-gray-900/60 rounded-lg p-3 text-xs space-y-1">
          <div className="flex items-center justify-between">
            <span className={`inline-flex items-center gap-1 font-medium ${
              r.status === 'completed' ? 'text-green-400' :
              r.status === 'running' ? 'text-blue-400' :
              r.status === 'failed' ? 'text-red-400' : 'text-gray-400'
            }`}>
              <RunStatusIcon status={r.status} /> {r.status}
            </span>
            <span className="text-gray-500">{new Date(r.started_at).toLocaleString()}</span>
          </div>
          {r.status === 'completed' && (
            <div className="text-gray-400">
              {r.seeds_crawled} seeds crawled · {r.candidates_found} candidates found
            </div>
          )}
          {r.notes && <div className="text-gray-500 truncate">{r.notes}</div>}
          {r.finished_at && (
            <div className="text-gray-600">Finished: {new Date(r.finished_at).toLocaleString()}</div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── Main Page ───────────────────────────────────────────────────────────────

export default function DiscoveryPage() {
  const [tab, setTab] = useState<Tab>('candidates');
  const [stats, setStats] = useState<DiscoveryStats | null>(null);
  const [sources, setSources] = useState<DiscoveredSource[]>([]);
  const [seeds, setSeeds] = useState<DiscoverySeed[]>([]);
  const [runs, setRuns] = useState<DiscoveryRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [st, src, sd, r] = await Promise.all([
        api.getDiscoveryStats(),
        api.getDiscoveredSources(),
        api.getDiscoverySeeds(),
        api.getDiscoveryRuns(),
      ]);
      setStats(st);
      setSources(src);
      setSeeds(sd);
      setRuns(r);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load discovery data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Poll while a run is active
  useEffect(() => {
    const hasActive = runs.some(r => r.status === 'pending' || r.status === 'running');
    if (!hasActive) return;
    const id = setInterval(load, 4000);
    return () => clearInterval(id);
  }, [runs, load]);

  const triggerRun = async () => {
    setTriggering(true);
    try {
      const run = await api.triggerDiscoveryRun();
      setRuns(prev => [run, ...prev]);
      setTab('runs');
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Failed to start discovery run');
    } finally {
      setTriggering(false);
    }
  };

  const TABS: { key: Tab; label: string }[] = [
    { key: 'candidates', label: `Candidates (${sources.length})` },
    { key: 'seeds', label: `Seeds (${seeds.length})` },
    { key: 'runs', label: `Runs (${runs.length})` },
  ];

  return (
    <>
      <Header title="Discovery" />
      <main className="flex-1 overflow-y-auto p-6 space-y-5">

        {/* Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={triggerRun}
            disabled={triggering || seeds.length === 0}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
          >
            <Search size={15} />
            {triggering ? 'Starting…' : 'Run Discovery'}
          </button>
          <button onClick={load} className="p-2 text-gray-400 hover:text-white transition-colors">
            <RefreshCw size={16} />
          </button>
          {seeds.length === 0 && (
            <span className="text-xs text-yellow-400">Add at least one seed URL to enable discovery.</span>
          )}
        </div>

        {error && (
          <div className="px-4 py-3 rounded-lg text-sm border bg-red-500/10 border-red-500/20 text-red-400">
            <span className="font-semibold">API error:</span> {error}
          </div>
        )}

        {/* Stats */}
        {stats && <StatsRow stats={stats} />}

        {/* Tabs */}
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-5">
          <div className="flex gap-1 mb-5 bg-gray-900/60 rounded-lg p-1 w-fit">
            {TABS.map(t => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  tab === t.key ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {loading ? (
            <p className="text-gray-500 text-sm animate-pulse">Loading…</p>
          ) : tab === 'candidates' ? (
            <CandidatesTab sources={sources} onRefresh={load} />
          ) : tab === 'seeds' ? (
            <SeedsTab seeds={seeds} onRefresh={load} />
          ) : (
            <RunsTab runs={runs} />
          )}
        </div>
      </main>
    </>
  );
}
