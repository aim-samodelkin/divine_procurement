"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { logout } from "../lib/auth";

const NAV = [
  { href: "/dashboard", label: "Дашборд" },
  { href: "/categories", label: "Категории" },
  { href: "/components", label: "Компоненты" },
  { href: "/suppliers", label: "Поставщики" },
  { href: "/suppliers/coverage", label: "Покрытие" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="flex min-h-screen bg-gray-50">
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <span className="font-bold text-gray-900">Закупки</span>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {NAV.map(n => (
            <Link
              key={n.href} href={n.href}
              className={`block px-3 py-2 rounded text-sm font-medium transition-colors ${
                pathname.startsWith(n.href) ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="p-3 border-t border-gray-200">
          <button onClick={logout} className="text-sm text-gray-500 hover:text-gray-900 w-full text-left px-3 py-2">
            Выйти
          </button>
        </div>
      </aside>
      <main className="flex-1 p-6 overflow-auto">{children}</main>
    </div>
  );
}
