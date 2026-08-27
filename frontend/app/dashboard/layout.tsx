import { ThemeProvider } from "@/contexts/ThemeContext";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

/** Layout aninhado do Next (app router) — aplicado a toda rota sob
 * /dashboard automaticamente, sem precisar repetir em cada page.tsx.
 * ThemeProvider fica so aqui de proposito: login/registro (fora de
 * /dashboard) nunca ficam sob o data-theme dele, sempre claros. */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      {/* h-dvh + overflow-hidden trava a altura do shell inteiro na
       * viewport — sem isso, o Sidebar (sem altura propria) fica mais alto
       * que a tela em janelas baixas e empurra a pagina toda, quebrando o
       * scroll interno de paginas como Atendimentos (que dependem de "minha
       * altura = exatamente o espaco disponivel", nao do conteudo). Cada
       * pagina decide sozinha se quer preencher esse espaco (h-full +
       * scroll proprio, como Atendimentos) ou deixar o wrapper abaixo
       * rolar por ela (paginas comuns, sem altura explicita). */}
      {/* Sem flex-1 aqui de proposito: essa div nao tem irmao nenhum
       * dividindo espaco com ela (e o unico filho do wrapper do body), e
       * flex-1 (flex-basis:0) some com o h-dvh num container flex-col — o
       * item volta a se ajustar ao conteudo (empurrado pela altura do
       * Sidebar) em vez de travar na viewport. */}
      <div className="flex h-dvh overflow-hidden">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <TopBar />
          <div className="flex flex-1 flex-col overflow-y-auto">{children}</div>
        </div>
      </div>
    </ThemeProvider>
  );
}
