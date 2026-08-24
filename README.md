# CRM FAELO

CRM com pré-atendimento/atendimento completo (IA e/ou humano), construído
como microsserviços independentes — cada um é uma API própria, com sua
própria URL e seu próprio banco. O frontend (e qualquer cliente externo)
chama só o **gateway**; os serviços internos nunca ficam expostos direto.

Construção incremental: só existe no código o que já foi pedido e
construído.

## Documentação

Checklists permanentes que valem pra toda mudança futura, não histórico do
que foi feito — ver `docs/`:

- `docs/SECURITY.md` — padrões de segurança (senha, tokens, JWT, RBAC, CORS)
- `docs/PERFORMANCE.md` — N+1, índices, paginação, pool de conexão
- `docs/TESTING.md` — como e o que testar em cada mudança
- `docs/LOGGING.md` — níveis de log, correlação entre serviços, mapeamento de erro
- `docs/DESIGN_SYSTEM.md` — identidade visual e arquitetura de UI alvo do frontend

## Serviços

| Serviço | Pasta | URL (dev) | Status |
|---|---|---|---|
| **gateway** | `services/gateway` | `:8000` | Ponto de entrada público — distribui requisições por prefixo de rota |
| **platform-service** | `services/platform-service` | `:8001` | Auth, Tenant, User/RBAC, Invites |
| **crm-service** | `services/crm-service` | `:8002` | Pipeline/Stage (Kanban multi-pipeline), Contact/ContactStatus — CRM manual, sem IA/WhatsApp ainda |

`services/shared/` é uma lib Python instalada via git (`requirements.txt`
aponta pro subdiretório `services/shared` deste mesmo repositório) por cada
serviço — não é um serviço, é código compartilhado (verificação de JWT,
RBAC, base de banco, HTTP client, logging). Instalação via git (não path
relativo `-e ../shared`) de propósito: cada serviço builda isolado em
produção (Railway builda `services/gateway` e `services/platform-service`
cada um sem enxergar a pasta irmã `services/shared`) — um path relativo
falha nesse cenário. Pra editar `shared/` e testar sem precisar commitar a
cada mudança, reinstale local com `pip install -e ../shared` por cima
(sobrescreve so na sua venv).

## Rodando localmente (gateway + platform-service + crm-service)

Mesmo padrão pros 3 serviços — dentro de cada pasta:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env            # preencher DATABASE_URL (banco proprio) e os segredos
alembic upgrade head            # platform-service e crm-service tem migration; gateway nao tem banco
uvicorn main:app --reload --port <8000|8001|8002>
```

`JWT_SECRET_KEY` precisa ser IGUAL em `platform-service` e `crm-service` —
um emite o token, o outro so verifica.

O frontend chama só `http://localhost:8000` (o gateway). Rotas hoje:
`/auth`, `/tenants`, `/users` → platform-service. `/pipelines`, `/stages`,
`/contacts`, `/contact-statuses` → crm-service.

## Testes

Ver `docs/TESTING.md` pro padrão geral. Mesmo comando pra platform-service e
crm-service (cada um com seu próprio banco de teste, criado na primeira vez):

```bash
cd services/platform-service   # ou services/crm-service
pip install -r requirements-dev.txt
python -c "import psycopg2; c=psycopg2.connect(host='localhost',port=5432,user='postgres',password='SUA_SENHA',dbname='postgres',client_encoding='utf8'); c.autocommit=True; c.cursor().execute('CREATE DATABASE crm_faelo_platform_test')"  # ou crm_faelo_crm_test
pytest
```
