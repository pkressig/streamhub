'use client';
import { ReactNode } from 'react';

interface Props {
  label: string;
  value: string | number;
  icon: ReactNode;
  color?: string;
}

export function StatsCard({ label, value, icon, color = 'text-blue-400' }: Props) {
  return (
    <div className="bg-gray-800 rounded-lg p-5 border border-gray-700">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wider">{label}</p>
          <p className={`text-3xl font-bold mt-1 ${color}`}>{value}</p>
        </div>
        <div className={`${color} opacity-60`}>{icon}</div>
      </div>
    </div>
  );
}
