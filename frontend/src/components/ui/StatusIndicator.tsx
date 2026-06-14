'use client';
export function StatusIndicator({ success }: { success: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${success ? 'text-green-400' : 'text-red-400'}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${success ? 'bg-green-400' : 'bg-red-400'}`} />
      {success ? 'OK' : 'FAIL'}
    </span>
  );
}
