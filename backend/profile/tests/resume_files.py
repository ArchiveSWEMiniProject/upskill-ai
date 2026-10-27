"""Resume files for tests, built in memory so no binaries are committed."""

import io
import zipfile


def pdf_with_text(lines: list[str]) -> bytes:
    """A minimal, valid one-page PDF whose text layer holds `lines`."""
    def escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    body = "BT /F1 11 Tf 50 780 Td 14 TL " + " ".join(
        f"({escape(line)}) Tj T*" for line in lines
    ) + " ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        "/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(body)} >>\nstream\n{body}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{obj}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{offset:010d} 00000 n \n" for offset in offsets).encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    ).encode()
    return bytes(out)


def pdf_without_text() -> bytes:
    """Like a scanned resume: a page with no text layer."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def encrypted_pdf() -> bytes:
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf_with_text(["Secret resume"] * 10))))
    writer.encrypt("open-sesame")
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def docx_with_text(paragraphs: list[str]) -> bytes:
    from docx import Document

    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def docx_zip_bomb() -> bytes:
    """Small on disk, but its contents would expand to 60 MB."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", "<w:document/>")
        archive.writestr("word/padding.bin", b"\0" * (60 * 1024 * 1024))
    return buffer.getvalue()


RESUME_LINES = [
    "Asha Rao - Computer Science undergraduate, PES University",
    "Skills: Python, SQL, React, Docker, Git",
    "Projects: built a REST API with FastAPI and PostgreSQL for study goals",
    "Experience: summer intern working on data pipelines with Pandas",
]
