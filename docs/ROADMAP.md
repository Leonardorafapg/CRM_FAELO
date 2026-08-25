# Roadmap — CRM-FAELO

> Prioridades sequenciadas a partir do estado descrito em [STATUS.md](STATUS.md).

## Princípio de priorização

O backend do CRM manual (Contact/Pipeline/Stage) já está pronto e testado, mas **invisível** — não há UI. Antes de adicionar novas entidades (Deal, Activity), o maior retorno é fechar o ciclo: expor o que já existe no frontend, para o CRM virar algo usável de fato.

## Fase 0 — Fechar o ciclo do que já existe (curtíssimo prazo)

Objetivo: qualquer usuário logado consegue ver e gerenciar seus contatos em um Kanban por pipeline, pelo navegador.

1. `lib/api.ts` — client para os endpoints do crm-service (contacts, pipelines, stages, contact-statuses), reaproveitando o padrão de auth já existente (token JWT do `AuthContext`).
2. Tela de listagem/gestão de **Pipelines e Stages** (CRUD básico, provavelmente owner/admin only).
3. Tela de **Kanban de Contacts** — colunas = stages do pipeline selecionado, cards = contacts, drag-and-drop ou botão simples para mover de stage.
4. Tela/modal de **criação e edição de Contact**.
5. Dashboard deixa de ser placeholder: vira um hub com atalho para pipelines/contatos e (futuramente) métricas.

## Fase 0.5 — whatsapp-service (novo microsserviço, transcrito do legado)

Baseado na estrutura antiga do Faelo (`C:\Users\Leonardo\Desktop\Chatbot`) — ver detalhamento completo em [features/ARQUITETURA_LEGADO_VS_NOVO.md](features/ARQUITETURA_LEGADO_VS_NOVO.md), [features/CLIENTES_ESTAGIOS.md](features/CLIENTES_ESTAGIOS.md) e [features/WHATSAPP_SERVICE.md](features/WHATSAPP_SERVICE.md).

12. Novo serviço `services/whatsapp-service`, versão mínima: models `Connection`, `Session`, `Message`; integração com Evolution API (QR code, webhook de mensagens). **Sem** vínculo automático com Contact do crm-service nesta fase.
13. Adicionar rotas do whatsapp-service ao `SERVICE_ROUTES` do gateway.
14. Frontend: tela de **Conexões** (QR code, status) e tela de **Atendimentos** (inbox em tempo real via WebSocket).
15. Sem IA/bot, sem automações, sem WhatsApp Cloud API oficial — atendimento 100% manual (ver [features/WHATSAPP_SERVICE.md](features/WHATSAPP_SERVICE.md)).

## Fase 1 — Completar o modelo de CRM

6. **Deal/Oportunidade**: entidade nova no crm-service (valor, moeda, previsão de fechamento, pipeline/stage, contact vinculado, status won/lost). Decidir se substitui o Kanban de contacts ou convive com ele (contact = pessoa, deal = negócio em andamento com essa pessoa — modelo mais próximo de CRM de vendas tradicional).
7. **Activity/Task**: follow-ups com data, tipo (ligação, reunião, e-mail), vinculado a contact e/ou deal, com dono (`assigned_to`).
8. Migrations incrementais a partir daqui (parar de fazer squash em uma única migration inicial).

## Fase 2 — Gestão e operação

9. UI de **gestão de usuários e convites** (endpoints já existem no platform-service: invite/accept-invite).
10. **Relatórios/métricas de funil**: contagem de contacts/deals por stage, taxa de conversão, tempo médio em cada stage.
11. Lógica de `BusinessHours` (schema já existe, sem uso hoje).

## Fase 3 — Além do CRM manual

12. `conversation-service` (WhatsApp/IA) — o `Tenant` já tem campos (`system_prompt`, `ai_provider`, `groq_key`, `openrouter_model`) esperando por isso.

## Fora de escopo por ora

- Integrações externas (e-mail, calendário) além do que já está previsto.
- Multi-idioma na UI.

Ver [TASKS.md](TASKS.md) para o checklist granular da Fase 0, que é o que faz sentido atacar amanhã.
