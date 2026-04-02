from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple


THEMES: Dict[str, List[str]] = {
    "inexequibilidade": ["inexequ", "preço inexequ", "desconto", "50%", "lucrativ"],
    "diligencia": ["diligência", "diligencia", "art. 64", "esclarecimento", "saneamento"],
    "erro_material": ["erro material", "erro de cotação", "erro de cotacao", "equívoco operacional", "equivoco operacional"],
    "desistencia": ["desistência", "desistencia", "desistir", "art. 170"],
    "prova": ["planilha", "nota fiscal", "notas fiscais", "laudo", "pesquisa de mercado", "composição de custos", "composicao de custos"],
    "lote_autonomo": ["autonomia dos lotes", "autonomia entre os lotes", "lote 06", "lote 07", "art. 47"],
    "tempestividade": ["tempestividade", "prazo legal", "art. 165", "tempestivo"],
    "principios": ["legalidade", "isonomia", "competitividade", "economicidade", "julgamento objetivo", "boa-fé", "boa-fé objetiva", "razoabilidade", "proporcionalidade"],
    "pedido_subsidiario": ["subsidiariamente", "caso não", "caso nao", "pedido subsidiário", "pedido subsidiario"],
    "vinculacao_edital": ["vinculação ao instrumento convocatório", "vinculacao ao instrumento convocatorio", "edital", "termo de referência", "termo de referencia"]
}

STRUCTURE_HINTS = [
    "tempestividade",
    "síntese",
    "sintese",
    "mérito",
    "merito",
    "pedidos",
    "conclusão",
    "conclusao"
]


@dataclass
class ThemeMatch:
    name: str
    found: bool
    hits: int


def count_theme_hits(text: str) -> List[ThemeMatch]:
    low = text.lower()
    matches: List[ThemeMatch] = []
    for theme, words in THEMES.items():
        hits = 0
        for word in words:
            hits += len(re.findall(re.escape(word.lower()), low))
        matches.append(ThemeMatch(name=theme, found=hits > 0, hits=hits))
    return matches


def theme_map(text: str) -> Dict[str, int]:
    return {m.name: m.hits for m in count_theme_hits(text)}


def detect_structure_score(text: str) -> Tuple[int, List[str]]:
    low = text.lower()
    found = [token for token in STRUCTURE_HINTS if token in low]
    score = min(10, max(2, len(set(found)) + 3))
    notes: List[str] = []
    if "pedidos" not in low:
        notes.append("A peça não destacou claramente a seção de pedidos.")
    if "tempestividade" not in low and "tempestivo" not in low:
        notes.append("A peça não evidenciou tempestividade de forma expressa.")
    if "síntese" not in low and "sintese" not in low:
        notes.append("A peça pode melhorar a síntese inicial do conflito.")
    return score, notes


def find_missing_counterarguments(recurso_text: str, contrarrazao_text: str) -> List[str]:
    rec = theme_map(recurso_text)
    con = theme_map(contrarrazao_text)
    missing: List[str] = []
    for theme, hits in rec.items():
        if hits > 0 and con.get(theme, 0) == 0:
            missing.append(theme)
    return missing


def score_counterargument_coverage(recurso_text: str, contrarrazao_text: str) -> Tuple[int, List[str]]:
    missing = find_missing_counterarguments(recurso_text, contrarrazao_text)
    total_themes = sum(1 for _, hits in theme_map(recurso_text).items() if hits > 0)
    covered = max(0, total_themes - len(missing))
    if total_themes == 0:
        return 5, ["O recurso não apresentou temas suficientes para comparação automática robusta."]
    ratio = covered / total_themes
    score = max(2, min(10, round(ratio * 10)))
    notes = [f"Tema do recurso sem enfrentamento claro: {theme}." for theme in missing]
    return score, notes


def score_evidence_strength(text: str) -> Tuple[int, List[str]]:
    low = text.lower()
    evidence_terms = [
        "planilha", "nota fiscal", "notas fiscais", "laudo", "pesquisa de mercado",
        "composição de custos", "composicao de custos", "documentação", "documentacao"
    ]
    hits = sum(1 for term in evidence_terms if term in low)
    score = min(10, max(2, hits + 2))
    notes: List[str] = []
    if "planilha" not in low:
        notes.append("Não há menção expressa a planilha ou memória de cálculo.")
    if "nota fiscal" not in low and "notas fiscais" not in low:
        notes.append("Não há menção expressa a notas fiscais como prova material.")
    return score, notes


def score_edital_adherence(edital_text: str, piece_text: str) -> Tuple[int, List[str]]:
    edital_low = edital_text.lower()
    piece_low = piece_text.lower()
    notes: List[str] = []
    score = 5

    if "edital" in piece_low:
        score += 1
    else:
        notes.append("A peça poderia referenciar o edital de forma mais direta.")

    if "termo de referência" in piece_low or "termo de referencia" in piece_low:
        score += 1
    else:
        notes.append("A peça poderia amarrar melhor a tese ao termo de referência.")

    edital_lots = re.findall(r"lote\s*(\d{1,3})", edital_low)
    piece_lots = re.findall(r"lote\s*(\d{1,3})", piece_low)
    overlap = set(edital_lots).intersection(set(piece_lots))
    if overlap:
        score += 2
    else:
        notes.append("A peça não vinculou de forma clara os lotes mencionados ao edital.")

    if "art. 64" in piece_low or "art. 59" in piece_low or "art. 165" in piece_low:
        score += 1

    return min(10, score), notes


def risk_label(score: int) -> str:
    if score >= 8:
        return "baixo"
    if score >= 5:
        return "médio"
    return "alto"
