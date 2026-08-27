"""Provider DeepSeek — API compativel com o formato OpenAI de chat
completions. Mesmo estilo do OpenRouterLLM do legado (Chatbot/chat-api/ai/
llm/openrouter.py): chamada crua via httpx, sem SDK propria, usando o
client HTTP compartilhado (shared/http_client.py) em vez de criar um
AsyncClient novo a cada chamada."""
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException

from shared.http_client import get_async_client
from shared.logging_config import get_logger
from app.llm.prompt_builder import build_system_prompt

logger = get_logger("ai-service")

DEEPSEEK_BASE_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"


class DeepSeekLLM:
    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or DEFAULT_MODEL

    async def chat(self, messages: List[Dict[str, Any]], temperature: float = 0.3, max_tokens: int = 1024) -> str:
        """Chamada base: recebe mensagens prontas (incluindo o system
        prompt) e devolve o texto da resposta."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        client = get_async_client()
        try:
            resp = await client.post(DEEPSEEK_BASE_URL, headers=headers, json=payload, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"].get("content") or ""
        except httpx.HTTPError as e:
            logger.error(f"Falha ao chamar DeepSeek: {type(e).__name__}: {e}", exc_info=True)
            raise HTTPException(status_code=502, detail="Falha ao consultar o provedor de IA")

    async def chat_response(self, tenant: Dict[str, Any], tenant_id: str, history: list, user_message: str, db) -> str:
        """Monta o system prompt (dados do tenant + FAQ + horarios) e conduz
        a conversa — historico limitado as ultimas 10 mensagens, mesmo
        criterio do legado."""
        system = build_system_prompt(tenant, tenant_id, db)
        messages = [{"role": "system", "content": system}]
        messages += [{"role": m["role"], "content": m["content"]} for m in history[-10:]]
        if user_message:
            messages.append({"role": "user", "content": user_message})

        return await self.chat(messages)
