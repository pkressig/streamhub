'use client';
import { SourceTest } from '@/lib/types';
import { StatusIndicator } from '@/components/ui/StatusIndicator';

export function RecentTests({ tests }: { tests: SourceTest[] }) {
  if (!tests.length) {
    return <p className="text-gray-500 text-sm">No tests recorded yet.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-400 border-b border-gray-700">
            <th className="pb-2 font-medium">Result</th>
            <th className="pb-2 font-medium">Type</th>
            <th className="pb-2 font-medium">Response</th>
            <th className="pb-2 font-medium">HTTP</th>
            <th className="pb-2 font-medium">Time</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-700/50">
          {tests.map((t) => (
            <tr key={t.id} className="py-2">
              <td className="py-2"><StatusIndicator success={t.success} /></td>
              <td className="py-2 text-gray-400">{t.tester_type ?? '—'}</td>
              <td className="py-2 text-gray-300">{t.response_time_ms != null ? `${t.response_time_ms}ms` : '—'}</td>
              <td className="py-2 text-gray-400">{t.http_status ?? '—'}</td>
              <td className="py-2 text-gray-500 text-xs">{new Date(t.timestamp).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
