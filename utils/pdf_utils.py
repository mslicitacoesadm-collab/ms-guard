from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import List, Optional

import fitz  # PyMuPDF


@dataclass
class PdfDocument:
    name: str
    text: str
    pages: int


def extract_text_from_pdf(file_bytes: bytes, filename: str) -> PdfDocument:
    """Extrai texto de um PDF usando PyMuPDF."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    parts: List[str] = []
    for page in doc:
        text = page.get_text("text") or ""
        parts.append(text)
    joined = "\n".join(parts)
    joined = normalize_text(joined)
    return PdfDocument(name=filename, text=joined, pages=len(doc))


def normalize_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sections(text: str) -> List[str]:
    """Quebra texto em blocos relevantes."""
    markers = [
        r"\nI[\.|\)] ", r"\nII[\.|\)] ", r"\nIII[\.|\)] ", r"\nIV[\.|\)] ",
        r"\nV[\.|\)] ", r"\nVI[\.|\)] ", r"\nVII[\.|\)] ", r"\nVIII[\.|\)] ",
        r"\nIX[\.|\)] ", r"\nX[\.|\)] ",
        r"\nDOS PEDIDOS", r"\nDA TEMPESTIVIDADE", r"\nDAS RAZÕES", r"\nCONCLUSÃO"
    ]
    pattern = "(" + "|".join(markers) + ")"
    chunks = re.split(pattern, text, flags=re.IGNORECASE)
    cleaned = [c.strip() for c in chunks if c and c.strip()]
    return cleaned if cleaned else [text]


def find_articles(text: str) -> List[str]:
    found = re.findall(r"art\.?\s*\d+[A-Za-zº°]*(?:\s*,\s*§\s*\d+[º°]?)?", text, flags=re.IGNORECASE)
    # remove duplicados preservando ordem
    seen = set()
    result = []
    for item in found:
        normalized = item.lower().replace("  ", " ").strip()
        if normalized not in seen:
            seen.add(normalized)
            result.append(item.strip())
    return result


def find_lots(text: str) -> List[str]:
    lots = re.findall(r"lote\s*(?:n[ºo]\s*)?(\d{1,3})", text, flags=re.IGNORECASE)
    seen = set()
    result = []
    for lot in lots:
        if lot not in seen:
            seen.add(lot)
            result.append(lot)
    return result


def excerpt_around_keyword(text: str, keyword: str, window: int = 500) -> Optional[str]:
    low = text.lower()
    idx = low.find(keyword.lower())
    if idx == -1:
        return None
    start = max(0, idx - window)
    end = min(len(text), idx + len(keyword) + window)
    return text[start:end].strip()
