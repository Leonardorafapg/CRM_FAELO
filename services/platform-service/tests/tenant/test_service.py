"""Unit tests de app/tenant/service.py."""
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth import service as auth_service
from app.auth.schemas import RegisterRequest
from app.tenant import service
from app.tenant.schemas import TenantUpdateBody
from app.identity.models import User


def _register(db: Session, email: str) -> User:
    return auth_service.register_user(
        RegisterRequest(name="Nome", email=email, password="senha12345", business_name="Empresa"), db
    )


def test_get_or_404_com_tenant_inexistente_levanta_404(db: Session):
    with pytest.raises(HTTPException) as exc:
        service.get_or_404("nao-existe", db)
    assert exc.value.status_code == 404


def test_serialize_tenant_nunca_expoe_groq_key_em_texto(db: Session):
    user = _register(db, "tenantserialize@teste.com")
    tenant = service.get_or_404(user.tenant_id, db)
    tenant.groq_key = "chave-secreta-de-verdade"
    db.commit()

    data = service.serialize_tenant(tenant)
    assert data["groq_key"] is True  # so booleano, nunca o valor
    assert "chave-secreta-de-verdade" not in str(data)


def test_update_tenant_atualiza_campo_simples(db: Session):
    user = _register(db, "tenantupdate@teste.com")
    service.update_tenant(user.tenant_id, TenantUpdateBody(business_name="Novo Nome"), db)
    tenant = service.get_or_404(user.tenant_id, db)
    assert tenant.business_name == "Novo Nome"


def test_update_tenant_nao_sobrescreve_groq_key_com_booleano(db: Session):
    """Protecao critica (SECURITY.md): o front pode reenviar o booleano do
    GET por engano — nao pode apagar a chave real salva."""
    user = _register(db, "tenantgroqkey@teste.com")
    tenant = service.get_or_404(user.tenant_id, db)
    tenant.groq_key = "chave-original"
    db.commit()

    service.update_tenant(user.tenant_id, TenantUpdateBody(groq_key=True), db)

    db.refresh(tenant)
    assert tenant.groq_key == "chave-original"


def test_update_tenant_aplica_groq_key_quando_string_nao_vazia(db: Session):
    user = _register(db, "tenantgroqkey2@teste.com")
    service.update_tenant(user.tenant_id, TenantUpdateBody(groq_key="nova-chave"), db)
    tenant = service.get_or_404(user.tenant_id, db)
    assert tenant.groq_key == "nova-chave"


def test_deactivate_tenant_marca_is_active_false(db: Session):
    user = _register(db, "tenantdeactivate@teste.com")
    service.deactivate_tenant(user.tenant_id, admin_user_id="algum-admin-id", db=db)
    tenant = service.get_or_404(user.tenant_id, db)
    assert tenant.is_active is False


def test_update_business_hours_cria_e_depois_atualiza(db: Session):
    user = _register(db, "tenanthours@teste.com")
    service.update_business_hours(
        user.tenant_id,
        [{"day_of_week": 0, "is_closed": False, "slots": [{"from": "09:00", "to": "18:00"}]}],
        db,
    )
    hours = service.get_business_hours(user.tenant_id, db)
    assert len(hours) == 1
    assert hours[0]["is_closed"] is False

    # Upsert: mesmo dia, agora fechado.
    service.update_business_hours(user.tenant_id, [{"day_of_week": 0, "is_closed": True, "slots": []}], db)
    hours = service.get_business_hours(user.tenant_id, db)
    assert len(hours) == 1  # nao duplicou o dia
    assert hours[0]["is_closed"] is True


def test_update_business_hours_vazio_levanta_400(db: Session):
    user = _register(db, "tenanthoursvazio@teste.com")
    with pytest.raises(HTTPException) as exc:
        service.update_business_hours(user.tenant_id, [], db)
    assert exc.value.status_code == 400


def test_update_business_hours_sem_day_of_week_levanta_400(db: Session):
    user = _register(db, "tenanthourssemdia@teste.com")
    with pytest.raises(HTTPException) as exc:
        service.update_business_hours(user.tenant_id, [{"is_closed": True}], db)
    assert exc.value.status_code == 400
