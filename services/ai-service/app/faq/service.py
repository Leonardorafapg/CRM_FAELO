"""Regras de negocio de FaqItem — acesso a banco e decisoes de dominio, sem
nada de HTTP. Todo acesso e sempre escopado por tenant_id (vem do JWT do
usuario logado, nunca de path/query) — nao existe leitura cross-tenant
aqui. Mesmo comportamento do legado (Chatbot/chat-api/routers/faq.py):
pergunta/resposta obrigatorios e sem espaco em branco, busca por texto,
paginacao."""
import math
import uuid

from fastapi import HTTPException
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.faq.models import FaqItem
from app.faq.schemas import FaqItemCreate, FaqItemUpdate


def _new_id() -> str:
    return str(uuid.uuid4())


def list_faq(tenant_id: str, db: Session, page: int = 1, limit: int = 10, q: str = "") -> dict:
    query = db.query(FaqItem).filter(FaqItem.tenant_id == tenant_id)

    search = q.strip().lower()
    if search:
        query = query.filter(
            or_(
                func.lower(FaqItem.pergunta).contains(search),
                func.lower(FaqItem.resposta).contains(search),
            )
        )

    total = query.count()
    items = query.order_by(FaqItem.created_at).offset((page - 1) * limit).limit(limit).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": math.ceil(total / limit) if total > 0 else 1,
    }


def get_faq_or_404(faq_id: str, tenant_id: str, db: Session) -> FaqItem:
    item = db.query(FaqItem).filter(FaqItem.id == faq_id, FaqItem.tenant_id == tenant_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    return item


def create_faq(tenant_id: str, body: FaqItemCreate, db: Session) -> FaqItem:
    if not body.pergunta.strip() or not body.resposta.strip():
        raise HTTPException(status_code=400, detail="Pergunta e resposta são obrigatórias")
    item = FaqItem(
        id=_new_id(),
        tenant_id=tenant_id,
        pergunta=body.pergunta.strip(),
        resposta=body.resposta.strip(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_faq(faq_id: str, tenant_id: str, body: FaqItemUpdate, db: Session) -> FaqItem:
    if not body.pergunta.strip() or not body.resposta.strip():
        raise HTTPException(status_code=400, detail="Pergunta e resposta são obrigatórias")
    item = get_faq_or_404(faq_id, tenant_id, db)
    item.pergunta = body.pergunta.strip()
    item.resposta = body.resposta.strip()
    db.commit()
    db.refresh(item)
    return item


def delete_faq(faq_id: str, tenant_id: str, db: Session) -> None:
    item = get_faq_or_404(faq_id, tenant_id, db)
    db.delete(item)
    db.commit()
