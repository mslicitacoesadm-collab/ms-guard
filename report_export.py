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
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('\n', '<br/>')
    )


def _add_list(story, styles, title: str, items: list[str]) -> None:
    story.append(Paragraph(_safe(title), styles['HeadLG']))
    if not items:
        story.append(Paragraph('Nenhum item.', styles['BodyLG']))
        return
    for item in items:
        story.append(Paragraph(_safe(f'• {item}'), styles['BodyLG']))


def build_pdf_report(result: Dict, titulo: str = 'Relatório MS Licitações IA') -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.3 * cm,
        bottomMargin=1.3 * cm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleLG', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=18, leading=22, spaceAfter=10))
    styles.add(ParagraphStyle(name='HeadLG', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, leading=15, spaceBefore=8, spaceAfter=5))
    styles.add(ParagraphStyle(name='BodyLG', parent=styles['BodyText'], fontName='Helvetica', fontSize=9.5, leading=12))

    story = [Paragraph(_safe(titulo), styles['TitleLG'])]
    story.append(Paragraph(_safe(result.get('quem_esta_mais_forte', '')), styles['HeadLG']))
    story.append(Paragraph(_safe(result.get('leitura_humana', '')), styles['BodyLG']))
    story.append(Spacer(1, 0.15 * cm))
    story.append(Paragraph(_safe(result.get('resumo_executivo', '')), styles['BodyLG']))

    story.append(Paragraph('Notas', styles['HeadLG']))
    for chave, valor in result.get('notas', {}).items():
        story.append(Paragraph(_safe(f'• {chave.replace("_", " ").title()}: {valor}/10'), styles['BodyLG']))

    _add_list(story, styles, 'Pontos fortes', result.get('pontos_fortes', []))
    _add_list(story, styles, 'Fragilidades', result.get('fragilidades', []))
    _add_list(story, styles, 'Argumentos não enfrentados', result.get('argumentos_nao_enfrentados', []))
    _add_list(story, styles, 'Recomendações', result.get('recomendacoes', []))

    story.append(Paragraph('Resposta automática', styles['HeadLG']))
    story.append(Paragraph(_safe(result.get('resposta_automatica', '')), styles['BodyLG']))

    story.append(Paragraph('Reforço sugerido para a contrarrazão', styles['HeadLG']))
    story.append(Paragraph(_safe(result.get('reforco_contrarrazao', '')), styles['BodyLG']))

    story.append(Paragraph('Minuta de decisão do pregoeiro', styles['HeadLG']))
    story.append(Paragraph(_safe(result.get('minuta_decisao', '')), styles['BodyLG']))

    story.append(Paragraph('Painel por tese jurídica', styles['HeadLG']))
    for row in result.get('painel_teses', []):
        line = f"• {row.get('tese', '')}: {row.get('status', '')} | impacto {row.get('impacto', '')} | {row.get('leitura', '')}"
        story.append(Paragraph(_safe(line), styles['BodyLG']))

    doc.build(story)
    return buffer.getvalue()
