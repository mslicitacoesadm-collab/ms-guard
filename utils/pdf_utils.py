from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

import fitz


@dataclass
class PdfDocument:
    name: str
    text: str
    pages: int


def _clean_text(text: str) -> str:
    text = text.replace('\x00', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_text_from_pdf(file_bytes: bytes, filename: str) -> PdfDocument:
    text_parts = []
    pages = 0
    with fitz.open(stream=file_bytes, filetype='pdf') as doc:
        pages = len(doc)
        for page in doc:
            text_parts.append(page.get_text('text'))
    text = _clean_text('\n'.join(text_parts))
    return PdfDocument(name=filename, text=text, pages=pages)


def find_articles(text: str) -> List[str]:
    matches = re.findall(r'art\.\s*\d+[ºo]?(?:\s*,\s*§\s*\d+[ºo]?)?', text, flags=re.IGNORECASE)
    result, seen = [], set()
    for m in matches:
        key = m.lower().replace('o', 'º')
        if key not in seen:
            seen.add(key)
            result.append(m)
    return result


def find_lots(text: str) -> List[str]:
    lots = re.findall(r'lote\s*(?:n[ºo]\s*)?(\d{1,3})', text, flags=re.IGNORECASE)
    items = re.findall(r'item\s*(?:n[ºo]\s*)?(\d{1,3})', text, flags=re.IGNORECASE)
    seen, result = set(), []
    for value in lots + items:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def excerpt_around_keyword(text: str, keyword: str, window: int = 450) -> Optional[str]:
    low = text.lower()
    idx = low.find(keyword.lower())
    if idx == -1:
        return None
    start = max(0, idx - window)
    end = min(len(text), idx + len(keyword) + window)
    return text[start:end].strip()
