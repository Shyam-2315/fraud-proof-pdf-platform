from datetime import datetime

from pydantic import BaseModel, Field


class PDFGenerateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=5000)


class PDFGenerateResponse(BaseModel):
    success: bool
    message: str
    pdf_id: str | None = None
    file_name: str | None = None
    file_path: str | None = None
    free_usage_count: int
    free_usage_limit: int
    remaining_free_uses: int


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
