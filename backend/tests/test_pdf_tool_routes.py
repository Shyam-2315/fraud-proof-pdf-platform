import json
from io import BytesIO
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.routes import pdf as pdf_routes
from app.schemas.pdf import MyPDFHistoryItem, MyPDFHistoryResponse, PDFGenerateRequest, PDFGenerateResponse
from app.utils.pdf_generator import generate_simple_pdf


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class FakePDFService:
    def __init__(self, storage_dir: str) -> None:
        self.settings = SimpleNamespace(
            PDF_STORAGE_DIR=storage_dir,
            PDF_GENERATE_RATE_LIMIT="5/minute",
            PDF_TOOL_MAX_UPLOAD_BYTES=1024 * 1024,
            PDF_TOOL_MAX_FILES=20,
        )
        self.records: list[dict[str, Any]] = []
        self.raise_block = False
        self.builder_called = False

    async def generate_pdf(
        self,
        request,
        payload,
        current_user=None,
        file_builder=None,
        tool: str = "TEXT_TO_PDF",
    ) -> PDFGenerateResponse:
        if self.raise_block:
            raise HTTPException(
                status_code=403,
                detail={
                    "success": False,
                    "message": "Free limit reached. Please log in to continue.",
                    "requires_login": True,
                    "used": 2,
                    "remaining": 0,
                    "free_limit": 2,
                },
            )

        if file_builder is None:
            file_name, file_path = generate_simple_pdf(
                title=payload.title,
                content=payload.content,
                output_dir=self.settings.PDF_STORAGE_DIR,
            )
        else:
            self.builder_called = True
            file_name, file_path = file_builder()

        pdf_id = f"pdf-{len(self.records) + 1}"
        self.records.append(
            {
                "pdf_id": pdf_id,
                "title": payload.title,
                "file_name": file_name,
                "file_path": file_path,
                "tool": tool,
            }
        )
        return PDFGenerateResponse(
            success=True,
            message="PDF generated successfully.",
            pdf_id=pdf_id,
            title=payload.title,
            file_name=file_name,
            download_url=f"/api/pdf/download/{pdf_id}",
            tool=tool,
            used=len(self.records),
            remaining=10 - len(self.records),
        )

    async def get_my_pdf_history(self, request) -> MyPDFHistoryResponse:
        return MyPDFHistoryResponse(
            total=len(self.records),
            items=[
                MyPDFHistoryItem(
                    pdf_id=record["pdf_id"],
                    title=record["title"],
                    file_name=record["file_name"],
                    tool=record["tool"],
                    created_at="2026-06-05T00:00:00Z",
                    download_url=f"/api/pdf/download/{record['pdf_id']}",
                )
                for record in self.records
            ],
        )


@pytest.mark.anyio
async def test_all_pdf_tool_routes_generate_files_and_record_history(monkeypatch, tmp_path) -> None:
    fake_service = FakePDFService(str(tmp_path))
    monkeypatch.setattr(pdf_routes, "pdf_service", fake_service)
    monkeypatch.setattr(
        pdf_routes,
        "_current_user_with_generation_rate_limit",
        _fake_current_user,
    )
    request = _request()

    calls = [
        (
            "TEXT_TO_PDF",
            lambda: pdf_routes.text_to_pdf(
                PDFGenerateRequest(title="Text PDF", content="Hello PDF"),
                request,
            ),
        ),
        (
            "IMAGE_TO_PDF",
            lambda: pdf_routes.image_to_pdf(
                request=request,
                title="Image PDF",
                files=[_upload("image.png", _sample_png(), "image/png")],
            ),
        ),
        (
            "MERGE_PDFS",
            lambda: pdf_routes.merge_pdfs(
                request=request,
                title="Merged PDF",
                files=[
                    _upload("one.pdf", _sample_pdf("one"), "application/pdf"),
                    _upload("two.pdf", _sample_pdf("two"), "application/pdf"),
                ],
            ),
        ),
        (
            "SPLIT_PDF",
            lambda: pdf_routes.split_pdf(
                request=request,
                title="Split PDF",
                page_ranges="1",
                file=_upload("split.pdf", _sample_pdf("split"), "application/pdf"),
            ),
        ),
        (
            "COMPRESS_PDF",
            lambda: pdf_routes.compress_pdf(
                request=request,
                title="Compressed PDF",
                file=_upload("compress.pdf", _sample_pdf("compress"), "application/pdf"),
            ),
        ),
        (
            "PASSWORD_PROTECT_PDF",
            lambda: pdf_routes.password_protect_pdf(
                request=request,
                title="Protected PDF",
                password="secret123",
                file=_upload("protect.pdf", _sample_pdf("protect"), "application/pdf"),
            ),
        ),
    ]

    for expected_tool, call in calls:
        response = await call()
        assert response.tool == expected_tool
        assert response.pdf_id
        assert response.file_name
        assert (tmp_path / response.file_name).exists()

    history = await pdf_routes.my_pdf_history(request)
    assert history.total == len(calls)
    assert {item.tool for item in history.items} == {case[0] for case in calls}


@pytest.mark.anyio
async def test_fraud_or_usage_block_prevents_tool_file_generation(monkeypatch, tmp_path) -> None:
    fake_service = FakePDFService(str(tmp_path))
    fake_service.raise_block = True
    monkeypatch.setattr(pdf_routes, "pdf_service", fake_service)
    monkeypatch.setattr(
        pdf_routes,
        "_current_user_with_generation_rate_limit",
        _fake_current_user,
    )

    response = await pdf_routes.merge_pdfs(
        request=_request(),
        title="Blocked merge",
        files=[
            _upload("one.pdf", _sample_pdf("one"), "application/pdf"),
            _upload("two.pdf", _sample_pdf("two"), "application/pdf"),
        ],
    )

    assert response.status_code == 403
    assert json.loads(response.body)["requires_login"] is True
    assert fake_service.builder_called is False
    assert list(tmp_path.iterdir()) == []


@pytest.mark.anyio
async def test_invalid_file_uploads_are_rejected_before_generation(monkeypatch, tmp_path) -> None:
    fake_service = FakePDFService(str(tmp_path))
    monkeypatch.setattr(pdf_routes, "pdf_service", fake_service)
    monkeypatch.setattr(
        pdf_routes,
        "_current_user_with_generation_rate_limit",
        _fake_current_user,
    )

    with pytest.raises(HTTPException) as unsupported:
        await pdf_routes.merge_pdfs(
            request=_request(),
            title="Invalid merge",
            files=[
                _upload("one.txt", b"not a pdf", "text/plain"),
                _upload("two.pdf", _sample_pdf("two"), "application/pdf"),
            ],
        )
    assert unsupported.value.status_code == 400

    with pytest.raises(HTTPException) as invalid_pdf:
        await pdf_routes.compress_pdf(
            request=_request(),
            title="Invalid compress",
            file=_upload("bad.pdf", b"not a pdf", "application/pdf"),
        )
    assert invalid_pdf.value.status_code == 400
    assert fake_service.records == []


async def _fake_current_user(request):
    return {"_id": "user-1"}


def _request():
    return SimpleNamespace(headers={}, cookies={}, state=SimpleNamespace(), url=SimpleNamespace(path="/pdf/tools"))


class FakeUploadFile:
    def __init__(self, file_name: str, content: bytes, content_type: str) -> None:
        self.filename = file_name
        self.content_type = content_type
        self._content = content

    async def read(self, size: int = -1) -> bytes:
        return self._content if size < 0 else self._content[:size]


def _upload(file_name: str, content: bytes, content_type: str) -> FakeUploadFile:
    return FakeUploadFile(file_name, content, content_type)


def _sample_pdf(text: str) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.drawString(72, 720, text)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _sample_png() -> bytes:
    buffer = BytesIO()
    image = Image.new("RGB", (120, 80), color="white")
    image.save(buffer, format="PNG")
    return buffer.getvalue()
