'use client';
export function Header({ title }: { title: string }) {
  return (
    <header className="h-14 border-b border-gray-800 flex items-center px-6 shrink-0">
      <h1 className="text-white font-semibold">{title}</h1>
    </header>
  );
}
