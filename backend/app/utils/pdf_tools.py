from io import BytesIO
from pathlib import Path
from typing import Iterable

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.utils.pdf_generator import _ensure_output_dir
from app.utils.security import generate_uuid


PDF_MIME_TYPES = {"application/pdf", "application/x-pdf"}
IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


def make_tool_file_name(prefix: str) -> str:
    return f"{prefix}_{generate_uuid()}.pdf"


def image_bytes_to_pdf(
    images: list[bytes],
    output_dir: str,
    prefix: str = "image_to_pdf",
) -> tuple[str, str]:
    if not images:
        raise ValueError("At least one image is required.")

    try:
        file_name = make_tool_file_name(prefix)
        file_path = _output_path(output_dir, file_name)
        page_width, page_height = letter
        margin = 36
        pdf = canvas.Canvas(str(file_path), pagesize=letter)
        for image_bytes in images:
            image_buffer, image_width, image_height = _normalized_image_buffer(image_bytes)
            scale = min(
                (page_width - margin * 2) / max(image_width, 1),
                (page_height - margin * 2) / max(image_height, 1),
            )
            draw_width = image_width * scale
            draw_height = image_height * scale
            pdf.drawImage(
                ImageReader(image_buffer),
                (page_width - draw_width) / 2,
                (page_height - draw_height) / 2,
                width=draw_width,
                height=draw_height,
                preserveAspectRatio=True,
                mask="auto",
            )
            pdf.showPage()
        pdf.save()
        return file_name, file_path.as_posix()
    except UnidentifiedImageError as exc:
        raise ValueError("One or more uploaded images are invalid.") from exc


def merge_pdf_bytes(
    pdf_files: list[bytes],
    output_dir: str,
    prefix: str = "merged",
) -> tuple[str, str]:
    if len(pdf_files) < 2:
        raise ValueError("At least two PDF files are required.")

    writer = PdfWriter()
    for pdf_bytes in pdf_files:
        reader = _reader_from_bytes(pdf_bytes)
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs cannot be merged.")
        for page in reader.pages:
            writer.add_page(page)
    return _write_pdf(writer, output_dir, prefix)


def split_pdf_bytes(
    pdf_bytes: bytes,
    output_dir: str,
    page_ranges: str | None = None,
    prefix: str = "split",
) -> tuple[str, str]:
    reader = _reader_from_bytes(pdf_bytes)
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs cannot be split.")

    indexes = _parse_page_ranges(page_ranges, len(reader.pages))
    writer = PdfWriter()
    for page_index in indexes:
        writer.add_page(reader.pages[page_index])
    return _write_pdf(writer, output_dir, prefix)


def compress_pdf_bytes(
    pdf_bytes: bytes,
    output_dir: str,
    prefix: str = "compressed",
) -> tuple[str, str]:
    reader = _reader_from_bytes(pdf_bytes)
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs cannot be compressed.")

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    for page in writer.pages:
        page.compress_content_streams()
    return _write_pdf(writer, output_dir, prefix)


def protect_pdf_bytes(
    pdf_bytes: bytes,
    password: str,
    output_dir: str,
    prefix: str = "protected",
) -> tuple[str, str]:
    if len(password) < 6 or len(password) > 128:
        raise ValueError("Password must be between 6 and 128 characters.")

    reader = _reader_from_bytes(pdf_bytes)
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs cannot be password protected again.")

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(password)
    return _write_pdf(writer, output_dir, prefix)


def validate_pdf_bytes(pdf_bytes: bytes) -> None:
    _reader_from_bytes(pdf_bytes)


def validate_image_bytes(image_bytes: bytes) -> None:
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image.verify()
    except UnidentifiedImageError as exc:
        raise ValueError("Uploaded image is invalid.") from exc


def _normalized_image_buffer(image_bytes: bytes) -> tuple[BytesIO, int, int]:
    with Image.open(BytesIO(image_bytes)) as image:
        image.load()
        width, height = image.size
        if image.mode in {"RGBA", "LA", "P"}:
            image = image.convert("RGBA")
            background = Image.new("RGB", image.size, "white")
            background.paste(image, mask=image.getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")
        output = BytesIO()
        image.save(output, format="PNG")
        output.seek(0)
        return output, width, height


def _reader_from_bytes(pdf_bytes: bytes) -> PdfReader:
    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("Uploaded file is not a valid PDF.")
    try:
        return PdfReader(BytesIO(pdf_bytes), strict=False)
    except (PdfReadError, OSError) as exc:
        raise ValueError("Uploaded file is not a valid PDF.") from exc


def _write_pdf(writer: PdfWriter, output_dir: str, prefix: str) -> tuple[str, str]:
    if len(writer.pages) == 0:
        raise ValueError("Selected PDF has no pages.")
    file_name = make_tool_file_name(prefix)
    file_path = _output_path(output_dir, file_name)
    with file_path.open("wb") as output_file:
        writer.write(output_file)
    return file_name, file_path.as_posix()


def _output_path(output_dir: str, file_name: str) -> Path:
    output_path = _ensure_output_dir(output_dir)
    file_path = (output_path / file_name).resolve()
    if output_path.resolve() not in file_path.parents:
        raise ValueError("Invalid output path.")
    return file_path


def _parse_page_ranges(page_ranges: str | None, page_count: int) -> list[int]:
    if page_count <= 0:
        raise ValueError("Uploaded PDF has no pages.")
    if not page_ranges or not page_ranges.strip():
        return [0]

    indexes: list[int] = []
    for part in page_ranges.split(","):
        value = part.strip()
        if not value:
            continue
        if "-" in value:
            start_raw, end_raw = value.split("-", 1)
            start = _parse_page_number(start_raw, page_count)
            end = _parse_page_number(end_raw, page_count)
            if start > end:
                raise ValueError("Page ranges must be in ascending order.")
            indexes.extend(range(start - 1, end))
        else:
            indexes.append(_parse_page_number(value, page_count) - 1)

    unique_indexes = _dedupe(indexes)
    if not unique_indexes:
        raise ValueError("At least one page must be selected.")
    return unique_indexes


def _parse_page_number(value: str, page_count: int) -> int:
    try:
        page_number = int(value.strip())
    except ValueError as exc:
        raise ValueError("Page ranges must contain only page numbers.") from exc
    if page_number < 1 or page_number > page_count:
        raise ValueError(f"Page number must be between 1 and {page_count}.")
    return page_number


def _dedupe(values: Iterable[int]) -> list[int]:
    seen: set[int] = set()
    result: list[int] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
