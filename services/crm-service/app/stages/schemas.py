from typing import Optional
from pydantic import BaseModel


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
