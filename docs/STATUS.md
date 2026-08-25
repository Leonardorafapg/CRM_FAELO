# Status do Projeto — CRM-FAELO

> Última atualização: 2026-08-24 (baseado em auditoria da estrutura atual)

Snapshot do que existe hoje no repositório, por camada. Este documento reflete o estado no momento em que foi escrito — não é histórico, é fotografia. Ao ficar desatualizado, deve ser reescrito, não acumulado.

## Arquitetura

- **Microserviços**: `gateway` (proxy reverso), `platform-service` (identidade/tenant), `crm-service` (CRM manual), `shared` (pacote Python comum).
- **Multi-tenant**: `tenant_id` em cada registro, sem FK cross-serviço. Bancos/schemas separados por serviço.
- **Auth**: JWT emitido **somente** pelo `platform-service`; os demais serviços apenas verificam via segredo compartilhado (`shared`). RBAC via enum `UserRole` (owner/admin/attendant) + `is_platform_admin` para super-admin.
- **Gateway**: roteamento por prefixo de path (`SERVICE_ROUTES`), propaga headers e `X-Request-ID`. Rotas `/internal/*` ficam fora do proxy (chamada direta serviço-a-serviço).

## 1. platform-service — ✅ Pronto

- **Entidades**: `Tenant` (já com campos para futura IA de atendimento: `system_prompt`, `ai_provider`, etc.), `BusinessHours` (schema existe, lógica **não implementada**), `User`, `PasswordResetToken`, `Invite` (tokens só guardados como hash sha256, expiração, uso único).
- **Endpoints** (`/auth/*`): registro, login, forgot-password (resposta anti-enumeração), reset-password, convite (`GET /invite/{token}`, `POST /accept-invite`). Rate limiting via slowapi. Routers separados para tenants/users/internal.
- **Testes**: cobrem os fluxos acima.
- **Migrations**: uma única migration inicial (2026-08-23) — sem histórico incremental ainda.

## 2. crm-service — ✅ Pronto (CRM manual, sem "negócio")

- **Entidades**: `ContactStatus` (livre por tenant), `Contact` (nome, phone único por tenant, email, tags, `assigned_to`), `Pipeline` (multi-pipeline, `is_default`), `Stage` (coluna do Kanban: `order`, `color`, `is_entry`).
- **Não existe**: Deal/Oportunidade (valor, previsão de fechamento), Activity/Task, Note. O Kanban hoje move **contatos**, não negócios.
- **Endpoints**: CRUD completo de contacts, contact-statuses, pipelines, stages — protegidos por JWT + RBAC.
- **Testes**: bons — isolamento multi-tenant, RBAC (attendant não cria pipeline/stage/status), movimentação no Kanban, regra de stage de entrada única.
- **Migrations**: uma única migration inicial.

## 3. gateway — ✅ Pronto (funcional, simples)

- Proxy por prefixo de path: `auth/tenants/users` → platform-service; `pipelines/stages/contact-statuses/contacts` → crm-service.
- Erros 502/404 tratados, `X-Request-ID` propagado.

## 4. frontend — ⚠️ Parcial (só cobre auth)

- **Pronto**: login, registro, `AuthContext.tsx` (sessão em `localStorage`), hooks (`useLogin`, `useRegister`, `useRequireAuth`), proteção de rota.
- **`lib/api.ts` só tem `login()` e `register()`** — nenhuma chamada para contacts/pipelines/stages.
- **Dashboard é placeholder puro**: texto "Plataforma em construção", nome do usuário e botão de logout. **Nenhuma tela de Kanban ou lista de contatos existe.**

## 5. docs/ — ✅ Convenções estabelecidas

`SECURITY.md`, `DESIGN_SYSTEM.md`, `LOGGING.md`, `PERFORMANCE.md`, `TESTING.md` funcionam como checklists permanentes. Destaques: bcrypt para senhas, tokens sempre hash+expiração, apenas platform-service emite JWT, identidade visual definida (logo pendente).

## Resumo — o que falta para o CRM ser utilizável de ponta a ponta

1. **UI do CRM no frontend** — nada existe (maior gap hoje).
2. **Deal/Oportunidade** — sem isso não há "funil de vendas" real, só contatos organizados em colunas.
3. **Activity/Task** — sem follow-ups, sem lembretes.
4. **Relatórios/métricas de funil**.
5. **UI de gestão de usuários/convites** (backend já existe).
6. Histórico incremental de migrations (hoje é tudo squash em uma migration por serviço).
7. `conversation-service` (WhatsApp/IA) — schema do Tenant já prevê, nada implementado.

Ver [ROADMAP.md](ROADMAP.md) para priorização e [TASKS.md](TASKS.md) para o checklist de execução.
