"""Schemas de entrada das rotas de tenant."""
from typing import Literal, Optional, Union
from pydantic import BaseModel


class TenantUpdateBody(BaseModel):
    """Schema do PATCH: todo campo opcional (so atualiza o que vier
    preenchido — ver model_dump(exclude_unset=True) no service). Validar com
    Pydantic aqui evita que um valor de tipo errado (ex.: numero no lugar de
    texto) vire erro 500 direto do Postgres."""
    business_name:    Optional[str] = None
    phone:            Optional[str] = None
    email:            Optional[str] = None
    city:             Optional[str] = None
    state:            Optional[str] = None
    address:          Optional[str] = None
    whatsapp:         Optional[str] = None
    instagram:        Optional[str] = None
    facebook:         Optional[str] = None
    website:          Optional[str] = None
    system_prompt:    Optional[str] = None
    fallback_message: Optional[str] = None
    ai_provider:      Optional[Literal["deepseek"]] = None  # so deepseek por enquanto — mais providers entram depois
    ai_model:         Optional[str] = None
    faq_enabled:      Optional[bool] = None
    # Segredo: o GET devolve um booleano ("existe chave?"), entao o front pode
    # reenviar esse bool sem querer. Aceita bool aqui pra nao rejeitar o PATCH
    # inteiro com 422 — o service so aplica de fato quando vier string nao vazia.
    ai_api_key:       Optional[Union[str, bool]] = None
