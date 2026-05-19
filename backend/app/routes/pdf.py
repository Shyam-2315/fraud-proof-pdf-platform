from fastapi import APIRouter, HTTPException, Request

from app.schemas.pdf import PDFGenerateRequest, PDFGenerateResponse, PDFHistoryResponse
from app.services.pdf_service import PDFService

router = APIRouter(prefix="/api/pdf", tags=["PDF"])
pdf_service = PDFService()


@router.post("/generate", response_model=PDFGenerateResponse)
async def generate_pdf(
    payload: PDFGenerateRequest,
    request: Request,
) -> PDFGenerateResponse:
    try:
        return await pdf_service.generate_pdf_for_anonymous_visitor(
            request=request,
            payload=payload,
        )
    except HTTPException:
        raise


@router.get("/history", response_model=PDFHistoryResponse)
async def pdf_history(request: Request) -> PDFHistoryResponse:
    try:
        return await pdf_service.get_pdf_history_for_visitor(request=request)
    except HTTPException:
        raise
