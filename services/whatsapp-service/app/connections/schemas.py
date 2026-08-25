from typing import Optional
from pydantic import BaseModel


class ConnectionOut(BaseModel):
    id: str
    instance_name: str
    phone: Optional[str] = None
    status: str

    class Config:
        from_attributes = True


class ConnectionCreateResponse(BaseModel):
    connection: ConnectionOut
    qrcode_base64: Optional[str] = None
