from datetime import datetime

from pydantic import BaseModel, Field


class PDFGenerateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=20000)


class PDFGenerateResponse(BaseModel):
    success: bool
    message: str
    pdf_id: str | None = None
    title: str | None = None
    file_name: str | None = None
    free_limit: int | None = None
    plan: str | None = None
    limit: int | None = None
    used: int
    remaining: int
    requires_login: bool = False
    requires_upgrade: bool = False


class PDFHistoryItem(BaseModel):
    pdf_id: str
    title: str
    file_name: str
    generation_type: str
    created_at: datetime


class PDFHistoryResponse(BaseModel):
    visitor_id: str
    total: int
    items: list[PDFHistoryItem]


class MyPDFHistoryItem(BaseModel):
    pdf_id: str
    title: str
    file_name: str
    created_at: datetime
    download_url: str


class MyPDFHistoryResponse(BaseModel):
    total: int
    items: list[MyPDFHistoryItem]
