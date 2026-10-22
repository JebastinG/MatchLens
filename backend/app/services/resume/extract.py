import re
from dataclasses import dataclass

import pymupdf as fitz  # PyMuPDF


class ResumeError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


@dataclass
class ResumeDoc:
    pages: list[str]  # index 0 == page 1
    page_count: int


def has_pdf_signature(head: bytes) -> bool:
    return b"%PDF-" in head[:1024]


def extract_resume(path_or_bytes: str | bytes, max_pages: int, min_chars: int) -> ResumeDoc:
    try:
        doc = (
            fitz.open(stream=path_or_bytes, filetype="pdf")
            if isinstance(path_or_bytes, bytes)
            else fitz.open(path_or_bytes)
        )
    except Exception as exc:
        raise ResumeError("pdf_corrupt", "The file could not be read as a PDF.") from exc
    try:
        if doc.needs_pass or doc.is_encrypted:
            raise ResumeError("pdf_encrypted", "Password-protected PDFs are not supported.")
        if doc.page_count == 0:
            raise ResumeError("pdf_empty", "The PDF has no pages.")
        if doc.page_count > max_pages:
            raise ResumeError("pdf_too_many_pages", f"The PDF has more than {max_pages} pages.")
        pages = []
        for page in doc:
            txt = page.get_text("text")
            pages.append(txt.replace("\x00", ""))
    except ResumeError:
        raise
    except Exception as exc:
        raise ResumeError("pdf_corrupt", "The PDF is damaged and could not be parsed.") from exc
    finally:
        doc.close()
    total = len(re.sub(r"\s+", "", "".join(pages)))
    if total < min_chars:
        raise ResumeError(
            "pdf_no_text",
            "Little or no selectable text was found. Scanned/image-only PDFs are not supported "
            "because OCR is not implemented.",
        )
    return ResumeDoc(pages=pages, page_count=len(pages))
