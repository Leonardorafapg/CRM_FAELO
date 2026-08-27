"use client";

import Link from "next/link";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import {
  IconBuilding,
  IconClock,
  IconBook,
  IconLayers,
  IconChevronRight,
} from "@/components/layout/icons";

type ConfigCard = {
  Icon: typeof IconBuilding;
  title: string;
  description: string;
  href: string;
  comingSoon?: boolean;
};

const CARDS: ConfigCard[] = [
  {
    Icon: IconBuilding,
    title: "Dados da Empresa",
    description: "Nome, telefone, endereço e informações do estabelecimento.",
    href: "/dashboard/configuracoes/empresa",
  },
  {
    Icon: IconClock,
    title: "Horários",
    description: "Defina os horários de atendimento por dia da semana.",
    href: "/dashboard/configuracoes/horarios",
  },
  {
    Icon: IconBook,
    title: "Base de Conhecimento",
    description: "Perguntas e respostas que treinam o assistente de IA.",
    href: "/dashboard/configuracoes/em-breve",
    comingSoon: true,
  },
  {
    Icon: IconLayers,
    title: "Pacotes",
    description: "Agendamento, catálogo e outras funcionalidades por nicho.",
    href: "/dashboard/configuracoes/em-breve",
    comingSoon: true,
  },
];

export default function ConfiguracoesPage() {
  const ready = useRequireAuth();
  if (!ready) return null;

  return (
    <main className="flex w-full max-w-3xl flex-1 flex-col gap-6 px-6 py-8">
      <div>
        <h1 className="font-heading text-2xl font-bold text-text-dark">Configurações</h1>
        <p className="mt-1 text-sm text-text-muted">Gerencie as configurações do seu estabelecimento.</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {CARDS.map((card) => (
          <Link
            key={card.title}
            href={card.href}
            className="flex items-start gap-4 rounded-xl border border-border-light bg-card-bg p-5 transition-colors hover:bg-page-bg"
          >
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[10px] bg-accent-blue/15 text-accent-blue">
              <card.Icon width={20} height={20} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="flex items-center gap-2 text-sm font-semibold text-text-dark">
                {card.title}
                {card.comingSoon && (
                  <span className="rounded-full bg-page-bg px-2 py-0.5 text-[10px] font-medium text-text-muted">
                    Em breve
                  </span>
                )}
              </p>
              <p className="mt-1 text-xs leading-relaxed text-text-muted">{card.description}</p>
            </div>
            <IconChevronRight width={16} height={16} className="mt-1 shrink-0 text-text-muted" />
          </Link>
        ))}
      </div>
    </main>
  );
}
