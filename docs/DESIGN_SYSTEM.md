# Design System — Faelo

Duas fontes: o brandbook (identidade de marca — logo, cores, tipografia) e a
especificação de arquitetura de interface do dashboard (fornecida à parte,
mais detalhada e é a que prevalece pra tokens de app/dark mode). Onde as
duas convergem (cores base), a especificação de app tem os valores exatos a
usar no código.

**Logo**: arquivo original ainda não recebido — o que está aqui é descrição
do brandbook, não o asset. Não recriar/aproximar o SVG até o arquivo chegar.

## Marca

- **Símbolo**: "The Faelo Symbol" — um `f` estilizado com uma seta/curva
  ascendente em gradiente azul→roxo, acompanhado de uma pequena estrela
  (glow) no canto. Representa "AI Automation, Self-Service, and Exponential
  Customer Flow".
- **Wordmark**: "FAELO" — "FA" e "ELO" em pesos/cores diferentes, caixa alta.
- **Tagline primária**: "Faelo. Fluxo inteligente. Resposta imediata."
- **Tagline secundária (produto)**: "IA de autoatendimento: revolucionando
  o CRM." / "Automatize seu pré-atendimento com Faelo."

## Variações do logotipo (aguardando arquivo)

| Variação | Uso |
|---|---|
| Primary | símbolo + wordmark lado a lado — uso padrão |
| Vertical | símbolo acima, wordmark abaixo — espaços mais quadrados/estreitos |
| Icon-only | só o símbolo — favicon, app icon, avatares pequenos |
| Grayscale | versão monocromática — documentos/print P&B |

## Tipografia

| Papel | Fonte | Fallback |
|---|---|---|
| Títulos (`headings`) | Faelo Geometric | `sans-serif` |
| Corpo (`fontFamily`) | Inter | `sans-serif` |

`Faelo Geometric` é o nome da fonte de marca — arquivo ainda não recebido.
Até chegar, o token `headings` fica como `"Faelo Geometric, sans-serif"` no
CSS (cai no fallback do sistema); não substituir por outra fonte gratuita
sem pedido explícito.

## Paleta de cores — tokens de app (fonte: especificação de dashboard)

```json
{
  "faelo-blue":   "#007BFF",
  "faelo-purple": "#8F42C1",
  "faelo-glow":   "#D0E1FF",
  "dark-bg":      "#121214",
  "dark-card":    "#1E1E22",
  "dark-border":  "#2D2D35",
  "text-primary":   "#F4F4F5",
  "text-secondary": "#A1A1AA"
}
```

| Token | Hex | Uso |
|---|---|---|
| `faelo-blue` | `#007BFF` | Cor primária — CTAs, links, elementos ativos, metade do gradiente |
| `faelo-purple` | `#8F42C1` | Cor secundária — destaques de IA, outra metade do gradiente |
| `faelo-glow` | `#D0E1FF` | Tom claro — ícones de IA, mini-gráficos, glow |
| `dark-bg` | `#121214` | Fundo principal do Dark Mode (default) |
| `dark-card` | `#1E1E22` | Fundo de cards/painéis sobre `dark-bg` |
| `dark-border` | `#2D2D35` | Bordas/divisores em Dark Mode |
| `text-primary` | `#F4F4F5` | Texto principal em Dark Mode |
| `text-secondary` | `#A1A1AA` | Texto secundário/subtexto em Dark Mode |

Light Mode: fundo `#EDEDED` (Neutral-Gray do brandbook) — só o essencial
definido até agora; cards/bordas do Light Mode ainda não especificados.

### Efeitos

```css
--ai-gradient: linear-gradient(135deg, #007BFF 0%, #8F42C1 100%);
--card-glass: {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(12px);
};
```

## Theme

- **Default: Dark Mode** refinado — fundo principal `dark-bg`, cards em
  `dark-card` ou glassmorphism sutil (`card-glass`).
- **Light Mode**: suportado, fundo `#EDEDED`.

---

## Arquitetura de Interface — Dashboard (FAELO CRM, AI-Powered)

### Sidebar (navegação)

- Fundo: dark neumórfico / glassmorphism de baixa opacidade.
- Logo (símbolo Faelo) no topo superior esquerdo, brilho sutil em gradiente
  `faelo-blue` → `faelo-purple`.
- Itens de navegação principal, nesta ordem:
  1. 📊 Dashboard (Visão Geral)
  2. 🤖 Agente IA (Configuração do Pré-Atendimento)
  3. 💬 Chat/Inbox Unificado (WhatsApp, Instagram, Webchat)
  4. 🔀 Pipelines / Funil de Vendas
  5. 👥 Leads & Contatos
  6. ⚡ Automações & Transbordo
  7. 📈 Relatórios & ROI de IA

### Header superior

- Barra de busca global — placeholder: "Pesquisar lead, conversa, tag ou
  intenção de compra..."
- Badge de status da IA, pulsante: "🟢 IA Ativa • 99.4% Taxa de Resposta
  Imediata"
- Seletor de canal + perfil do operador.

### Seção superior — KPIs de pré-atendimento e IA (4 cards)

| Card | Métrica | Subtexto | Visual |
|---|---|---|---|
| Atendimentos feitos pela IA (mês) | 14.280 | ↗ +24% vs. mês anterior | ícone glow (`faelo-glow`) + mini-gráfico de linha subindo |
| Tempo médio de 1ª resposta | 1.2s | ⚡ 100% dentro da meta | — |
| Taxa de resolutividade/autoatendimento | 78.5% | leads qualificados/atendidos sem intervenção humana | — |
| Leads qualificados gerados | 1.842 | enviados para o time comercial (transbordo) | — |

Todos os 4 cards usam linha de tendência em gradiente (`ai-gradient`).

### Seção central — painel duplo

**1. Gráfico principal (esquerda, ~60% da largura)**
- Título: "Fluxo de Qualificação & Atendimento por Horário"
- Tipo: área/linhas sobrepostas, gradiente `faelo-blue` → `faelo-purple`
- Eixo X: horários do dia (00h–23h) · Eixo Y: volume de conversas
- 2 séries: "Conversas Iniciadas" e "Convertidos em Agendamento/Venda pela IA"

**2. Monitor de transbordo / fila humana (direita, ~40% da largura)**
- Título: "Fila de Transbordo Humano (Aguardando Atendente)"
- Lista em tempo real de leads pré-atendidos pela IA que precisam de
  fechamento humano. Cada item:
  - Avatar + nome do lead (ex.: "Carlos Eduardo (WhatsApp)")
  - Badge de intenção identificada pela IA (ex.: "Intenção: Compra de Plano
    Premium")
  - Score do lead (ex.: "🔥 92/100 — Alta Prioridade")
  - Status "Aguardando Vendedor" + botão rápido "Assumir Chat"

### Seção inferior — analytics do funil de pré-atendimento

**1. Pipeline/funil automático (Kanban simplificado)**

| Estágio | % retido |
|---|---|
| Entrada (Primeiro Contato) | 100% |
| Qualificação (Entendimento da Dor) | 85% |
| Proposta Aprovada / Agendado | 45% |
| Transbordo / Comercial | 22% |

**2. Performance das intenções (top dúvidas do autoatendimento)** — tabela
com barra de progresso por linha:

| Intenção | % |
|---|---|
| 🏷️ Tirar dúvidas de preços/planos | 38% |
| 🏷️ Agendamento de reuniões/demonstrações | 29% |
| 🏷️ Suporte técnico rápido | 18% |
| 🏷️ Outros/Transbordo | 15% |

---

## Nota de escopo

Este documento descreve a interface **alvo** (referência de design), não o
que já foi construído — nenhuma dessas telas existe no código ainda. Ver
README.md / conversa em andamento pro que está de fato implementado hoje
(gateway + platform-service, sem frontend).
