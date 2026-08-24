# CRM FAELO

CRM com pré-atendimento/atendimento completo (IA e/ou humano), construído
como microsserviços independentes — cada um é uma API própria, com sua
própria URL e seu próprio banco. O frontend (e qualquer cliente externo)
chama só o **gateway**; os serviços internos nunca ficam expostos direto.

## Serviços

| Serviço | Pasta | URL (dev) | Status |
|---|---|---|---|
| **gateway** | `services/gateway` | `:8000` | Ponto de entrada público — distribui requisições por prefixo de rota |
| **platform-service** | `services/platform-service` | `:8001` | Auth, Tenant, User/RBAC, Invites |
| **crm-service** | — | `:8002` | Contacts, Pipeline/Stage (planejado) |
| **conversation-service** | — | `:8003` | Conversas, WhatsApp, IA (planejado) |

`services/shared/` é uma lib Python instalada localmente (`pip install -e ../shared`)
por cada serviço — não é um serviço, é código compartilhado (verificação de
JWT, RBAC, base de banco, HTTP client, logging).

## Rodando localmente (gateway + platform-service)

```bash
# platform-service
cd services/platform-service
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env            # preencher DATABASE_URL/JWT_SECRET_KEY/INTERNAL_SERVICE_KEY
alembic upgrade head
uvicorn main:app --reload --port 8001

# gateway (outro terminal)
cd services/gateway
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

O frontend passa a chamar `http://localhost:8000` (o gateway), não mais cada
serviço direto. `/auth`, `/tenants`, `/users` já roteiam pro platform-service;
`/contacts`, `/pipelines`, `/stages` (crm-service) e `/conversations`,
`/webhooks` (conversation-service) já têm rota reservada no gateway e vão
funcionar assim que esses serviços forem construídos — até lá devolvem 502.
