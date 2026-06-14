'use client';
import { useState } from 'react';
import { SourceCreate, SourceType } from '@/lib/types';
import { api } from '@/lib/api';
import { X } from 'lucide-react';

const SOURCE_TYPES: SourceType[] = ['torznab', 'newznab', 'rss', 'manifest', 'generic_http'];

interface Props {
  onClose: () => void;
  onCreated: () => void;
}

export function SourceForm({ onClose, onCreated }: Props) {
  const [form, setForm] = useState<SourceCreate>({
    name: '',
    url: '',
    source_type: 'generic_http',
    requires_auth: false,
    auth_key: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload = { ...form };
      if (!payload.auth_key) delete payload.auth_key;
      await api.createSource(payload);
      onCreated();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="bg-gray-800 rounded-xl border border-gray-700 w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-white">Add Source</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white"><X size={20} /></button>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Name</label>
            <input
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              required placeholder="My Source"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">URL</label>
            <input
              type="url"
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              value={form.url} onChange={e => setForm(f => ({ ...f, url: e.target.value }))}
              required placeholder="https://example.com/api"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Source Type</label>
            <select
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              value={form.source_type} onChange={e => setForm(f => ({ ...f, source_type: e.target.value as SourceType }))}
            >
              {SOURCE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox" id="requires_auth" className="accent-blue-500"
              checked={form.requires_auth} onChange={e => setForm(f => ({ ...f, requires_auth: e.target.checked }))}
            />
            <label htmlFor="requires_auth" className="text-sm text-gray-400">Requires Authentication</label>
          </div>
          {form.requires_auth && (
            <div>
              <label className="block text-sm text-gray-400 mb-1">API Key</label>
              <input
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                value={form.auth_key || ''} onChange={e => setForm(f => ({ ...f, auth_key: e.target.value }))}
                placeholder="your-api-key"
              />
            </div>
          )}
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 py-2 rounded-lg border border-gray-700 text-gray-400 hover:text-white text-sm transition-colors">Cancel</button>
            <button type="submit" disabled={loading} className="flex-1 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors disabled:opacity-50">
              {loading ? 'Adding...' : 'Add Source'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
