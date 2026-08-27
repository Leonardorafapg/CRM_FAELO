"""Interface comum de provider de LLM — cada provider (DeepSeek, etc.) em
app/llm/ implementa esta classe. Montagem do prompt fica em
app/llm/prompt_builder.py, separado daqui de proposito: sao preocupacoes
diferentes (contrato de provider vs. conteudo do prompt)."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: List[Dict[str, Any]]) -> Any:
        """Recebe a lista de mensagens (incluindo o system prompt) e devolve
        a resposta de texto."""
        raise NotImplementedError
