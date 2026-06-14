'use client';
import { SourceStatus, SourceType } from '@/lib/types';

const statusColors: Record<string, string> = {
  active: 'bg-green-500/20 text-green-400 border border-green-500/30',
  degraded: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  dead: 'bg-red-500/20 text-red-400 border border-red-500/30',
  unknown: 'bg-gray-500/20 text-gray-400 border border-gray-500/30',
};

const typeColors: Record<string, string> = {
  torznab: 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
  newznab: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  rss: 'bg-orange-500/20 text-orange-400 border border-orange-500/30',
  manifest: 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30',
  generic_http: 'bg-gray-500/20 text-gray-400 border border-gray-500/30',
};

export function StatusBadge({ status }: { status: SourceStatus }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${statusColors[status] ?? statusColors.unknown}`}>
      {status}
    </span>
  );
}

export function TypeBadge({ type }: { type: SourceType }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${typeColors[type] ?? typeColors.generic_http}`}>
      {type}
    </span>
  );
}
