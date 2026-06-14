'use client';
import { useEffect, useState, useCallback, useRef } from 'react';
import { api } from '@/lib/api';
import { BenchmarkTitle, BenchmarkRun, Category, LanguageTarget } from '@/lib/types';
import { Header } from '@/components/layout/Header';
import { Plus, Play, Upload, Trash2, RefreshCw, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react';

const CATEGORIES: Category[] = ['movie', 'series', 'anime'];
const LANGUAGES: LanguageTarget[] = ['ita', 'ger', 'multi'];

const catColor: Record<string, string> = {
  movie: 'bg-blue-500/20 text-blue-400',
  series: 'bg-purple-500/20 text-purple-400',
  anime: 'bg-pink-500/20 text-pink-400',
};
const langColor: Record<string, string> = {
  ita: 'bg-green-500/20 text-green-400',
  ger: 'bg-yellow-500/20 text-yellow-400',
  multi: 'bg-gray-500/20 text-gray-400',
};

function RunStatusBadge({ status }: { status: string }) {
  const map: Record<string, { color: string; icon: React.ReactNode }> = {
    pending: { color: 'text-gray-400', icon: <Clock size={12} /> },
    running: { color: 'text-blue-400', icon: <Loader2 size={12} className="animate-spin" /> },
    completed: { color: 'text-green-400', icon: <CheckCircle size={12} /> },
    failed: { color: 'text-red-400', icon: <XCircle size={12} /> },
  };
  const s = map[status] ?? map.pending;
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium ${s.color}`}>
      {s.icon} {status}
    </span>
  );
}

export default function BenchmarksPage() {
  const [titles, setTitles] = useState<BenchmarkTitle[]>([]);
  const [runs, setRuns] = useState<BenchmarkRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [catFilter, setCatFilter] = useState('');
  const [langFilter, setLangFilter] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [importResult, setImportResult] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const [form, setForm] = useState({
    title: '', imdb_id: '', category: 'movie' as Category,
    language_target: 'multi' as LanguageTarget, year: '',
  });

  const [loadError, setLoadError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [t, r] = await Promise.all([
        api.getBenchmarkTitles({
          category: catFilter || undefined,
          language_target: langFilter || undefined,
        }),
        api.getBenchmarkRuns(),
      ]);
      setTitles(t);
      setRuns(r);
    } catch (err: unknown) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load benchmarks');
    } finally {
      setLoading(false);
    }
  }, [catFilter, langFilter]);

  useEffect(() => { load(); }, [load]);

  // Poll runs while any are pending/running
  useEffect(() => {
    const hasActive = runs.some(r => r.status === 'pending' || r.status === 'running');
    if (!hasActive) return;
    const id = setInterval(async () => {
      const r = await api.getBenchmarkRuns();
      setRuns(r);
    }, 3000);
    return () => clearInterval(id);
  }, [runs]);

  const triggerRun = async () => {
    setRunning(true);
    try {
      const run = await api.triggerBenchmarkRun();
      setRuns(prev => [run, ...prev]);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Failed to start benchmark run');
    } finally {
      setRunning(false);
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportResult(null);
    try {
      const res = await api.importBenchmarkTitles(file);
      setImportResult(`Imported ${res.imported} titles. Skipped: ${res.skipped}.${res.errors.length ? ` Errors: ${res.errors.slice(0, 3).join('; ')}` : ''}`);
      load();
    } catch (err: unknown) {
      setImportResult(`Error: ${err instanceof Error ? err.message : 'unknown'}`);
    }
    if (fileRef.current) fileRef.current.value = '';
  };

  const addTitle = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.createBenchmarkTitle({
      title: form.title,
      imdb_id: form.imdb_id || undefined,
      category: form.category,
      language_target: form.language_target,
      year: form.year ? parseInt(form.year) : undefined,
    });
    setForm({ title: '', imdb_id: '', category: 'movie', language_target: 'multi', year: '' });
    setShowAddForm(false);
    load();
  };

  const deleteTitle = async (id: string) => {
    await api.deleteBenchmarkTitle(id);
    load();
  };

  return (
    <>
      <Header title="Benchmarks" />
      <main className="flex-1 overflow-y-auto p-6 space-y-5">

        {/* Actions row */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={triggerRun}
            disabled={running || titles.length === 0}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
          >
            <Play size={15} />
            {running ? 'Starting…' : 'Run Benchmark'}
          </button>
          <button
            onClick={() => fileRef.current?.click()}
            className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Upload size={15} /> Import CSV / JSON
          </button>
          <input ref={fileRef} type="file" accept=".csv,.json" className="hidden" onChange={handleImport} />
          <button
            onClick={() => setShowAddForm(v => !v)}
            className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Plus size={15} /> Add Title
          </button>
          <button onClick={load} className="p-2 text-gray-400 hover:text-white transition-colors">
            <RefreshCw size={16} />
          </button>
        </div>

        {loadError && (
          <div className="px-4 py-3 rounded-lg text-sm border bg-red-500/10 border-red-500/20 text-red-400">
            <span className="font-semibold">API error:</span> {loadError}
          </div>
        )}

        {importResult && (
          <div className={`px-4 py-3 rounded-lg text-sm border ${importResult.startsWith('Error') ? 'bg-red-500/10 border-red-500/20 text-red-400' : 'bg-green-500/10 border-green-500/20 text-green-400'}`}>
            {importResult}
          </div>
        )}

        {/* Add title form */}
        {showAddForm && (
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-5">
            <h3 className="text-sm font-semibold text-gray-300 mb-4">Add Benchmark Title</h3>
            <form onSubmit={addTitle} className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <label className="block text-xs text-gray-400 mb-1">Title</label>
                <input
                  required
                  className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
                  value={form.title}
                  onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                  placeholder="e.g. Dark"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">IMDB ID</label>
                <input
                  className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
                  value={form.imdb_id}
                  onChange={e => setForm(f => ({ ...f, imdb_id: e.target.value }))}
                  placeholder="tt5753856"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Year</label>
                <input
                  type="number"
                  className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
                  value={form.year}
                  onChange={e => setForm(f => ({ ...f, year: e.target.value }))}
                  placeholder="2017"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Category</label>
                <select
                  className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
                  value={form.category}
                  onChange={e => setForm(f => ({ ...f, category: e.target.value as Category }))}
                >
                  {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Language Target</label>
                <select
                  className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
                  value={form.language_target}
                  onChange={e => setForm(f => ({ ...f, language_target: e.target.value as LanguageTarget }))}
                >
                  {LANGUAGES.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
              <div className="col-span-2 flex gap-2 justify-end">
                <button type="button" onClick={() => setShowAddForm(false)} className="px-3 py-1.5 text-sm text-gray-400 hover:text-white transition-colors">Cancel</button>
                <button type="submit" className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-medium transition-colors">Save</button>
              </div>
            </form>
          </div>
        )}

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

          {/* Titles table — 2/3 width */}
          <div className="lg:col-span-2 bg-gray-800 rounded-lg border border-gray-700 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-300">Benchmark Titles ({titles.length})</h2>
              <div className="flex gap-2">
                <select
                  className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-gray-300 focus:outline-none"
                  value={catFilter}
                  onChange={e => setCatFilter(e.target.value)}
                >
                  <option value="">All Categories</option>
                  {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
                <select
                  className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-gray-300 focus:outline-none"
                  value={langFilter}
                  onChange={e => setLangFilter(e.target.value)}
                >
                  <option value="">All Languages</option>
                  {LANGUAGES.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
            </div>
            {loading ? (
              <p className="text-gray-500 text-sm animate-pulse">Loading…</p>
            ) : titles.length === 0 ? (
              <div className="text-center py-10 text-gray-500">
                <p>No benchmark titles yet.</p>
                <p className="text-xs mt-1">Import a CSV/JSON or add titles manually.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-400 border-b border-gray-700">
                      <th className="pb-2 font-medium">Title</th>
                      <th className="pb-2 font-medium">Year</th>
                      <th className="pb-2 font-medium">Category</th>
                      <th className="pb-2 font-medium">Language</th>
                      <th className="pb-2 font-medium">IMDB</th>
                      <th className="pb-2"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-700/50">
                    {titles.map(t => (
                      <tr key={t.id} className="hover:bg-gray-700/30 transition-colors">
                        <td className="py-2 text-white font-medium">{t.title}</td>
                        <td className="py-2 text-gray-400">{t.year ?? '—'}</td>
                        <td className="py-2">
                          <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${catColor[t.category]}`}>{t.category}</span>
                        </td>
                        <td className="py-2">
                          <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${langColor[t.language_target]}`}>{t.language_target}</span>
                        </td>
                        <td className="py-2 text-gray-500 text-xs">{t.imdb_id ?? '—'}</td>
                        <td className="py-2 text-right">
                          <button
                            onClick={() => deleteTitle(t.id)}
                            className="p-1 text-gray-500 hover:text-red-400 transition-colors"
                          >
                            <Trash2 size={13} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Run history — 1/3 */}
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-5">
            <h2 className="text-sm font-semibold text-gray-300 mb-4">Run History</h2>
            {runs.length === 0 ? (
              <p className="text-gray-500 text-sm">No runs yet. Click "Run Benchmark" to start.</p>
            ) : (
              <div className="space-y-3">
                {runs.map(r => (
                  <div key={r.id} className="bg-gray-900/60 rounded-lg p-3 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <RunStatusBadge status={r.status} />
                      <span className="text-gray-500">{new Date(r.started_at).toLocaleString()}</span>
                    </div>
                    {r.status === 'completed' && (
                      <div className="text-gray-400">
                        {r.sources_tested} sources × {r.titles_tested} titles
                      </div>
                    )}
                    {r.notes && <div className="text-gray-500 truncate">{r.notes}</div>}
                    {r.finished_at && (
                      <div className="text-gray-600">
                        Finished: {new Date(r.finished_at).toLocaleString()}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </>
  );
}
