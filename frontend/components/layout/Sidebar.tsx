"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { useTheme } from "@/contexts/ThemeContext";

/** So as rotas que de fato existem hoje — nada de item de menu apontando
 * pra tela que ainda nao foi construida (ver ROADMAP.md). */
const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: "📊" },
  { href: "/dashboard/clientes", label: "Clientes", icon: "👥" },
  { href: "/dashboard/quadros", label: "Quadros", icon: "🔀" },
  { href: "/dashboard/conexoes", label: "Conexões", icon: "🔌" },
  { href: "/dashboard/atendimentos", label: "Atendimentos", icon: "💬" },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <aside className="flex w-60 shrink-0 flex-col gap-6 border-r border-border-light bg-sidebar-bg px-3 py-5">
      <div className="px-2">
        <span className="font-heading text-lg font-bold text-text-dark">FAELO</span>
      </div>

      <nav className="flex flex-1 flex-col gap-1">
        {NAV_ITEMS.map((item) => {
          const active = item.href === "/dashboard" ? pathname === item.href : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-accent-blue text-white"
                  : "text-text-muted hover:bg-card-bg hover:text-text-dark"
              }`}
            >
              <span aria-hidden="true">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="flex flex-col gap-1 border-t border-border-light pt-3">
        <button
          type="button"
          onClick={toggleTheme}
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-text-muted transition-colors hover:bg-card-bg hover:text-text-dark"
        >
          <span aria-hidden="true">{theme === "dark" ? "☀️" : "🌙"}</span>
          {theme === "dark" ? "Tema claro" : "Tema escuro"}
        </button>

        {user && <p className="truncate px-3 pt-1 text-xs text-text-muted">{user.name}</p>}

        <button
          type="button"
          onClick={handleLogout}
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-text-muted transition-colors hover:bg-card-bg hover:text-text-dark"
        >
          <span aria-hidden="true">🚪</span>
          Sair
        </button>
      </div>
    </aside>
  );
}
