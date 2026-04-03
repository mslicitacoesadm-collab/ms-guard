from __future__ import annotations

import io
from typing import Dict

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def _safe(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def build_pdf_report(result: Dict, titulo: str = "Relatório LicitaGuard") -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleLG", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, spaceAfter=12))
    styles.add(ParagraphStyle(name="HeadLG", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, spaceBefore=10, spaceAfter=6))
    styles.add(ParagraphStyle(name="BodyLG", parent=styles["BodyText"], fontName="Helvetica", fontSize=10, leading=13))

    story = [Paragraph(_safe(titulo), styles["TitleLG"])]
    story.append(Paragraph(_safe(result.get("quem_esta_mais_forte", "")), styles["HeadLG"]))
    story.append(Paragraph(_safe(result.get("leitura_humana", "")), styles["BodyLG"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(_safe(result.get("resumo_executivo", "")), styles["BodyLG"]))

    story.append(Paragraph("Notas", styles["HeadLG"]))
    for chave, valor in result.get("notas", {}).items():
        story.append(Paragraph(_safe(f"• {chave.replace('_', ' ').title()}: {valor}/10"), styles["BodyLG"]))

    for bloco in ["pontos_fortes", "fragilidades", "argumentos_nao_enfrentados", "recomendacoes"]:
        story.append(Paragraph(bloco.replace("_", " ").title(), styles["HeadLG"]))
        for item in result.get(bloco, []):
            story.append(Paragraph(_safe(f"• {item}"), styles["BodyLG"]))

    story.append(Paragraph("Artigos identificados", styles["HeadLG"]))
    for chave, valores in result.get("artigos_identificados", {}).items():
        texto = ", ".join(valores) if valores else "nenhum"
        story.append(Paragraph(_safe(f"• {chave}: {texto}"), styles["BodyLG"]))

    doc.build(story)
    return buffer.getvalue()
