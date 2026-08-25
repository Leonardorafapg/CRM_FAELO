# Do legado (Faelo/Chatbot) para o CRM-FAELO: só a arquitetura muda

> Referência: `C:\Users\Leonardo\Desktop\Chatbot` (monolito modular: `chat-api` + `chat-pannel`).

## Regra geral de tradução

O legado (`chat-api`) é um único backend FastAPI com um banco só, organizado em módulos internos: `core/identity`, `core/tenant`, `core/contacts`, `core/pipeline`, `core/conversations`, mais `ai/` e `infra/`. Toda a lógica de negócio e os modelos de dados descritos nos documentos desta pasta **são os mesmos** do legado — o que muda é:

| Módulo do legado | Destino no CRM-FAELO |
|---|---|
| `core/identity`, `core/tenant` | já existe: **platform-service** |
| `core/contacts`, `core/pipeline` | já existe: **crm-service** (ver [CLIENTES_ESTAGIOS.md](CLIENTES_ESTAGIOS.md)) |
| `core/conversations`, `infra/evolution.py`, webhooks, WebSocket | novo: **whatsapp-service** (ver [WHATSAPP_SERVICE.md](WHATSAPP_SERVICE.md)) |
| `ai/` (LLM) | fora de escopo por ora — futuro `conversation-service`/IA (ver [STATUS.md](../STATUS.md)) |
| `chat-pannel` (um frontend só) | mesmas telas, mas consumindo múltiplos serviços via gateway em vez de um backend só |

## O que muda de fato

1. **Banco de dados**: no legado, `Contact` e `Session` estavam no mesmo banco. Na nova arquitetura, `crm-service` e `whatsapp-service` têm bancos separados. **Nesta primeira fase, isso não é um problema porque os dois nem estão ligados** — sem vínculo automático entre conversa do WhatsApp e cadastro de cliente (ver [WHATSAPP_SERVICE.md](WHATSAPP_SERVICE.md#sem-integração-com-o-crm-service-por-enquanto)). Se essa ligação virar necessidade real depois, aí sim vale desenhar a chamada entre serviços — não antes.
2. **Autenticação**: já resolvido — igual ao legado, JWT emitido só pelo platform-service, verificado pelos demais via segredo compartilhado (`shared`). Nenhuma mudança necessária aqui, só reaproveitar.
3. **Gateway**: o legado não tinha gateway (um processo só). O CRM-FAELO já tem um proxy por prefixo de path — só precisa adicionar as novas rotas do whatsapp-service (`connections`, `webhook`, `sessoes`, `chat`) ao `SERVICE_ROUTES`.
4. **Deploy/infra**: cada serviço agora sobe/reinicia independente — não há mudança de comportamento esperada pelo usuário final, só operacional.

## O que NÃO muda

- Nomes de campos, regras de negócio (ex: `is_entry` stage, status vs. stage independentes, dedup de mensagem por `message.id`, resposta sempre pelo mesmo número que recebeu).
- Stack tecnológica por camada (FastAPI/SQLAlchemy/Alembic no backend, Next.js/React/TypeScript no frontend, Evolution API para WhatsApp, WebSocket nativo para tempo real).
- Fluxos de UI (Kanban drag-and-drop nativo, inbox de atendimento, tela de QR code) — a ideia é o usuário final não perceber diferença nenhuma de UX, só ganhar a escalabilidade/isolamento dos microsserviços por trás.

## Documentos desta pasta

- [CLIENTES_ESTAGIOS.md](CLIENTES_ESTAGIOS.md) — cadastro de clientes e Kanban de estágios (crm-service).
- [WHATSAPP_SERVICE.md](WHATSAPP_SERVICE.md) — instâncias de WhatsApp e tela de atendimentos (novo whatsapp-service).

Ver [../ROADMAP.md](../ROADMAP.md) para onde essas features entram na priorização geral, e [../TASKS.md](../TASKS.md) para o checklist de execução atualizado.
