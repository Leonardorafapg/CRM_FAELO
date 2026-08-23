import os
from shared.http_client import get_async_client
from shared.logging_config import get_logger

logger = get_logger("platform-service")

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")


async def send_password_reset_email(to_email: str, reset_url: str) -> None:
    """Envia o email de recuperacao de senha via API da Resend. Se a chave
    nao estiver configurada (ex.: ambiente de dev sem conta Resend), so loga
    o erro e retorna — nao quebra o fluxo de forgot-password (que sempre
    devolve mensagem generica de sucesso pro frontend de qualquer forma)."""
    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY nao configurada — email de recuperacao nao enviado")
        return

    client = get_async_client()
    try:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={
                "from": RESEND_FROM_EMAIL,
                "to": [to_email],
                "subject": "Recuperação de senha",
                "html": (
                    f"<p>Recebemos um pedido para redefinir sua senha.</p>"
                    f'<p><a href="{reset_url}">Clique aqui para criar uma nova senha</a></p>'
                    f"<p>Esse link expira em 1 hora. Se você não pediu isso, ignore este email.</p>"
                ),
            },
        )
        resp.raise_for_status()
    except Exception as e:
        # Falha de envio nunca deve propagar como erro pro usuario que pediu
        # o reset — so registra pra investigacao manual.
        logger.error(f"Erro ao enviar email de recuperacao de senha: {e}", exc_info=True)


async def send_team_invite_email(to_email: str, invite_url: str, tenant_name: str, inviter_name: str | None) -> None:
    """Envia o email de convite pra entrar num tenant. Mesma logica de
    tolerancia a falha do send_password_reset_email — nao derruba o fluxo de
    criar_convite (routers/users.py) se o email nao sair."""
    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY nao configurada — email de convite nao enviado")
        return

    convidado_por = f" por {inviter_name}" if inviter_name else ""
    client = get_async_client()
    try:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={
                "from": RESEND_FROM_EMAIL,
                "to": [to_email],
                "subject": f"Convite para entrar em {tenant_name}",
                "html": (
                    f"<p>Você foi convidado{convidado_por} para fazer parte da equipe de "
                    f"<strong>{tenant_name}</strong>.</p>"
                    f'<p><a href="{invite_url}">Clique aqui para aceitar o convite</a></p>'
                    f"<p>Esse link expira em 7 dias. Se você não esperava este convite, ignore este email.</p>"
                ),
            },
        )
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Erro ao enviar email de convite: {e}", exc_info=True)
