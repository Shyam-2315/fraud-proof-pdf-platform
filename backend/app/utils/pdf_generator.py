from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.utils.security import generate_uuid, utc_now


def generate_simple_pdf(
    title: str,
    content: str,
    output_dir: str = "generated_files",
) -> tuple[str, str]:
    """
    Generate a simple PDF file on disk for a title and text body.

    Args:
        title: Title rendered at the top of the PDF.
        content: Main text content rendered into the PDF body.
        output_dir: Directory where the generated PDF should be stored.

    Returns:
        Tuple containing the generated file name and absolute POSIX file path.
    """
    output_path = _ensure_output_dir(output_dir)

    file_name = f"generated_{generate_uuid()}.pdf"
    file_path = output_path / file_name

    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(str(file_path), pagesize=letter)
    story = [
        Paragraph(escape(title), styles["Title"]),
        Spacer(1, 16),
        Paragraph(f"Created: {utc_now().isoformat()}", styles["Normal"]),
        Spacer(1, 16),
    ]

    escaped_content = escape(content).replace("\n", "<br/>")
    story.append(Paragraph(escaped_content, styles["BodyText"]))
    document.build(story)

    return file_name, file_path.as_posix()


@lru_cache(maxsize=8)
def _ensure_output_dir(output_dir: str) -> Path:
    """
    Create and cache the output directory used for generated PDFs.

    Args:
        output_dir: Directory path that should exist for generated files.

    Returns:
        Filesystem path object for the ensured directory.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path
