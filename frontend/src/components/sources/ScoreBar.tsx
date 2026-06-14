'use client';

interface Props {
  label: string;
  value: number;
  small?: boolean;
}

export function ScoreBar({ label, value, small }: Props) {
  const color = value >= 70 ? 'bg-green-500' : value >= 40 ? 'bg-yellow-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-3">
      <span className={`text-gray-400 ${small ? 'text-xs w-24' : 'text-sm w-28'} shrink-0`}>{label}</span>
      <div className="flex-1 bg-gray-700 rounded-full h-1.5 overflow-hidden">
        <div className={`h-1.5 rounded-full ${color} transition-all`} style={{ width: `${value}%` }} />
      </div>
      <span className={`${small ? 'text-xs' : 'text-sm'} text-gray-300 w-10 text-right`}>{value.toFixed(0)}</span>
    </div>
  );
}
