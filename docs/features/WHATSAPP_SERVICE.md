# Feature: whatsapp-service (instâncias + atendimentos)

> Versão simplificada para o primeiro momento. Transcrito do legado `Chatbot/chat-api`, mudando só a arquitetura (serviço próprio em vez de módulo dentro de um backend só). Nada de IA, automações, multi-canal ou features que o legado tinha como avançadas — só o essencial pra abrir o WhatsApp via QR code e atender.

## Escopo desta fase

1. Tela de **Conexões**: gerar QR code, escanear, ver status conectado/desconectado.
2. Tela de **Atendimentos**: lista de conversas + chat, responder manualmente.

Fora disso, **nada**: sem IA/bot, sem WhatsApp Cloud API oficial, sem vínculo automático com Contact do crm-service, sem tracking de status de entrega, sem retenção configurável, sem resync de webhook como feature separada. Se algo disso for necessário depois, vira um documento novo.

## Serviço novo: `services/whatsapp-service`

Mesma stack dos outros serviços (FastAPI + SQLAlchemy + Alembic), mesmo padrão de JWT/RBAC do platform-service. Usa **Evolution API** (self-hosted, Baileys) via webhook — é a integração que o legado já valida em produção, não reinventar.

## Modelo de dados (mínimo)

### `Connection`

| Campo | Observação |
|---|---|
| `id` | PK |
| `tenant_id` | Isolamento multi-tenant |
| `instance_name` | Único, gerado |
| `phone` | Preenchido após conectar |
| `status` | `connecting` / `connected` / `disconnected` |

### `Session` (uma conversa por telefone)

| Campo | Observação |
|---|---|
| `id` | `"{tenant_id}:{phone}"` |
| `connection_id` | FK `Connection` |
| `contact_name` | Nome vindo do WhatsApp (perfil), só pra exibir no inbox — **não** é o Contact do crm-service |
| `is_open` | Atendimento aberto/fechado |
| `last_activity` | Ordenação do inbox |

### `Message`

| Campo | Observação |
|---|---|
| `session_id` | FK `Session` |
| `role` | `user` (cliente) / `attendant` (humano) |
| `content` | Texto |
| `created_at` | — |

Sem `delivery_status`, sem `is_fallback` (não existe fallback, não existe IA). Sem política de retenção agora — se o volume virar problema, resolve-se depois com um índice/expurgo simples, não precisa decidir hoje.

## Sem integração com o crm-service (por enquanto)

O legado ligava a conversa ao Contact e usava isso pra alimentar o Kanban automaticamente. Isso é a parte mais fácil de virar overengineering na tradução pra microsserviços (banco separado = precisaria de chamada HTTP entre serviços, cache local, tratamento de falha, etc.), e você pediu explicitamente sem automação nesta fase.

**Decisão**: `Session` guarda só o nome que vem do próprio WhatsApp. Não cria Contact automaticamente, não move nada em nenhum Kanban. O atendente que achar necessário cria o cliente manualmente na tela de Clientes (ver [CLIENTES_ESTAGIOS.md](CLIENTES_ESTAGIOS.md)). Automação de "mensagem nova vira Contact" fica anotada como possível fase futura, não como parte deste documento.

## Fluxo de conexão (QR code)

1. `POST /connections` → gera `instance_name`, chama a Evolution API pra criar a instância com QR code.
2. Salva `Connection` local com `status=connecting`.
3. Configura o webhook da instância na Evolution apontando para `POST /webhook/evolution` deste serviço.
4. Retorna o QR code (base64) pro frontend mostrar.
5. Frontend faz polling em `GET /connections` até `status=connected`.
6. `DELETE /connections/{id}` remove a instância na Evolution e a linha local.

Nada de endpoint de "resync webhook" separado nesta fase — se o webhook precisar ser reconfigurado, basta recriar a conexão. Simplifica a v1; revisitar só se isso doer na prática.

## Fluxo de atendimento

1. `POST /webhook/evolution` recebe a mensagem, valida um header secreto simples, ignora duplicata por `message.id`.
2. Resolve `Connection` pelo `instance_name`, resolve/cria `Session` pelo telefone.
3. Salva `Message(role=user)`.
4. Notifica o painel em tempo real via WebSocket (`/ws/{tenant_id}`).
5. Atendente responde pelo painel: `POST /chat/{session_id}/responder` → envia via Evolution → salva `Message(role=attendant)` → notifica via WebSocket.
6. Atendente pode encerrar (`is_open=false`).

Mensagens mandadas do próprio celular do atendente (fora do painel) também chegam pelo mesmo webhook — trate como `role=attendant` e só grave, sem lógica especial além disso.

## Endpoints

- `POST /connections`, `GET /connections`, `DELETE /connections/{id}`
- `POST /webhook/evolution` (autenticado por secret, não por JWT — quem chama é a Evolution, não um usuário logado)
- `GET /sessoes` (lista de conversas), `GET /chat/{session_id}/mensagens`, `POST /chat/{session_id}/responder`
- `WS /ws/{tenant_id}` (JWT via query param)

## Frontend

### Tela de Conexões

- Lista de conexões do tenant com status.
- Botão "Conectar" → mostra QR code, aguarda ficar `connected` (polling simples).
- Botão de excluir.
- Restrito a owner/admin.

### Tela de Atendimentos

- Lista de conversas (nome + preview da última mensagem).
- Chat ao selecionar: histórico + campo de resposta.
- Atualização via WebSocket.
- Botão de encerrar atendimento.

## Integração no gateway

Adicionar ao `SERVICE_ROUTES`: prefixos `connections`, `webhook`, `sessoes`, `chat` → `whatsapp-service`.

## Fora de escopo (não implementar agora)

- IA/bot, `system_prompt`, fallback automático.
- WhatsApp Cloud API oficial.
- Vínculo automático mensagem → Contact/Kanban.
- Tracking de status de entrega, atribuição de conversa a atendente, retenção configurável.
