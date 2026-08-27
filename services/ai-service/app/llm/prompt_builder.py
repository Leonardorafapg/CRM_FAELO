"""Montagem do system prompt — porta de Chatbot/chat-api/ai/llm/base.py,
adaptada pra microsservicos: la `tenant` era um objeto ORM local (mesmo
banco); aqui e um dict vindo do GET /internal/tenants/{id} do
platform-service (ver app/tenant_client.py), e a FAQ e consultada no banco
proprio deste servico (app/faq/models.py)."""
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.faq.models import FaqItem

# Fuso do negocio (o servidor roda em UTC no Railway; sem isso o bot erra o
# "hoje" depois das 21h no Brasil).
BR_TZ = ZoneInfo("America/Sao_Paulo")

# Texto padrao usado quando o tenant nao configurou fallback_message proprio.
DEFAULT_FALLBACK_MESSAGE = (
    "Não tenho essa informação no momento, mas posso te conectar "
    "com nossa equipe para esclarecer."
)


def _get_data_atual() -> str:
    dias_pt = {
        "Monday": "Segunda-feira", "Tuesday": "Terça-feira",
        "Wednesday": "Quarta-feira", "Thursday": "Quinta-feira",
        "Friday": "Sexta-feira", "Saturday": "Sábado", "Sunday": "Domingo",
    }
    agora = datetime.now(BR_TZ)
    dia_semana = dias_pt.get(agora.strftime("%A"), "")
    return f"{dia_semana}, {agora.strftime('%d/%m/%Y')} (horário de Brasília, {agora.strftime('%H:%M')})"


def _build_faq_context(tenant_id: str, db: Session) -> str:
    items = db.query(FaqItem).filter(FaqItem.tenant_id == tenant_id).all()
    if not items:
        return ""

    lines = ["PERGUNTAS FREQUENTES (Use APENAS estas respostas para responder ao cliente):"]
    for item in items:
        lines.append(f"P: {item.pergunta}\nR: {item.resposta}")
    return "\n\n".join(lines)


def _build_business_hours_context(business_hours: Optional[List[dict]]) -> str:
    """Cada item de `slots` ja e um intervalo completo ({"from": "09:00",
    "to": "18:00"}) — diferente do sistema de agendamento do legado, que
    guardava uma lista de marcadores de 30min e precisava inferir o fim.
    Aqui e so formatar o intervalo que ja existe, sem inventar duracao."""
    if not business_hours:
        return ""

    day_names = {0: "Segunda", 1: "Terça", 2: "Quarta", 3: "Quinta", 4: "Sexta", 5: "Sábado", 6: "Domingo"}
    open_days: List[str] = []
    closed_days: List[str] = []

    for bh in sorted(business_hours, key=lambda x: x["day_of_week"]):
        label = day_names.get(bh["day_of_week"], str(bh["day_of_week"]))
        if bh.get("is_closed"):
            closed_days.append(label)
            continue
        slots = bh.get("slots") or []
        if not slots:
            continue
        periods = [f"{slot['from']}-{slot['to']}" for slot in slots]
        open_days.append(f"{label}: {' e '.join(periods)}")

    context = ""
    if open_days:
        context += "\nHORÁRIOS DE FUNCIONAMENTO:\n"
        for d in open_days:
            context += f"- {d}\n"
    if closed_days:
        context += f"- Fechado: {', '.join(closed_days)}\n"
    return context


def build_system_prompt(tenant: Dict[str, Any], tenant_id: str, db: Session) -> str:
    """`tenant` e o dict devolvido por GET /internal/tenants/{id} do
    platform-service (business_name, phone, address, system_prompt,
    business_hours, etc.) — este servico nunca guarda dado de identidade do
    tenant, so consulta ele por chamada interna."""
    business_name = tenant.get("business_name") or "nossa empresa"
    phone = tenant.get("phone")
    whatsapp = tenant.get("whatsapp")
    instagram = tenant.get("instagram")
    facebook = tenant.get("facebook")
    website = tenant.get("website")
    email = tenant.get("email")
    address = tenant.get("address")
    city = tenant.get("city")
    system_prompt = tenant.get("system_prompt")
    fallback_text = tenant.get("fallback_message") or DEFAULT_FALLBACK_MESSAGE

    contact = phone or whatsapp or "nosso contato direto"

    prompt = f"Você é a assistente virtual da {business_name}.\n"
    prompt += "Idioma: português brasileiro. Tom: profissional e cordial.\n"
    prompt += f"Hoje é: {_get_data_atual()}\n\n"

    prompt += "COMPORTAMENTO E ESTILO DE RESPOSTA:\n"
    prompt += "- Seja muito simpático, acolhedor e natural (como um atendente humano real).\n"
    prompt += "- LIMITE DE TAMANHO (regra rígida, vale mais que qualquer outra instrução de conteúdo): cada mensagem tem NO MÁXIMO 3 frases curtas, divididas em no máximo 2 parágrafos. Nunca escreva um texto explicativo longo, mesmo que o assunto pareça exigir.\n"
    prompt += "- NO MÁXIMO 1 pergunta por mensagem. Nunca empilhe várias perguntas ou vários pontos de venda na mesma resposta.\n"
    prompt += "- Não repita informação que você já deu antes na conversa só para reforçar ou parecer completo. Se já disse, não diga de novo.\n"
    prompt += "- RESPONDA SÓ O QUE FOI PERGUNTADO. Não ofereça, cite ou detalhe proativamente outros produtos, serviços ou diferenciais que o cliente não pediu — mesmo que estejam listados abaixo.\n"
    prompt += "- Nunca diga que é uma IA ou robô. Comporte-se como um funcionário da casa.\n"
    prompt += f"- Se perguntado se é humano: diga que é o assistente virtual da {business_name}.\n\n"

    prompt += "REGRAS DE FORMATAÇÃO (PADRÃO WHATSAPP):\n"
    prompt += "- Use quebras de linha duplas para separar parágrafos e dar respiro à leitura.\n"
    prompt += "- Sempre que listar mais de um item (produtos, serviços, preços, horários, locais), use listas verticais com emojis amigáveis (ex: 🔹, 📍, 💳, ✅).\n"
    prompt += "- Use o negrito do WhatsApp (*texto*) para destacar termos importantes, como dias da semana, horários, preços ou nomes de produtos/serviços.\n\n"

    prompt += "REGRAS CRÍTICAS:\n"
    prompt += "- NUNCA invente serviços, preços, horários ou informações que não estejam listadas abaixo.\n"
    prompt += "- NUNCA direcione para o contato humano se a informação solicitada já estiver listada abaixo.\n"
    prompt += f"- Direcione para o contato ({contact}) APENAS quando a informação não estiver listada.\n"
    prompt += (
        "- Se a pergunta do cliente NÃO puder ser respondida com as perguntas frequentes, "
        "dados da empresa ou informações adicionais fornecidas abaixo — responda EXATAMENTE com:\n"
        f"  \"{fallback_text}\"\n"
        "- Não tente adivinhar, supor ou inventar respostas em nenhuma circunstância.\n\n"
    )

    prompt += "DADOS DA EMPRESA:\n"
    if address and city:
        prompt += f"- Endereço: {address}, {city}\n"
    elif address:
        prompt += f"- Endereço: {address}\n"
    elif city:
        prompt += f"- Cidade: {city}\n"
    if phone:
        prompt += f"- Telefone: {phone}\n"
    if whatsapp:
        prompt += f"- WhatsApp: {whatsapp}\n"
    if instagram:
        prompt += f"- Instagram: {instagram}\n"
    if facebook:
        prompt += f"- Facebook: {facebook}\n"
    if website:
        prompt += f"- Site: {website}\n"
    if email:
        prompt += f"- Email: {email}\n"

    prompt += _build_business_hours_context(tenant.get("business_hours"))

    faq_context = _build_faq_context(tenant_id, db)
    if faq_context:
        prompt += f"\n{faq_context}\n"

    if system_prompt:
        prompt += f"\nINFORMAÇÕES ADICIONAIS:\n{system_prompt}\n"

    return prompt
