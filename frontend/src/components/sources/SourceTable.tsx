'use client';
import Link from 'next/link';
import { Source } from '@/lib/types';
import { StatusBadge, TypeBadge } from '@/components/ui/Badge';
import { Trash2, TestTube, ExternalLink } from 'lucide-react';
import { api } from '@/lib/api';
import { useState } from 'react';

interface Props {
  sources: Source[];
  onRefresh: () => void;
}

export function SourceTable({ sources, onRefresh }: Props) {
  const [testing, setTesting] = useState<string | null>(null);

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete "${name}"?`)) return;
    await api.deleteSource(id);
    onRefresh();
  };

  const handleTest = async (id: string) => {
    setTesting(id);
    try {
      await api.testSource(id);
      onRefresh();
    } finally {
      setTesting(null);
    }
  };

  if (!sources.length) {
    return (
      <div className="text-center py-16 text-gray-500">
        <p className="text-lg">No sources found.</p>
        <p className="text-sm mt-1">Add your first source to get started.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-400 border-b border-gray-700">
            <th className="pb-3 font-medium">Name</th>
            <th className="pb-3 font-medium">Type</th>
            <th className="pb-3 font-medium hidden md:table-cell">URL</th>
            <th className="pb-3 font-medium">Status</th>
            <th className="pb-3 font-medium">Score</th>
            <th className="pb-3 font-medium hidden lg:table-cell">Last Checked</th>
            <th className="pb-3 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-700/50">
          {sources.map((s) => (
            <tr key={s.id} className="hover:bg-gray-700/30 transition-colors">
              <td className="py-3">
                <Link href={`/sources/${s.id}`} className="text-white hover:text-blue-400 font-medium">
                  {s.name}
                </Link>
              </td>
              <td className="py-3"><TypeBadge type={s.source_type} /></td>
              <td className="py-3 hidden md:table-cell">
                <a href={s.url} target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-blue-400 flex items-center gap-1 max-w-xs truncate">
                  <span className="truncate">{s.url}</span>
                  <ExternalLink size={10} className="shrink-0" />
                </a>
              </td>
              <td className="py-3"><StatusBadge status={s.status} /></td>
              <td className="py-3">
                {s.latest_score ? (
                  <span className={`font-mono text-sm ${s.latest_score.overall_score >= 70 ? 'text-green-400' : s.latest_score.overall_score >= 40 ? 'text-yellow-400' : 'text-red-400'}`}>
                    {s.latest_score.overall_score.toFixed(0)}
                  </span>
                ) : (
                  <span className="text-gray-600">—</span>
                )}
              </td>
              <td className="py-3 hidden lg:table-cell text-gray-500 text-xs">
                {s.last_checked ? new Date(s.last_checked).toLocaleString() : '—'}
              </td>
              <td className="py-3">
                <div className="flex items-center justify-end gap-2">
                  <button
                    onClick={() => handleTest(s.id)}
                    disabled={testing === s.id}
                    className="p-1.5 text-gray-400 hover:text-blue-400 disabled:opacity-40 transition-colors"
                    title="Run test"
                  >
                    <TestTube size={15} />
                  </button>
                  <button
                    onClick={() => handleDelete(s.id, s.name)}
                    className="p-1.5 text-gray-400 hover:text-red-400 transition-colors"
                    title="Delete"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
