from typing import Optional
from pydantic import BaseModel


class ContactStatusCreate(BaseModel):
    name: str


class ContactStatusUpdate(BaseModel):
    name:   Optional[str] = None
    active: Optional[bool] = None
    order:  Optional[int] = None


class ContactCreate(BaseModel):
    name:        str
    phone:       str
    email:       Optional[str] = None
    source:      Optional[str] = None
    tags:        list[str] = []
    status_id:   Optional[str] = None
    assigned_to: Optional[str] = None
    stage_id:    Optional[str] = None


class ContactUpdate(BaseModel):
    """PATCH parcial — inclui status_id/stage_id porque mover um contact de
    coluna no Kanban ou mudar sua situacao e so uma atualizacao de campo,
    sem endpoint dedicado (ver docs/PERFORMANCE.md — nao criar endpoint
    extra pra algo que um PATCH generico ja cobre)."""
    name:        Optional[str] = None
    phone:       Optional[str] = None
    email:       Optional[str] = None
    source:      Optional[str] = None
    tags:        Optional[list[str]] = None
    status_id:   Optional[str] = None
    assigned_to: Optional[str] = None
    stage_id:    Optional[str] = None
