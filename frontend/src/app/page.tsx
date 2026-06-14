'use client';
import { useEffect, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import { Stats } from '@/lib/types';
import { StatsCard } from '@/components/dashboard/StatsCard';
import { RecentTests } from '@/components/dashboard/RecentTests';
import { Header } from '@/components/layout/Header';
import { Database, CheckCircle, XCircle, HelpCircle, TrendingUp } from 'lucide-react';

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const s = await api.getStats();
      setStats(s);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, [load]);

  return (
    <>
      <Header title="Dashboard" />
      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        {loading && !stats ? (
          <div className="text-gray-500 text-sm">Loading...</div>
        ) : stats ? (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              <StatsCard label="Total Sources" value={stats.total} icon={<Database size={28} />} color="text-blue-400" />
              <StatsCard label="Active" value={stats.active} icon={<CheckCircle size={28} />} color="text-green-400" />
              <StatsCard label="Degraded" value={stats.degraded} icon={<TrendingUp size={28} />} color="text-yellow-400" />
              <StatsCard label="Dead" value={stats.dead} icon={<XCircle size={28} />} color="text-red-400" />
              <StatsCard label="Avg Score" value={`${stats.avg_overall_score.toFixed(0)}`} icon={<HelpCircle size={28} />} color="text-purple-400" />
            </div>

            <div className="bg-gray-800 rounded-lg border border-gray-700 p-5">
              <h2 className="text-sm font-semibold text-gray-300 mb-4">Recent Tests</h2>
              <RecentTests tests={stats.recent_tests} />
            </div>
          </>
        ) : null}
      </main>
    </>
  );
}
