# Desempenho — padrões a seguir em toda mudança

Este arquivo não é histórico do que foi feito — é checklist do que **sempre**
se aplica ao escrever código novo neste projeto, em qualquer serviço.

## N+1

- Nunca acessar uma `relationship` dentro de um loop sobre uma lista vinda
  do banco sem eager loading — isso dispara 1 query por item. Usar
  `joinedload`/`selectinload` na query original quando o endpoint vai
  precisar do relacionamento pra cada linha (ex.: listar users e mostrar o
  nome do tenant de cada um).
- Se um endpoint lista N registros e depois faz outra query "por registro"
  (inclusive pra outro serviço via HTTP), isso é N+1 também — resolver
  buscando em lote (`WHERE id IN (...)` ou uma chamada HTTP só, com lista de
  ids) em vez de um round-trip por item.

## Índices

- Toda coluna usada em `.filter()`/`WHERE` com frequência (FK que aparece em
  listagem, campo usado pra dedup/lookup) precisa de índice — não confiar só
  na PK.
- Hoje existem: `ix_password_reset_tokens_user` (lookup por `user_id`),
  `ix_invites_tenant` (listagem de convites por tenant). Todo model novo que
  tiver um padrão de acesso parecido (buscar por FK, listar por tenant)
  segue o mesmo padrão.
- `UniqueConstraint`/índice único quando a regra de negócio exige unicidade
  (ex.: `email` em `users`) — não confiar só em checagem na aplicação, que
  tem race condition.

## Paginação

- Toda listagem que pode crescer sem limite (mensagens, contatos, etc.)
  precisa de paginação desde o primeiro dia — não implementar "lista tudo"
  com a intenção de paginar depois (isso quebra contrato de API depois).
- Hoje nenhuma listagem do platform-service tem esse risco (times e convites
  por tenant são naturalmente pequenos) — mas o padrão vale a partir do
  primeiro model que não tiver esse limite natural.

## Conexão com banco

- Uma sessão (`Session`) por requisição, sempre fechada no `finally` (ver
  `shared/db.py::make_db`) — nunca reusar sessão entre requisições nem
  deixar aberta além do escopo da requisição.

## Chamadas HTTP entre serviços

- Client HTTP assíncrono é singleton por processo com connection pool
  (`shared/http_client.py`) — nunca criar um `httpx.AsyncClient()` novo a
  cada chamada (perde reuso de conexão TCP/TLS).
