'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { RankedSource } from '@/lib/types';
import { Header } from '@/components/layout/Header';
import { ScoreBar } from '@/components/sources/ScoreBar';
import { StatusBadge } from '@/components/ui/Badge';
import { Trophy, Flag, Film, Tv, Sword, ExternalLink } from 'lucide-react';

type Tab = 'italian' | 'german' | 'movies' | 'series' | 'anime';

const TABS: { key: Tab; label: string; icon: React.ReactNode; scoreKey: string }[] = [
  { key: 'italian', label: 'Italian', icon: <Flag size={14} />, scoreKey: 'italian_score' },
  { key: 'german', label: 'German', icon: <Flag size={14} />, scoreKey: 'german_score' },
  { key: 'movies', label: 'Movies', icon: <Film size={14} />, scoreKey: 'movie_score' },
  { key: 'series', label: 'Series', icon: <Tv size={14} />, scoreKey: 'series_score' },
  { key: 'anime', label: 'Anime', icon: <Sword size={14} />, scoreKey: 'anime_score' },
];

const FETCHERS: Record<Tab, () => Promise<RankedSource[]>> = {
  italian: () => api.getRankingsItalian(),
  german: () => api.getRankingsGerman(),
  movies: () => api.getRankingsMovies(),
  series: () => api.getRankingsSeries(),
  anime: () => api.getRankingsAnime(),
};

function RankingTable({ sources, scoreLabel, scoreKey }: {
  sources: RankedSource[];
  scoreLabel: string;
  scoreKey: string;
}) {
  if (!sources.length) {
    return (
      <div className="text-center py-12 text-gray-500">
        <Trophy size={32} className="mx-auto mb-3 opacity-30" />
        <p>No ranked sources yet.</p>
        <p className="text-xs mt-1">Run a benchmark to generate rankings.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {sources.map((s, i) => {
        const profile = s.profile;
        const score = s.score;
        return (
          <div key={s.id} className="bg-gray-900/60 rounded-lg p-4 flex items-start gap-4">
            <div className={`text-2xl font-bold w-8 shrink-0 ${i === 0 ? 'text-yellow-400' : i === 1 ? 'text-gray-300' : i === 2 ? 'text-orange-400' : 'text-gray-600'}`}>
              {i + 1}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <Link href={`/sources/${s.id}`} className="text-white font-semibold hover:text-blue-400 transition-colors">
                  {s.name}
                </Link>
                <StatusBadge status={s.status} />
                <span className="text-gray-600 text-xs">{s.source_type}</span>
              </div>
              <a href={s.url} target="_blank" rel="noopener noreferrer" className="text-xs text-gray-500 hover:text-blue-400 flex items-center gap-1 mt-0.5 transition-colors">
                <span className="truncate max-w-xs">{s.url}</span>
                <ExternalLink size={10} />
              </a>
              {profile && (
                <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5">
                  <ScoreBar label="Reliability" value={profile.reliability_pct} small />
                  <ScoreBar label="Italian" value={profile.italian_score} small />
                  <ScoreBar label="Movies" value={profile.movie_score} small />
                  <ScoreBar label="German" value={profile.german_score} small />
                  <ScoreBar label="Series" value={profile.series_score} small />
                  <ScoreBar label="Anime" value={profile.anime_score} small />
                </div>
              )}
              {profile && (
                <div className="mt-2 flex gap-4 text-xs text-gray-500">
                  {profile.avg_response_ms != null && (
                    <span>Avg response: {profile.avg_response_ms.toFixed(0)}ms</span>
                  )}
                  <span>Avg results: {profile.avg_result_count.toFixed(1)}</span>
                  <span>Dup rate: {profile.duplicate_rate.toFixed(1)}%</span>
                  <span>{profile.benchmark_runs} run{profile.benchmark_runs !== 1 ? 's' : ''}</span>
                </div>
              )}
            </div>
            <div className="text-right shrink-0">
              <div className={`text-3xl font-bold ${score >= 70 ? 'text-green-400' : score >= 40 ? 'text-yellow-400' : 'text-red-400'}`}>
                {score.toFixed(0)}
              </div>
              <div className="text-xs text-gray-500">{scoreLabel}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function RankingsPage() {
  const [tab, setTab] = useState<Tab>('italian');
  const [data, setData] = useState<Partial<Record<Tab, RankedSource[]>>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTab = async (t: Tab, force = false) => {
    if (data[t] && !force) return;
    setLoading(true);
    setError(null);
    try {
      const res = await FETCHERS[t]();
      setData(d => ({ ...d, [t]: res }));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load rankings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadTab(tab); }, [tab]);

  const currentTab = TABS.find(t => t.key === tab)!;
  const sources = data[tab] ?? [];

  return (
    <>
      <Header title="Rankings" />
      <main className="flex-1 overflow-y-auto p-6 space-y-5">
        {/* Tab bar */}
        <div className="flex gap-1 bg-gray-800/60 rounded-lg p-1 w-fit">
          {TABS.map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                tab === t.key
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>

        <div className="bg-gray-800 rounded-lg border border-gray-700 p-5">
          <div className="flex items-center gap-2 mb-5">
            <Trophy size={16} className="text-yellow-400" />
            <h2 className="text-sm font-semibold text-gray-300">
              Top {currentTab.label} Sources
            </h2>
            <button
              onClick={() => { setData(d => ({ ...d, [tab]: undefined })); loadTab(tab, true); }}
              className="ml-auto text-xs text-gray-500 hover:text-white transition-colors"
            >
              Refresh
            </button>
          </div>
          {error && (
            <div className="px-4 py-3 rounded-lg text-sm border bg-red-500/10 border-red-500/20 text-red-400 mb-4">
              <span className="font-semibold">API error:</span> {error}
            </div>
          )}
          {loading && !sources.length ? (
            <p className="text-gray-500 text-sm animate-pulse">Loading…</p>
          ) : (
            <RankingTable
              sources={sources}
              scoreLabel={currentTab.label}
              scoreKey={currentTab.scoreKey}
            />
          )}
        </div>
      </main>
    </>
  );
}
