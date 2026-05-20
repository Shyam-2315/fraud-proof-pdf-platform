from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.schemas.pdf import (
    MyPDFHistoryResponse,
    PDFGenerateRequest,
    PDFGenerateResponse,
)
from app.services.pdf_service import PDFService
from app.services.rate_limit_service import RateLimitService, client_ip

router = APIRouter(prefix="/api/pdf", tags=["PDF"])
pdf_service = PDFService()
rate_limit_service = RateLimitService()


@router.post(
    "/generate",
    response_model=PDFGenerateResponse,
    response_model_exclude_none=True,
)
async def generate_pdf(
    payload: PDFGenerateRequest,
    request: Request,
) -> PDFGenerateResponse:
    identifier = (
        request.headers.get("authorization")
        or request.headers.get("X-Visitor-Id")
        or request.headers.get("X-Device-Fingerprint")
        or client_ip(request)
    )
    await rate_limit_service.check(
        request,
        bucket="pdf_generate",
        identifier=identifier,
        limit=20,
        window_seconds=3600,
    )
    try:
        return await pdf_service.generate_pdf(
            request=request,
            payload=payload,
        )
    except HTTPException as exc:
        if isinstance(exc.detail, dict) and (
            exc.detail.get("requires_login") is True
            or exc.detail.get("requires_upgrade") is True
        ):
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        raise


@router.get("/history", response_model=MyPDFHistoryResponse)
async def pdf_history(request: Request) -> MyPDFHistoryResponse:
    try:
        return await pdf_service.get_my_pdf_history(request=request)
    except HTTPException:
        raise


@router.get("/my-history", response_model=MyPDFHistoryResponse)
async def my_pdf_history(request: Request) -> MyPDFHistoryResponse:
    try:
        return await pdf_service.get_my_pdf_history(request=request)
    except HTTPException:
        raise


@router.get("/download/{pdf_id}", tags=["PDF"])
async def download_pdf(pdf_id: str, request: Request) -> FileResponse:
    pdf_record = await pdf_service.get_downloadable_pdf(request=request, pdf_id=pdf_id)
    storage_root = Path(get_settings().PDF_STORAGE_DIR).resolve()
    file_path = Path(str(pdf_record.get("file_path", ""))).resolve()
    if storage_root not in file_path.parents and file_path != storage_root:
        raise HTTPException(status_code=404, detail="PDF not found.")
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="PDF file not found.")
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=str(pdf_record.get("file_name") or f"{pdf_id}.pdf"),
    )
