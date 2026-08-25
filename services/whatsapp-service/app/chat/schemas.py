from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SessionOut(BaseModel):
    id: str
    connection_id: str
    phone: str
    contact_name: Optional[str] = None
    is_open: bool
    last_activity: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ResponderBody(BaseModel):
    content: str


class EvolutionWebhookPayload(BaseModel):
    """Formato simplificado do payload que a Evolution API manda no webhook —
    so os campos que este servico realmente usa. instance/messageId/from/text
    variam de nome conforme a versao da Evolution; o parsing tolerante fica
    no service, aqui e so o shape minimo esperado."""
    instance: str
    message_id: str
    phone: str
    role: str  # "user" ou "attendant" (mensagem enviada do proprio celular)
    content: str
    contact_name: Optional[str] = None
