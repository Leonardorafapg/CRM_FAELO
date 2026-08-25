import { ThemeProvider } from "@/contexts/ThemeContext";
import { Sidebar } from "@/components/layout/Sidebar";

/** Layout aninhado do Next (app router) — aplicado a toda rota sob
 * /dashboard automaticamente, sem precisar repetir em cada page.tsx.
 * ThemeProvider fica so aqui de proposito: login/registro (fora de
 * /dashboard) nunca ficam sob o data-theme dele, sempre claros. */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <div className="flex flex-1">
        <Sidebar />
        <div className="flex flex-1 flex-col">{children}</div>
      </div>
    </ThemeProvider>
  );
}
