"use client";

import { useEffect, useState } from "react";
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
  IconChevronLeft,
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

const COLLAPSED_KEY = "faelo_sidebar_collapsed";

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    setCollapsed(localStorage.getItem(COLLAPSED_KEY) === "1");
  }, []);

  useEffect(() => {
    localStorage.setItem(COLLAPSED_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  function handleLogout() {
    logout();
    router.push("/login");
  }

  const itemClass = (active: boolean) =>
    `flex items-center gap-2.5 rounded-lg px-2.5 py-2.5 transition-colors ${
      collapsed ? "justify-center" : ""
    } ${
      active
        ? "bg-sidebar-active-bg font-medium text-sidebar-fg"
        : "text-sidebar-fg-muted hover:bg-sidebar-hover-bg hover:text-sidebar-fg"
    }`;

  return (
    <aside
      className={`flex shrink-0 flex-col gap-4 border-r border-sidebar-border bg-sidebar-bg px-3 py-4 text-[13px] transition-[width] duration-150 ${
        collapsed ? "w-16" : "w-52"
      }`}
    >
      <div className={`flex items-center ${collapsed ? "justify-center" : "justify-between"} px-1`}>
        {!collapsed && (
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-sidebar-fg-muted">Faelo CRM</p>
            <span className="font-heading text-base font-bold text-sidebar-fg">FAELO</span>
          </div>
        )}
        <button
          type="button"
          onClick={() => setCollapsed((c) => !c)}
          title={collapsed ? "Expandir menu" : "Recolher menu"}
          className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-sidebar-fg-muted transition-colors hover:bg-sidebar-hover-bg hover:text-sidebar-fg"
        >
          <IconChevronLeft
            width={14}
            height={14}
            className={`transition-transform duration-150 ${collapsed ? "rotate-180" : ""}`}
          />
        </button>
      </div>

      <div className="flex flex-1 flex-col gap-1">
        {!collapsed && (
          <p className="px-2 text-[10px] font-semibold uppercase tracking-wider text-sidebar-fg-muted">Menu</p>
        )}
        <nav className="flex flex-col gap-2">
          {NAV_ITEMS.map(({ href, label, Icon }) => {
            const active = href === "/dashboard" ? pathname === href : pathname.startsWith(href);
            return (
              <Link key={href} href={href} title={collapsed ? label : undefined} className={itemClass(active)}>
                <Icon className="shrink-0" width={16} height={16} />
                {!collapsed && label}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="flex flex-col gap-2 border-t border-sidebar-border pt-3">
        <button
          type="button"
          onClick={toggleTheme}
          title={collapsed ? (theme === "dark" ? "Tema claro" : "Tema escuro") : undefined}
          className={`flex items-center gap-2.5 rounded-lg px-2.5 py-2.5 text-left text-sidebar-fg-muted transition-colors hover:bg-sidebar-hover-bg hover:text-sidebar-fg ${
            collapsed ? "justify-center" : ""
          }`}
        >
          {theme === "dark" ? (
            <IconSun className="shrink-0" width={16} height={16} />
          ) : (
            <IconMoon className="shrink-0" width={16} height={16} />
          )}
          {!collapsed && (theme === "dark" ? "Tema claro" : "Tema escuro")}
        </button>

        {user && !collapsed && (
          <p className="truncate px-2.5 pt-0.5 text-xs text-sidebar-fg-muted">{user.name}</p>
        )}

        <button
          type="button"
          onClick={handleLogout}
          title={collapsed ? "Sair" : undefined}
          className={`flex items-center gap-2.5 rounded-lg px-2.5 py-2.5 text-left text-sidebar-fg-muted transition-colors hover:bg-sidebar-hover-bg hover:text-sidebar-fg ${
            collapsed ? "justify-center" : ""
          }`}
        >
          <IconLogout className="shrink-0" width={16} height={16} />
          {!collapsed && "Sair"}
        </button>
      </div>
    </aside>
  );
}
