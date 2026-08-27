"""Unit tests de app/faq/service.py."""
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.faq import service
from app.faq.schemas import FaqItemCreate, FaqItemUpdate


def _tenant() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


def test_create_faq_com_pergunta_vazia_levanta_400(db: Session):
    tenant = _tenant()
    with pytest.raises(HTTPException) as exc:
        service.create_faq(tenant, FaqItemCreate(pergunta="   ", resposta="Resposta"), db)
    assert exc.value.status_code == 400


def test_create_faq_com_resposta_vazia_levanta_400(db: Session):
    tenant = _tenant()
    with pytest.raises(HTTPException) as exc:
        service.create_faq(tenant, FaqItemCreate(pergunta="Pergunta", resposta="  "), db)
    assert exc.value.status_code == 400


def test_create_faq_ok(db: Session):
    tenant = _tenant()
    item = service.create_faq(tenant, FaqItemCreate(pergunta=" Qual o horário? ", resposta=" 9h-18h "), db)
    assert item.pergunta == "Qual o horário?"  # strip aplicado
    assert item.resposta == "9h-18h"


def test_list_faq_escopado_por_tenant(db: Session):
    tenant_a, tenant_b = _tenant(), _tenant()
    service.create_faq(tenant_a, FaqItemCreate(pergunta="Q1", resposta="A1"), db)
    service.create_faq(tenant_b, FaqItemCreate(pergunta="Q2", resposta="A2"), db)

    result = service.list_faq(tenant_a, db)
    assert result["total"] == 1
    assert result["items"][0].pergunta == "Q1"


def test_list_faq_pagina_e_busca(db: Session):
    tenant = _tenant()
    service.create_faq(tenant, FaqItemCreate(pergunta="Qual o horário de funcionamento", resposta="9h-18h"), db)
    service.create_faq(tenant, FaqItemCreate(pergunta="Vocês fazem entrega", resposta="Sim"), db)

    result = service.list_faq(tenant, db, q="horário")
    assert result["total"] == 1
    assert "horário" in result["items"][0].pergunta.lower()

    result = service.list_faq(tenant, db, page=1, limit=1)
    assert len(result["items"]) == 1
    assert result["pages"] == 2


def test_get_faq_or_404_de_outro_tenant_levanta_404(db: Session):
    tenant_a, tenant_b = _tenant(), _tenant()
    item = service.create_faq(tenant_a, FaqItemCreate(pergunta="Q1", resposta="A1"), db)
    with pytest.raises(HTTPException) as exc:
        service.get_faq_or_404(item.id, tenant_b, db)
    assert exc.value.status_code == 404


def test_update_faq_muda_campos(db: Session):
    tenant = _tenant()
    item = service.create_faq(tenant, FaqItemCreate(pergunta="Q1", resposta="A1"), db)
    updated = service.update_faq(item.id, tenant, FaqItemUpdate(pergunta="Q1 editada", resposta="A1 editada"), db)
    assert updated.pergunta == "Q1 editada"
    assert updated.resposta == "A1 editada"


def test_delete_faq(db: Session):
    tenant = _tenant()
    item = service.create_faq(tenant, FaqItemCreate(pergunta="Q1", resposta="A1"), db)
    service.delete_faq(item.id, tenant, db)
    with pytest.raises(HTTPException):
        service.get_faq_or_404(item.id, tenant, db)
