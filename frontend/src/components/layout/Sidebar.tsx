'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Database, FlaskConical, Zap, Trophy, ClipboardList } from 'lucide-react';

const nav = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/sources', label: 'Sources', icon: Database },
  { href: '/benchmarks', label: 'Benchmarks', icon: ClipboardList },
  { href: '/rankings', label: 'Rankings', icon: Trophy },
  { href: '/testing', label: 'Testing', icon: FlaskConical },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-56 shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
      <div className="p-5 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Zap size={20} className="text-blue-400" />
          <span className="font-bold text-white text-lg tracking-tight">PascalHub</span>
        </div>
        <p className="text-xs text-gray-500 mt-0.5">Source Intelligence</p>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {nav.map(({ href, label, icon: Icon }) => {
          const active =
            href === '/' ? pathname === '/' : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                active
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              <Icon size={16} />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="p-4 border-t border-gray-800">
        <p className="text-xs text-gray-600">v0.2.0</p>
      </div>
    </aside>
  );
}
