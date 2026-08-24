# Segurança — padrões a seguir em toda mudança

Este arquivo não é histórico do que foi feito — é checklist do que **sempre**
se aplica ao escrever código novo neste projeto, em qualquer serviço.

## Senhas

- Nunca guardar senha em texto puro. Sempre `bcrypt.hashpw` com salt gerado
  na hora (`bcrypt.gensalt()`) — nunca um salt fixo/compartilhado.
- Exigir tamanho mínimo (hoje: 8 caracteres) em todo lugar que define senha
  (registro, reset, aceite de convite).
- Ver `app/auth/routes.py::_hash_password` / `_verify_password` (platform-service).

## Tokens de uso único (reset de senha, convite)

- Nunca guardar o token em texto puro no banco — só o hash (`sha256`).
- O valor puro existe só no link enviado por email, nunca é persistido.
- Sempre ter `expires_at` E um campo de "usado" (`used_at`/`accepted_at`) —
  os dois juntos, não um só. Um token usado fica inutilizável mesmo dentro
  da janela de validade.
- Gerar um token novo pro mesmo propósito invalida o anterior (nunca deixar
  dois links válidos pra mesma ação).
- Ver `app/auth/routes.py::_hash_token`, `PasswordResetToken`, `Invite`.

## JWT

- Sempre tem `exp` (expiração) — nenhum token deve ser eterno.
- Só o serviço dono do domínio (hoje: platform-service) EMITE token.
  Qualquer outro serviço só verifica, usando o mesmo `JWT_SECRET_KEY`
  (nunca reimplementar emissão em outro lugar).
- Nunca colocar dado sensível no payload (ele não é criptografado, só
  assinado — qualquer um pode decodificar e ler, só não pode forjar).

## Segredos do tenant (ex.: `groq_key`)

- Todo GET público devolve booleano ("existe?"), nunca o valor real.
- PATCH só sobrescreve o segredo quando vem uma string nova e não vazia —
  nunca aceitar o booleano do GET de volta como se fosse o valor (senão o
  frontend reenviando o próprio GET apaga o segredo salvo).
- Valor real em texto puro só sai por endpoint `/internal/*` (autenticado
  por `X-Internal-Key`), nunca por rota pública.
- Ver `app/routers/tenants.py::update_tenant`, `app/routers/internal.py`.

## Rate limit

- Toda rota que pode ser abusada por automação (login, registro, forgot-
  password, criação de convite) tem `@limiter.limit(...)`.
- Mensagens de erro de login/forgot-password são genéricas de propósito
  (não revelam se o email existe) — evita enumeração de contas.

## Autorização (RBAC)

- Nunca checar `current_user["role"]` direto numa rota — sempre usar
  `Depends(require_role(...))` / `require_admin` / `require_owner`
  (`shared/policy.py`), pra manter a matriz de permissão num lugar só.
- Rota com `{tenant_id}` no path sempre combina `require_own_tenant` (ou
  checagem equivalente) COM `require_role` — nível de permissão sozinho não
  garante que o usuário pertence àquele tenant.
- Toda ação administrativa tem proteção contra auto-lockout/autopromoção
  (ex.: usuário não edita a própria role, tenant sempre mantém 1 owner ativo).

## Serviço-a-serviço

- Endpoints que só outro serviço deve chamar (nunca o frontend) ficam sob
  `/internal/*` e exigem `X-Internal-Key` (`shared/internal_auth.py`) —
  nunca dependem só de "estar numa rede interna" como proteção.

## CORS

- `ALLOWED_ORIGINS` sempre explícito por env, nunca `*` em produção.
