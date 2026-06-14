'use client';
import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Stats, DiscoveryStats } from '@/lib/types';
import { StatsCard } from '@/components/dashboard/StatsCard';
import { RecentTests } from '@/components/dashboard/RecentTests';
import { Header } from '@/components/layout/Header';
import { Database, CheckCircle, XCircle, AlertTriangle, TrendingUp, Radar, Clock, CalendarClock } from 'lucide-react';

export default function DashboardPage() {
  const [stats, setStats]         = useState<Stats | null>(null);
  const [dStats, setDStats]       = useState<DiscoveryStats | null>(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [s, d] = await Promise.all([api.getStats(), api.getDiscoveryStats()]);
      setStats(s);
      setDStats(d);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load stats');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 30_000);
    return () => clearInterval(id);
  }, [load]);

  return (
    <>
      <Header title="Dashboard" />
      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        {loading && !stats ? (
          <div className="text-gray-500 text-sm animate-pulse">Loading…</div>
        ) : error ? (
          <div className="px-4 py-3 rounded-lg text-sm border bg-red-500/10 border-red-500/20 text-red-400">
            <span className="font-semibold">API error:</span> {error}
            <button onClick={load} className="ml-3 underline text-red-300 hover:text-white">Retry</button>
          </div>
        ) : (
          <>
            {/* Approved Sources */}
            {stats && (
              <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
                <StatsCard label="Total Sources" value={stats.total}                     icon={<Database size={28} />}    color="text-blue-400" />
                <StatsCard label="Active"        value={stats.active}                    icon={<CheckCircle size={28} />} color="text-green-400" />
                <StatsCard label="Degraded"      value={stats.degraded}                  icon={<AlertTriangle size={28} />} color="text-yellow-400" />
                <StatsCard label="Dead"          value={stats.dead}                      icon={<XCircle size={28} />}     color="text-red-400" />
                <StatsCard label="Avg Score"     value={stats.avg_overall_score.toFixed(0)} icon={<TrendingUp size={28} />} color="text-purple-400" />
              </div>
            )}

            {/* Discovery widget */}
            {dStats && (
              <div className="bg-gray-800 rounded-lg border border-gray-700 p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Radar size={16} className="text-blue-400" />
                    <h2 className="text-sm font-semibold text-gray-300">Discovery Pipeline</h2>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${dStats.auto_discovery_enabled ? 'bg-green-500/20 text-green-400' : 'bg-gray-700 text-gray-500'}`}>
                      {dStats.auto_discovery_enabled ? 'Auto: On' : 'Auto: Off'}
                    </span>
                  </div>
                  <Link href="/discovery" className="text-xs text-blue-400 hover:text-blue-300 transition-colors">View all →</Link>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3 mb-4">
                  {[
                    { label: 'Candidates',  value: dStats.total_candidates, color: 'text-gray-300' },
                    { label: 'Benchmarked', value: dStats.benchmarked,      color: 'text-purple-400' },
                    { label: 'Approved',    value: dStats.approved,          color: 'text-green-400' },
                    { label: 'Imported',    value: dStats.imported,          color: 'text-teal-400' },
                    { label: 'Seeds',       value: dStats.total_seeds,       color: 'text-blue-400' },
                    { label: 'Bred Seeds',  value: dStats.total_bred_seeds,  color: 'text-orange-400' },
                    { label: 'Runs',        value: dStats.total_runs,        color: 'text-gray-400' },
                  ].map(c => (
                    <div key={c.label} className="bg-gray-900/60 rounded-lg p-3 text-center">
                      <div className={`text-xl font-bold ${c.color}`}>{c.value}</div>
                      <div className="text-xs text-gray-600 mt-0.5">{c.label}</div>
                    </div>
                  ))}
                </div>
                <div className="flex flex-wrap gap-4 text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <Clock size={11} />
                    Every {dStats.discovery_interval_hours}h
                  </span>
                  {dStats.next_scheduled_at && (
                    <span className="flex items-center gap-1">
                      <CalendarClock size={11} />
                      Next: {new Date(dStats.next_scheduled_at).toLocaleString()}
                    </span>
                  )}
                </div>
              </div>
            )}

            {stats && (
              <div className="bg-gray-800 rounded-lg border border-gray-700 p-5">
                <h2 className="text-sm font-semibold text-gray-300 mb-4">Recent Tests</h2>
                <RecentTests tests={stats.recent_tests} />
              </div>
            )}
          </>
        )}
      </main>
    </>
  );
}
