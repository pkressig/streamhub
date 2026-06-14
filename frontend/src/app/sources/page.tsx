'use client';
import { useEffect, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import { Source } from '@/lib/types';
import { SourceTable } from '@/components/sources/SourceTable';
import { SourceForm } from '@/components/sources/SourceForm';
import { Header } from '@/components/layout/Header';
import { Plus, RefreshCw } from 'lucide-react';

const STATUS_OPTIONS: Array<{ value: string; label: string }> = [
  { value: '', label: 'All Status' },
  { value: 'active', label: 'Active' },
  { value: 'degraded', label: 'Degraded' },
  { value: 'dead', label: 'Dead' },
  { value: 'unknown', label: 'Unknown' },
];

const TYPE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: '', label: 'All Types' },
  { value: 'torznab', label: 'Torznab' },
  { value: 'newznab', label: 'Newznab' },
  { value: 'rss', label: 'RSS' },
  { value: 'manifest', label: 'Manifest' },
  { value: 'generic_http', label: 'Generic HTTP' },
];

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [status, setStatus] = useState('');
  const [sourceType, setSourceType] = useState('');
  const [search, setSearch] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const s = await api.getSources({ status: status || undefined, source_type: sourceType || undefined });
      setSources(s);
    } finally {
      setLoading(false);
    }
  }, [status, sourceType]);

  useEffect(() => { load(); }, [load]);

  const filtered = sources.filter(s =>
    !search || s.name.toLowerCase().includes(search.toLowerCase()) || s.url.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <>
      <Header title="Sources" />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="flex flex-wrap items-center gap-3 mb-5">
          <input
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 w-56"
            placeholder="Search sources..."
            value={search} onChange={e => setSearch(e.target.value)}
          />
          <select
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
            value={status} onChange={e => setStatus(e.target.value)}
          >
            {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <select
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
            value={sourceType} onChange={e => setSourceType(e.target.value)}
          >
            {TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <button onClick={load} className="p-2 text-gray-400 hover:text-white transition-colors">
            <RefreshCw size={16} />
          </button>
          <div className="flex-1" />
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Plus size={16} /> Add Source
          </button>
        </div>

        <div className="bg-gray-800 rounded-lg border border-gray-700 p-5">
          {loading ? (
            <div className="text-gray-500 text-sm">Loading...</div>
          ) : (
            <SourceTable sources={filtered} onRefresh={load} />
          )}
        </div>
      </main>
      {showForm && <SourceForm onClose={() => setShowForm(false)} onCreated={load} />}
    </>
  );
}
