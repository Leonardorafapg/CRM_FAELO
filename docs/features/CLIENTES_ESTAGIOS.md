# Feature: Cadastro de Clientes e Quadros (Kanban)

> Versão simplificada para o primeiro momento: sem automações, sem vínculo com WhatsApp, sem campos extras do legado que não são essenciais. Serviço responsável: **crm-service** (já existe — ver [STATUS.md](../STATUS.md)).

## O que já existe no crm-service (reaproveitar, não recriar)

- `Contact`: nome, telefone, email, tags, status.
- `Pipeline` (quadro) e `Stage` (coluna do quadro), multi-pipeline.
- CRUD completo + RBAC + testes.

Isso já cobre o pedido — **não é necessário mudar o backend agora**, só construir a UI que falta (frontend não tem nenhuma tela pra isso ainda).

## Escopo desta fase

1. Cadastro manual de clientes (formulário simples: nome, telefone, email, tags).
2. Criação de quadros e colunas (pipeline/stage), simples: nome e ordem — sem regras automáticas de entrada, sem cor obrigatória, sem campo customizado.
3. Mover cliente de coluna manualmente (arrastar ou botão).

Sem automação nenhuma: nada move um cliente de coluna sozinho, nada cria cliente sozinho. Toda ação é manual, disparada pelo usuário na tela.

## Frontend a construir

### Tela de Clientes

- Lista/tabela simples de contacts.
- Botão de criar cliente (nome, telefone, email, tags).
- Editar/excluir.

### Tela de Quadros (Kanban)

- Seletor de pipeline (se houver mais de um).
- Colunas = stages, cards = contacts.
- Botão "mover para →" é suficiente — **não** introduzir biblioteca de drag-and-drop nesta fase; só considerar se o usuário pedir explicitamente depois de ver a versão simples funcionando.
- Tela separada (ou modal) pra criar/renomear/reordenar quadro e colunas — restrito a owner/admin, igual ao backend já garante.

## Fora de escopo (não implementar agora)

- Qualquer campo novo em `Contact` (foto, origem, campos customizados) — só adicionar se/quando surgir necessidade concreta.
- Entrada automática de cliente numa coluna específica (isso depende de uma origem automática, ex. WhatsApp, que não existe nesta fase — ver [WHATSAPP_SERVICE.md](WHATSAPP_SERVICE.md)).
- Deal/Oportunidade, relatórios de funil.
