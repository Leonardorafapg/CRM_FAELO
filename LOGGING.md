# Logs e mapeamento de erros — padrões a seguir em toda mudança

Este arquivo não é histórico do que foi feito — é checklist do que **sempre**
se aplica ao escrever/mudar código neste projeto, em qualquer serviço.

## Infra de logging (já existe, reusar sempre — `shared/logging_config.py`)

- Todo serviço chama `setup_logging("<nome-do-servico>")` uma vez no boot
  (`main.py`) e usa `get_logger("<nome-do-servico>")` — nunca
  `logging.getLogger(__name__)` direto nem `print()`.
- Todo log carrega `request_id` automaticamente (via `RequestIdFilter`) —
  nunca formatar manualmente um id de correlação na mensagem.

## Correlação entre serviços

- O **gateway** gera/repassa `X-Request-ID` pra todo serviço interno que
  chama — um mesmo `request_id` aparece nos logs do gateway E do serviço que
  atendeu. Toda chamada nova servico-a-servico (ex.: `crm-service` chamando
  `platform-service`) precisa repassar esse header, nunca gerar um novo id
  no meio do caminho.
- Ao investigar um bug relatado pelo usuário, o primeiro passo é achar o
  `request_id` (devolvido no header `X-Request-ID` de toda resposta) e
  filtrar os logs por ele.

## Níveis de log

| Nível | Quando usar |
|---|---|
| `ERROR` | Exceção não esperada, falha de integração externa (email, futuramente LLM/WhatsApp) que impede completar a operação. Sempre com `exc_info=True` quando é uma exceção. |
| `WARNING` | Ação administrativa sensível (desativar tenant, remover usuário) e tentativa bloqueada que pode indicar abuso (rate limit estourado, token inválido rejeitado). |
| `INFO` | Mudança de estado relevante de negócio (tenant atualizado, convite criado) — não toda leitura (`GET`), só o que muda dado. |
| `DEBUG` | Não usado ainda neste projeto — não introduzir sem necessidade concreta de investigação. |

Nunca logar em `ERROR` algo que é erro de input do usuário (400/401/403/404
esperado) — isso é ruído que esconde erro real. `ERROR` é reservado pra
"algo quebrou que não deveria".

## Mapeamento de exceção → resposta HTTP

- Toda regra de negócio violada levanta `HTTPException` com status code
  específico (`400` validação, `401` não autenticado, `403` sem permissão,
  `404` não encontrado) — nunca deixar propagar uma exceção genérica pra
  representar um erro de negócio esperado.
- Mensagens de erro devem ser genéricas quando revelar detalhe ajuda um
  atacante (ex.: login não diz se foi email ou senha errada — ver
  SECURITY.md) e específicas quando ajuda o usuário legítimo a corrigir
  (ex.: "Email já cadastrado").
- **Exceção não tratada** (bug de verdade) é pega pelo
  `@app.exception_handler(Exception)` central de cada `main.py` — sempre
  loga `ERROR` com `exc_info=True` e `request_id`, e devolve `500` genérico
  pro cliente (nunca vaza stacktrace/detalhe interno na resposta).
- Nunca adicionar `try/except` genérico numa rota só pra "engolir" erro —
  se uma exceção não é uma regra de negócio conhecida, ela deve subir até o
  handler central, não ser mascarada silenciosamente.

## O que sempre logar

- Toda tentativa de autenticação falha (login errado, token inválido/
  expirado rejeitado) — nível `WARNING` se for token malformado (possível
  scan/ataque), sem log adicional se for só senha errada normal (rate limit
  já cobre o abuso, logar toda tentativa de login errada é ruído).
- Toda ação administrativa que muda estado de outro usuário/tenant
  (desativar, mudar role, deletar) — sempre incluindo *quem* fez (`user_id`
  do ator), não só o alvo.
- Toda falha de chamada a serviço externo (email, e futuramente LLM/
  WhatsApp/serviço interno) — nunca falhar silenciosamente uma integração.

## O que nunca logar

- Senha em texto puro, token de reset/convite em texto puro, `groq_key`
  ou qualquer segredo de tenant — nem em `DEBUG`.
- Corpo inteiro de request/response sem filtrar — pode conter dado
  sensível de cliente do tenant.
