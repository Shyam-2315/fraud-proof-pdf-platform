from datetime import datetime

from pydantic import BaseModel, Field


class PDFGenerateRequest(BaseModel):
    """
    Schema describing the pdf generate request payload.
    """
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=20000)


class PDFGenerateResponse(BaseModel):
    """
    Schema describing the pdf generate response payload.
    """
    success: bool
    message: str
    pdf_id: str | None = None
    title: str | None = None
    file_name: str | None = None
    free_limit: int | None = None
    free_usage_count: int | None = None
    free_usage_limit: int | None = None
    remaining_free_uses: int | None = None
    plan: str | None = None
    limit: int | None = None
    used: int
    remaining: int
    requires_login: bool = False
    requires_upgrade: bool = False


class PDFHistoryItem(BaseModel):
    """
    Schema describing the pdf history item payload.
    """
    pdf_id: str
    title: str
    file_name: str
    generation_type: str
    created_at: datetime


class PDFHistoryResponse(BaseModel):
    """
    Schema describing the pdf history response payload.
    """
    visitor_id: str
    total: int
    items: list[PDFHistoryItem]


class MyPDFHistoryItem(BaseModel):
    """
    Schema describing the my pdf history item payload.
    """
    pdf_id: str
    title: str
    file_name: str
    created_at: datetime
    download_url: str


class MyPDFHistoryResponse(BaseModel):
    """
    Schema describing the my pdf history response payload.
    """
    total: int
    items: list[MyPDFHistoryItem]
