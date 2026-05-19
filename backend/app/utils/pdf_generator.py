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
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

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
