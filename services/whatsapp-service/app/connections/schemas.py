from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ConnectionOut(BaseModel):
    id: str
    instance_name: str
    phone: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConnectionCreateResponse(BaseModel):
    connection: ConnectionOut
    qrcode_base64: Optional[str] = None
