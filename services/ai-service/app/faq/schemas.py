from pydantic import BaseModel


class FaqItemOut(BaseModel):
    id: str
    pergunta: str
    resposta: str

    class Config:
        from_attributes = True


class FaqItemCreate(BaseModel):
    pergunta: str
    resposta: str


class FaqItemUpdate(BaseModel):
    pergunta: str
    resposta: str


class FaqItemList(BaseModel):
    """Mesmo formato paginado do legado (routers/faq.py::listar_faq)."""
    items: list[FaqItemOut]
    total: int
    page: int
    limit: int
    pages: int
