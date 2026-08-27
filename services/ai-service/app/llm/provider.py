"""Selecao de provider por tenant — porta simplificada de Chatbot/chat-api/
ai/llm/provider.py: o legado alternava entre groq/openrouter com fallback
automatico; por enquanto so existe deepseek, entao nao ha fallback pra
"outro provider" (so um existe). A estrutura fica pronta pra crescer: novo
provider = nova classe em app/llm/ + um `elif` aqui, sem mexer no resto."""
from typing import Any, Dict

from fastapi import HTTPException

from app.llm.deepseek import DeepSeekLLM
from shared.logging_config import get_logger

logger = get_logger("ai-service")


def get_llm(tenant: Dict[str, Any]):
    provider = tenant.get("ai_provider") or "deepseek"

    if provider == "deepseek":
        key = tenant.get("ai_api_key")
        if not key:
            raise HTTPException(status_code=400, detail="Provedor de IA selecionado mas chave não configurada")
        return DeepSeekLLM(key, tenant.get("ai_model"))

    raise HTTPException(status_code=400, detail=f"Provedor de IA \"{provider}\" não suportado")


async def run_chat(tenant: Dict[str, Any], tenant_id: str, history: list, user_message: str, db) -> str:
    llm = get_llm(tenant)
    return await llm.chat_response(tenant, tenant_id, history, user_message, db)
