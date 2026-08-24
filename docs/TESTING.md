# Testes — padrões a seguir em toda mudança

Este arquivo não é histórico do que foi feito — é checklist do que **sempre**
se aplica ao escrever/mudar código neste projeto, em qualquer serviço.

## Ferramentas

- **pytest** como test runner em todo serviço Python.
- **FastAPI `TestClient`** (via `httpx`) pra testes de rota — sobe o app em
  memória, sem precisar de um processo `uvicorn` rodando.
- **pytest-cov** pra medir cobertura quando fizer sentido revisar (não é
  gate automático ainda — sem CI configurado).

## Onde os testes vivem

Cada serviço tem sua própria pasta `tests/`, espelhando a estrutura de
`app/`:

```
platform-service/
  app/auth/service.py
  tests/auth/test_service.py
  tests/auth/test_routes.py
```

Teste de `service.py` = unitário (lógica de negócio, sem subir o app).
Teste de `routes.py` = integração (via `TestClient`, HTTP de verdade contra
o app, banco real de teste).

## Banco de dados nos testes

- Testes de integração rodam contra um Postgres real (não SQLite, não mock)
  — schema diferente do banco de dev, nunca o de produção.
- Cada teste roda dentro de uma transação que é revertida no final
  (`SAVEPOINT`/rollback) — testes nunca deixam dado sujo pra trás nem
  dependem de ordem de execução entre si.
- Nunca mockar o banco pra "simplificar" um teste de integração — isso
  já causou divergência entre teste e produção antes (ver reasoning
  em SECURITY.md sobre confiar em comportamento real do Postgres, ex.:
  constraints únicas).

## O que sempre testar (não só o caminho feliz)

Pra toda rota/função nova, cobrir no mínimo:

- **Caminho feliz** — a operação funciona com input válido.
- **Cada `HTTPException` que a função pode levantar** — um teste por
  condição de erro (ex.: `authenticate_user`: senha errada, usuário
  inativo, tenant inativo são 3 testes, não 1).
- **Fronteira de RBAC** — toda rota protegida por `require_role`/
  `require_admin`/`require_owner` tem um teste confirmando que o nível
  abaixo do exigido toma 403 (não só que o nível certo passa).
- **Isolamento multi-tenant** — toda rota que recebe `tenant_id` tem um
  teste confirmando que um usuário de outro tenant não acessa (403/404,
  nunca vazamento de dado de tenant errado).
- **Idempotência/uso único** onde se aplica (token de reset/convite usado
  duas vezes deve falhar na segunda).

## O que mockar vs. o que não mockar

- **Mockar**: chamadas HTTP pra fora do sistema (Resend/email, e futuramente
  LLM/WhatsApp) — não depender de serviço externo real pra suite passar.
- **Nunca mockar**: o próprio banco de dados do serviço, nem chamadas
  internas entre serviços do próprio sistema (ex.: `crm-service` chamando
  `platform-service`) — isso é comportamento real que precisa ser validado
  de verdade, não assumido.

## Testes end-to-end entre serviços

Além dos testes por serviço, fluxos que atravessam mais de um serviço (ex.:
login pelo gateway → platform-service) devem ter pelo menos um teste manual
documentado (via `curl`/script) antes de considerar a mudança pronta —
formalizar em suite automatizada de integração entre serviços quando existir
mais de 2 serviços se comunicando de verdade.

## Nomenclatura

- Arquivo: `test_<modulo>.py`. Função: `test_<o_que>_<condicao_esperada>`
  (ex.: `test_login_com_senha_errada_retorna_401`) — o nome do teste sozinho
  já diz o que quebrou, sem precisar abrir o arquivo.
