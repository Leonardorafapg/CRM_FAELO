"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { useTheme } from "@/contexts/ThemeContext";
import {
  IconDashboard,
  IconUsers,
  IconKanban,
  IconPlug,
  IconChat,
  IconSun,
  IconMoon,
  IconLogout,
} from "@/components/layout/icons";

/** So as rotas que de fato existem hoje — nada de item de menu apontando
 * pra tela que ainda nao foi construida (ver ROADMAP.md). */
const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", Icon: IconDashboard },
  { href: "/dashboard/clientes", label: "Clientes", Icon: IconUsers },
  { href: "/dashboard/quadros", label: "Quadros", Icon: IconKanban },
  { href: "/dashboard/conexoes", label: "Conexões", Icon: IconPlug },
  { href: "/dashboard/atendimentos", label: "Atendimentos", Icon: IconChat },
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
    <aside className="flex w-64 shrink-0 flex-col gap-5 border-r border-border-light bg-sidebar-bg px-4 py-5">
      <div className="px-1">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-accent-blue">Faelo CRM</p>
        <span className="font-heading text-lg font-bold text-text-dark">FAELO</span>
      </div>

      <div className="flex flex-1 flex-col gap-1.5">
        <p className="px-2 text-[11px] font-semibold uppercase tracking-wider text-accent-blue">Menu</p>
        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map(({ href, label, Icon }) => {
            const active = href === "/dashboard" ? pathname === href : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                  active
                    ? "bg-accent-blue text-white"
                    : "text-text-muted hover:bg-card-bg hover:text-text-dark"
                }`}
              >
                <Icon className="shrink-0" />
                {label}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="flex flex-col gap-1 border-t border-border-light pt-3">
        <button
          type="button"
          onClick={toggleTheme}
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-text-muted transition-colors hover:bg-card-bg hover:text-text-dark"
        >
          {theme === "dark" ? <IconSun className="shrink-0" /> : <IconMoon className="shrink-0" />}
          {theme === "dark" ? "Tema claro" : "Tema escuro"}
        </button>

        {user && <p className="truncate px-3 pt-1 text-xs text-text-muted">{user.name}</p>}

        <button
          type="button"
          onClick={handleLogout}
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-text-muted transition-colors hover:bg-card-bg hover:text-text-dark"
        >
          <IconLogout className="shrink-0" />
          Sair
        </button>
      </div>
    </aside>
  );
}
