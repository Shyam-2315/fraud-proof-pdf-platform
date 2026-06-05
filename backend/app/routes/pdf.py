import logging
from pathlib import Path
from time import perf_counter
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.config import get_settings
from app.core.auth import get_current_user_optional
from app.schemas.pdf import (
    MyPDFHistoryResponse,
    PDFGenerateRequest,
    PDFGenerateResponse,
)
from app.services.pdf_service import PDFService
from app.services.rate_limit_service import RateLimitService, client_ip
from app.utils.pdf_tools import (
    IMAGE_MIME_TYPES,
    PDF_MIME_TYPES,
    compress_pdf_bytes,
    image_bytes_to_pdf,
    merge_pdf_bytes,
    protect_pdf_bytes,
    split_pdf_bytes,
    validate_image_bytes,
    validate_pdf_bytes,
)
from app.utils.sanitization import sanitize_log_value

router = APIRouter(prefix="/pdf", tags=["PDF"])
pdf_service = PDFService()
rate_limit_service = RateLimitService()
logger = logging.getLogger(__name__)
SLOW_ENDPOINT_MS = 500


@router.post(
    "/generate",
    response_model=PDFGenerateResponse,
    response_model_exclude_none=True,
)
async def generate_pdf(
    payload: PDFGenerateRequest,
    request: Request,
) -> PDFGenerateResponse:
    """
    Generate a PDF while enforcing anonymous and authenticated limits.

    Args:
        payload: Validated PDF generation input from the client.
        request: Incoming HTTP request used for identity and rate limiting.

    Returns:
        Generated PDF metadata and download access details.

    Raises:
        HTTPException: If access is blocked or the PDF cannot be generated.
    """
    started_at = perf_counter()
    current_user: dict[str, Any] | None = await _current_user_with_generation_rate_limit(request)
    is_authenticated = current_user is not None
    try:
        return await pdf_service.generate_pdf(
            request=request,
            payload=payload,
            current_user=current_user,
        )
    except HTTPException as exc:
        if isinstance(exc.detail, dict) and (
            exc.detail.get("success") is False
            or exc.detail.get("requires_login") is True
            or exc.detail.get("requires_upgrade") is True
        ):
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        raise
    finally:
        duration_ms = (perf_counter() - started_at) * 1000
        if duration_ms >= SLOW_ENDPOINT_MS:
            logger.info(
                "Slow endpoint path=%s duration_ms=%.2f authenticated=%s",
                request.url.path,
                duration_ms,
                is_authenticated,
            )


@router.post(
    "/tools/text-to-pdf",
    response_model=PDFGenerateResponse,
    response_model_exclude_none=True,
)
async def text_to_pdf(
    payload: PDFGenerateRequest,
    request: Request,
) -> PDFGenerateResponse:
    return await _run_pdf_tool(
        request=request,
        payload=payload,
        tool="TEXT_TO_PDF",
    )


@router.post(
    "/tools/image-to-pdf",
    response_model=PDFGenerateResponse,
    response_model_exclude_none=True,
)
async def image_to_pdf(
    request: Request,
    title: str = Form("Image PDF"),
    files: list[UploadFile] = File(...),
) -> PDFGenerateResponse:
    uploaded_images = await _read_uploads(
        files=files,
        allowed_mime_types=IMAGE_MIME_TYPES,
        allowed_extensions={".jpg", ".jpeg", ".png", ".webp"},
        min_files=1,
    )
    for uploaded_image in uploaded_images:
        try:
            validate_image_bytes(uploaded_image["content"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload = _build_tool_payload(
        title=title,
        content=_uploaded_content_summary("Image to PDF", uploaded_images),
    )
    return await _run_pdf_tool(
        request=request,
        payload=payload,
        tool="IMAGE_TO_PDF",
        file_builder=lambda: image_bytes_to_pdf(
            [item["content"] for item in uploaded_images],
            output_dir=pdf_service.settings.PDF_STORAGE_DIR,
        ),
    )


@router.post(
    "/tools/merge",
    response_model=PDFGenerateResponse,
    response_model_exclude_none=True,
)
async def merge_pdfs(
    request: Request,
    title: str = Form("Merged PDF"),
    files: list[UploadFile] = File(...),
) -> PDFGenerateResponse:
    uploaded_pdfs = await _read_pdf_uploads(files=files, min_files=2)
    payload = _build_tool_payload(
        title=title,
        content=_uploaded_content_summary("Merge PDFs", uploaded_pdfs),
    )
    return await _run_pdf_tool(
        request=request,
        payload=payload,
        tool="MERGE_PDFS",
        file_builder=lambda: merge_pdf_bytes(
            [item["content"] for item in uploaded_pdfs],
            output_dir=pdf_service.settings.PDF_STORAGE_DIR,
        ),
    )


@router.post(
    "/tools/split",
    response_model=PDFGenerateResponse,
    response_model_exclude_none=True,
)
async def split_pdf(
    request: Request,
    title: str = Form("Split PDF"),
    page_ranges: str | None = Form(None),
    file: UploadFile = File(...),
) -> PDFGenerateResponse:
    uploaded_pdf = (await _read_pdf_uploads(files=[file], min_files=1, max_files=1))[0]
    payload = _build_tool_payload(
        title=title,
        content=f"Split PDF: {uploaded_pdf['file_name']} pages={page_ranges or '1'}",
    )
    return await _run_pdf_tool(
        request=request,
        payload=payload,
        tool="SPLIT_PDF",
        file_builder=lambda: split_pdf_bytes(
            uploaded_pdf["content"],
            output_dir=pdf_service.settings.PDF_STORAGE_DIR,
            page_ranges=page_ranges,
        ),
    )


@router.post(
    "/tools/compress",
    response_model=PDFGenerateResponse,
    response_model_exclude_none=True,
)
async def compress_pdf(
    request: Request,
    title: str = Form("Compressed PDF"),
    file: UploadFile = File(...),
) -> PDFGenerateResponse:
    uploaded_pdf = (await _read_pdf_uploads(files=[file], min_files=1, max_files=1))[0]
    payload = _build_tool_payload(
        title=title,
        content=f"Compress PDF: {uploaded_pdf['file_name']}",
    )
    return await _run_pdf_tool(
        request=request,
        payload=payload,
        tool="COMPRESS_PDF",
        file_builder=lambda: compress_pdf_bytes(
            uploaded_pdf["content"],
            output_dir=pdf_service.settings.PDF_STORAGE_DIR,
        ),
    )


@router.post(
    "/tools/password-protect",
    response_model=PDFGenerateResponse,
    response_model_exclude_none=True,
)
async def password_protect_pdf(
    request: Request,
    password: str = Form(..., min_length=6, max_length=128),
    title: str = Form("Protected PDF"),
    file: UploadFile = File(...),
) -> PDFGenerateResponse:
    uploaded_pdf = (await _read_pdf_uploads(files=[file], min_files=1, max_files=1))[0]
    payload = _build_tool_payload(
        title=title,
        content=f"Password protect PDF: {uploaded_pdf['file_name']}",
    )
    return await _run_pdf_tool(
        request=request,
        payload=payload,
        tool="PASSWORD_PROTECT_PDF",
        file_builder=lambda: protect_pdf_bytes(
            uploaded_pdf["content"],
            password=password,
            output_dir=pdf_service.settings.PDF_STORAGE_DIR,
        ),
    )


@router.get("/history", response_model=MyPDFHistoryResponse)
async def pdf_history(request: Request) -> MyPDFHistoryResponse:
    """
    Return PDF history for the current caller.

    Args:
        request: Incoming HTTP request used to resolve the current user.

    Returns:
        Generated PDF history visible to the current caller.
    """
    try:
        return await pdf_service.get_my_pdf_history(request=request)
    except HTTPException:
        raise


@router.get("/my-history", response_model=MyPDFHistoryResponse)
async def my_pdf_history(request: Request) -> MyPDFHistoryResponse:
    """
    Return PDF history using the legacy alias path.

    Args:
        request: Incoming HTTP request used to resolve the current user.

    Returns:
        Generated PDF history visible to the current caller.
    """
    try:
        return await pdf_service.get_my_pdf_history(request=request)
    except HTTPException:
        raise


@router.get("/download/{pdf_id}", tags=["PDF"])
async def download_pdf(pdf_id: str, request: Request) -> FileResponse:
    """
    Download a previously generated PDF after access checks pass.

    Args:
        pdf_id: Identifier of the generated PDF record to download.
        request: Incoming HTTP request used to authorize the download.

    Returns:
        File response streaming the requested PDF document.

    Raises:
        HTTPException: If the PDF does not exist or resolves outside storage.
    """
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


async def _run_pdf_tool(
    request: Request,
    payload: PDFGenerateRequest,
    tool: str,
    file_builder: Any | None = None,
) -> PDFGenerateResponse:
    current_user = await _current_user_with_generation_rate_limit(request)
    try:
        return await pdf_service.generate_pdf(
            request=request,
            payload=payload,
            current_user=current_user,
            file_builder=file_builder,
            tool=tool,
        )
    except HTTPException as exc:
        if isinstance(exc.detail, dict) and (
            exc.detail.get("success") is False
            or exc.detail.get("requires_login") is True
            or exc.detail.get("requires_upgrade") is True
        ):
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _current_user_with_generation_rate_limit(
    request: Request,
) -> dict[str, Any] | None:
    current_user: dict[str, Any] | None = await get_current_user_optional(request)
    if current_user is not None:
        return current_user
    identifier = (
        request.headers.get("X-Visitor-Id")
        or request.headers.get("X-Device-Fingerprint")
        or client_ip(request)
    )
    await rate_limit_service.check(
        request,
        bucket="pdf_generate",
        identifier=identifier,
        rate=pdf_service.settings.PDF_GENERATE_RATE_LIMIT,
    )
    return None


async def _read_pdf_uploads(
    files: list[UploadFile],
    min_files: int,
    max_files: int | None = None,
) -> list[dict[str, Any]]:
    uploaded_pdfs = await _read_uploads(
        files=files,
        allowed_mime_types=PDF_MIME_TYPES,
        allowed_extensions={".pdf"},
        min_files=min_files,
        max_files=max_files,
    )
    for uploaded_pdf in uploaded_pdfs:
        try:
            validate_pdf_bytes(uploaded_pdf["content"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return uploaded_pdfs


async def _read_uploads(
    files: list[UploadFile],
    allowed_mime_types: set[str],
    allowed_extensions: set[str],
    min_files: int,
    max_files: int | None = None,
) -> list[dict[str, Any]]:
    max_file_count = max_files or pdf_service.settings.PDF_TOOL_MAX_FILES
    if len(files) < min_files:
        raise HTTPException(status_code=400, detail=f"Upload at least {min_files} file(s).")
    if len(files) > max_file_count:
        raise HTTPException(status_code=400, detail=f"Upload no more than {max_file_count} file(s).")

    uploaded: list[dict[str, Any]] = []
    for file in files:
        file_name = sanitize_log_value(file.filename or "")
        suffix = Path(file_name).suffix.lower()
        content_type = (file.content_type or "").lower()
        if suffix not in allowed_extensions and content_type not in allowed_mime_types:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_name or 'upload'}.")

        content = await file.read(pdf_service.settings.PDF_TOOL_MAX_UPLOAD_BYTES + 1)
        if len(content) > pdf_service.settings.PDF_TOOL_MAX_UPLOAD_BYTES:
            limit_mb = pdf_service.settings.PDF_TOOL_MAX_UPLOAD_BYTES // (1024 * 1024)
            raise HTTPException(status_code=400, detail=f"File is too large. Maximum size is {limit_mb} MB.")
        if not content:
            raise HTTPException(status_code=400, detail=f"Uploaded file is empty: {file_name or 'upload'}.")
        uploaded.append(
            {
                "file_name": file_name or "upload",
                "content_type": content_type,
                "content": content,
            }
        )
    return uploaded


def _build_tool_payload(title: str, content: str) -> PDFGenerateRequest:
    try:
        return PDFGenerateRequest(title=title, content=content)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Tool title or input contains invalid text.") from exc


def _uploaded_content_summary(tool_label: str, files: list[dict[str, Any]]) -> str:
    names = ", ".join(item["file_name"] for item in files)
    return f"{tool_label}: {len(files)} file(s): {names}"
