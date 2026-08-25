# Checklist — Fase 0 (frontend do CRM manual)

> Granular o suficiente para começar a codar direto. Baseado em [ROADMAP.md](ROADMAP.md) Fase 0.
> Marcar com `[x]` conforme for concluindo.

## 1. Client de API para o crm-service

- [ ] Em `frontend/lib/api.ts`, adicionar funções seguindo o padrão de `login()`/`register()` (mesmo tratamento de erro, mesma base URL via gateway, token JWT do contexto de auth):
  - [ ] `listPipelines()`, `createPipeline()`, `updatePipeline()`, `deletePipeline()`
  - [ ] `listStages(pipelineId)`, `createStage()`, `updateStage()`, `deleteStage()`, `reorderStage()`
  - [ ] `listContactStatuses()`, `createContactStatus()`
  - [ ] `listContacts(filters?)`, `createContact()`, `updateContact()`, `moveContactStage(contactId, stageId)`, `deleteContact()`
- [ ] Confirmar nos routers do crm-service (`services/crm-service/app`) o path exato e payload de cada endpoint antes de tipar no frontend.

## 2. Tipos TypeScript

- [ ] Criar `frontend/types/crm.ts` (ou similar) com interfaces: `Pipeline`, `Stage`, `Contact`, `ContactStatus` — espelhando os schemas Pydantic do crm-service.

## 3. Tela de Pipelines/Stages

- [ ] Rota `frontend/app/dashboard/pipelines` (ou dentro de settings).
- [ ] Listar pipelines existentes, indicar qual é `is_default`.
- [ ] CRUD de stages dentro de um pipeline (nome, cor, ordem, `is_entry`).
- [ ] Restringir ações de escrita a owner/admin (usar role do `AuthContext`).

## 4. Kanban de Contacts

- [ ] Rota `frontend/app/dashboard/contacts` (ou `/kanban`).
- [ ] Seletor de pipeline (se houver mais de um).
- [ ] Colunas = stages ordenados; cards = contacts naquele stage.
- [ ] Ação de mover contact de stage (botão ou drag-and-drop — avaliar biblioteca leve, ex. `@dnd-kit/core`, se drag-and-drop for desejado; botão "mover para →" é suficiente para uma primeira versão).
- [ ] Modal de criar/editar contact (nome, phone, email, tags, status, assigned_to).

## 5. Dashboard

- [ ] Remover placeholder "Plataforma em construção".
- [ ] Cards/atalhos para Pipelines e Contacts.
- [ ] (Opcional, se sobrar tempo) contagem simples de contacts por stage no pipeline padrão.

## 6. Validação manual

- [ ] Rodar os três serviços + frontend localmente, testar o fluxo: login → ver dashboard → criar pipeline → criar stages → criar contact → mover contact entre stages → editar/excluir contact.
- [ ] Testar como usuário `attendant` (sem permissão de criar pipeline/stage) para confirmar que a UI respeita o RBAC já implementado no backend.

## Não fazer nesta fase

- Não criar Deal/Activity ainda (Fase 1 do roadmap).
- Não mexer em migrations do backend — schema atual já suporta tudo que está aqui.
