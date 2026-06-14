'use client';
import { useState } from 'react';
import { Header } from '@/components/layout/Header';
import { SourceType } from '@/lib/types';
import { api } from '@/lib/api';
import { Play } from 'lucide-react';

const SOURCE_TYPES: SourceType[] = ['torznab', 'newznab', 'rss', 'manifest', 'generic_http'];

export default function TestingPage() {
  const [url, setUrl] = useState('');
  const [type, setType] = useState<SourceType>('generic_http');
  const [authKey, setAuthKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<null | { success: boolean; response_time_ms: number | null; http_status: number | null; notes: string | null }>(null);

  const runTest = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    try {
      const source = await api.createSource({ name: `__temp_${Date.now()}`, url, source_type: type, requires_auth: !!authKey, auth_key: authKey || undefined });
      const testResult = await api.testSource(source.id);
      setResult({ success: testResult.success, response_time_ms: testResult.response_time_ms, http_status: testResult.http_status, notes: testResult.notes });
      await api.deleteSource(source.id);
    } catch (err: unknown) {
      setResult({ success: false, response_time_ms: null, http_status: null, notes: err instanceof Error ? err.message : 'Unknown error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Header title="Testing" />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl space-y-5">
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-5">
            <h2 className="text-sm font-semibold text-gray-300 mb-4">Manual Source Test</h2>
            <form onSubmit={runTest} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">URL</label>
                <input
                  type="url"
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  placeholder="https://example.com/api"
                  value={url} onChange={e => setUrl(e.target.value)} required
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Source Type</label>
                <select
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  value={type} onChange={e => setType(e.target.value as SourceType)}
                >
                  {SOURCE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">API Key (optional)</label>
                <input
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  placeholder="Leave blank if not required"
                  value={authKey} onChange={e => setAuthKey(e.target.value)}
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                <Play size={15} />
                {loading ? 'Testing...' : 'Run Test'}
              </button>
            </form>
          </div>

          {result && (
            <div className={`bg-gray-800 rounded-lg border p-5 ${result.success ? 'border-green-500/30' : 'border-red-500/30'}`}>
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Test Result</h3>
              <dl className="space-y-2 text-sm">
                <div className="flex gap-3">
                  <dt className="text-gray-500 w-32">Status</dt>
                  <dd className={result.success ? 'text-green-400 font-medium' : 'text-red-400 font-medium'}>{result.success ? 'PASSED' : 'FAILED'}</dd>
                </div>
                <div className="flex gap-3">
                  <dt className="text-gray-500 w-32">Response Time</dt>
                  <dd className="text-gray-300">{result.response_time_ms != null ? `${result.response_time_ms}ms` : '—'}</dd>
                </div>
                <div className="flex gap-3">
                  <dt className="text-gray-500 w-32">HTTP Status</dt>
                  <dd className="text-gray-300">{result.http_status ?? '—'}</dd>
                </div>
                <div className="flex gap-3">
                  <dt className="text-gray-500 w-32">Notes</dt>
                  <dd className="text-gray-300">{result.notes ?? '—'}</dd>
                </div>
              </dl>
            </div>
          )}
        </div>
      </main>
    </>
  );
}
