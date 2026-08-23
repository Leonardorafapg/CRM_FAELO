# CRM FAELO

CRM com pré-atendimento/atendimento completo (IA e/ou humano), construído
como microsserviços independentes — cada um é uma API própria, com sua
própria URL e seu próprio banco.

## Serviços

| Serviço | Pasta | URL (dev) | Status |
|---|---|---|---|
| **platform-service** | `services/platform-service` | `:8001` | Auth, Tenant, User/RBAC, Invites |
| **crm-service** | — | `:8002` | Contacts, Pipeline/Stage (planejado) |
| **conversation-service** | — | `:8003` | Conversas, WhatsApp, IA (planejado) |

`services/shared/` é uma lib Python instalada localmente (`pip install -e ../shared`)
por cada serviço — não é um serviço, é código compartilhado (verificação de
JWT, RBAC, base de banco, HTTP client, logging).

## Rodando o platform-service localmente

```bash
cd services/platform-service
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env            # preencher DATABASE_URL/JWT_SECRET_KEY/INTERNAL_SERVICE_KEY
alembic upgrade head
uvicorn main:app --reload --port 8001
```
