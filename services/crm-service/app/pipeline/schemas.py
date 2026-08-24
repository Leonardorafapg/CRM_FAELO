from typing import Optional
from pydantic import BaseModel


class PipelineCreate(BaseModel):
    name:        str
    description: Optional[str] = None
    is_default:  bool = False


class PipelineUpdate(BaseModel):
    """PATCH parcial — so atualiza o que vier preenchido."""
    name:        Optional[str] = None
    description: Optional[str] = None
    active:      Optional[bool] = None
    is_default:  Optional[bool] = None


class StageCreate(BaseModel):
    name:     str
    color:    Optional[str] = None
    is_entry: bool = False


class StageUpdate(BaseModel):
    name:     Optional[str] = None
    order:    Optional[int] = None
    color:    Optional[str] = None
    active:   Optional[bool] = None
    is_entry: Optional[bool] = None
