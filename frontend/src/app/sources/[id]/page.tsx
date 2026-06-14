'use client';
import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { SourceDetail } from '@/lib/types';
import { Header } from '@/components/layout/Header';
import { StatusBadge, TypeBadge } from '@/components/ui/Badge';
import { StatusIndicator } from '@/components/ui/StatusIndicator';
import { ScoreBar } from '@/components/sources/ScoreBar';
import { ArrowLeft, TestTube, Trash2, ExternalLink } from 'lucide-react';
import Link from 'next/link';

export default function SourceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const [source, setSource] = useState<SourceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const s = await api.getSource(id);
      setSource(s);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const runTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await api.testSource(id);
      setTestResult(r.success ? `Test passed in ${r.response_time_ms}ms` : `Test failed: ${r.notes}`);
      load();
    } catch (e: unknown) {
      setTestResult(`Error: ${e instanceof Error ? e.message : 'Unknown'}`);
    } finally {
      setTesting(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`Delete "${source?.name}"?`)) return;
    await api.deleteSource(id);
    router.push('/sources');
  };

  if (loading) return <><Header title="Source Detail" /><div className="p-6 text-gray-500">Loading...</div></>;
  if (!source) return <><Header title="Not Found" /><div className="p-6 text-gray-500">Source not found.</div></>;

  const score = source.latest_score;

  return (
    <>
      <Header title={source.name} />
      <main className="flex-1 overflow-y-auto p-6 space-y-5">
        <div className="flex items-center gap-3">
          <Link href="/sources" className="text-gray-400 hover:text-white">
            <ArrowLeft size={18} />
          </Link>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <h2 className="text-xl font-bold text-white">{source.name}</h2>
              <StatusBadge status={source.status} />
              <TypeBadge type={source.source_type} />
            </div>
            <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-sm text-gray-400 hover:text-blue-400 flex items-center gap-1 mt-0.5">
              <span className="truncate">{source.url}</span>
              <ExternalLink size={12} />
            </a>
          </div>
          <div className="flex gap-2">
            <button
              onClick={runTest}
              disabled={testing}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
            >
              <TestTube size={15} />
              {testing ? 'Testing...' : 'Run Test'}
            </button>
            <button onClick={handleDelete} className="p-2 text-gray-400 hover:text-red-400 transition-colors">
              <Trash2 size={16} />
            </button>
          </div>
        </div>

        {testResult && (
          <div className={`px-4 py-3 rounded-lg text-sm ${testResult.startsWith('Test passed') ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
            {testResult}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-5">
            <h3 className="text-sm font-semibold text-gray-300 mb-4">Score Breakdown</h3>
            {score ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-gray-400 text-sm">Overall</span>
                  <span className={`text-2xl font-bold ${score.overall_score >= 70 ? 'text-green-400' : score.overall_score >= 40 ? 'text-yellow-400' : 'text-red-400'}`}>
                    {score.overall_score.toFixed(0)}
                  </span>
                </div>
                <ScoreBar label="Reliability" value={score.reliability_score} />
                <ScoreBar label="Speed" value={score.speed_score} />
                <ScoreBar label="Trust" value={score.trust_score} />
                <ScoreBar label="Italian" value={score.italian_score} />
                <ScoreBar label="German" value={score.german_score} />
              </div>
            ) : (
              <p className="text-gray-500 text-sm">No scores yet. Run a test first.</p>
            )}
          </div>

          <div className="bg-gray-800 rounded-lg border border-gray-700 p-5">
            <h3 className="text-sm font-semibold text-gray-300 mb-2">Details</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-gray-500">Type</dt><dd className="text-gray-300">{source.source_type}</dd></div>
              <div className="flex justify-between"><dt className="text-gray-500">Auth Required</dt><dd className="text-gray-300">{source.requires_auth ? 'Yes' : 'No'}</dd></div>
              <div className="flex justify-between"><dt className="text-gray-500">Last Checked</dt><dd className="text-gray-300">{source.last_checked ? new Date(source.last_checked).toLocaleString() : '—'}</dd></div>
              <div className="flex justify-between"><dt className="text-gray-500">Created</dt><dd className="text-gray-300">{new Date(source.created_at).toLocaleString()}</dd></div>
            </dl>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg border border-gray-700 p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Test History ({source.recent_tests.length})</h3>
          {source.recent_tests.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-gray-700">
                    <th className="pb-2 font-medium">Result</th>
                    <th className="pb-2 font-medium">Response</th>
                    <th className="pb-2 font-medium">HTTP</th>
                    <th className="pb-2 font-medium">Notes</th>
                    <th className="pb-2 font-medium">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700/50">
                  {source.recent_tests.map((t) => (
                    <tr key={t.id}>
                      <td className="py-2"><StatusIndicator success={t.success} /></td>
                      <td className="py-2 text-gray-300">{t.response_time_ms != null ? `${t.response_time_ms}ms` : '—'}</td>
                      <td className="py-2 text-gray-400">{t.http_status ?? '—'}</td>
                      <td className="py-2 text-gray-500 max-w-xs truncate">{t.notes ?? '—'}</td>
                      <td className="py-2 text-gray-500 text-xs">{new Date(t.timestamp).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No tests yet.</p>
          )}
        </div>
      </main>
    </>
  );
}
