from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

THEMES: Dict[str, List[str]] = {
    "inexequibilidade": ["inexequ", "preço inexequ", "preco inexequ", "desconto", "50%", "lucrativ"],
    "diligencia": ["diligência", "diligencia", "esclarecimento", "saneamento", "complementação", "complementacao"],
    "erro_material": ["erro material", "erro de cotação", "erro de cotacao", "equívoco", "equivoco"],
    "desistencia": ["desistência", "desistencia", "desistir", "renúncia", "renuncia"],
    "prova": ["planilha", "nota fiscal", "notas fiscais", "laudo", "pesquisa de mercado", "composição de custos", "composicao de custos", "documento", "comprova"],
    "lotes": ["lote", "item", "itens", "parcelamento"],
    "tempestividade": ["tempestividade", "tempestivo", "prazo legal", "prazo recursal"],
    "principios": ["legalidade", "isonomia", "competitividade", "economicidade", "julgamento objetivo", "boa-fé", "boa-fé objetiva", "razoabilidade", "proporcionalidade", "segurança jurídica"],
    "pedido_subsidiario": ["subsidiariamente", "caso não", "caso nao", "pedido subsidiário", "pedido subsidiario"],
    "edital": ["edital", "termo de referência", "termo de referencia", "instrumento convocatório", "instrumento convocatorio"],
    "habilitacao": ["habilitação", "habilitacao", "qualificação técnica", "qualificacao tecnica", "atestado", "capacidade técnica"],
    "amostra_marca": ["amostra", "marca", "modelo", "catálogo", "catalogo", "equivalente"]
}

SECTION_HINTS = [
    "tempestividade",
    "síntese", "sintese",
    "fatos",
    "mérito", "merito",
    "fundamentação", "fundamentacao",
    "pedidos",
    "conclusão", "conclusao"
]


@dataclass
class ThemeMatch:
    name: str
    found: bool
    hits: int


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def count_theme_hits(text: str) -> List[ThemeMatch]:
    low = normalize(text)
    matches: List[ThemeMatch] = []
    for theme, words in THEMES.items():
        hits = 0
        for word in words:
            hits += len(re.findall(re.escape(normalize(word)), low))
        matches.append(ThemeMatch(name=theme, found=hits > 0, hits=hits))
    return matches


def theme_map(text: str) -> Dict[str, int]:
    return {m.name: m.hits for m in count_theme_hits(text)}


def detect_structure_score(text: str) -> Tuple[int, List[str]]:
    low = normalize(text)
    found = [token for token in SECTION_HINTS if normalize(token) in low]
    score = min(10, max(2, len(set(found)) + 2))
    notes: List[str] = []
    if "pedidos" not in low:
        notes.append("Os pedidos finais não ficaram claramente destacados.")
    if "tempestividade" not in low and "tempestivo" not in low:
        notes.append("Vale deixar a tempestividade expressa logo no início da peça.")
    if "síntese" not in low and "sintese" not in low and "fatos" not in low:
        notes.append("Pode melhorar a explicação inicial do conflito antes de entrar na defesa.")
    return score, notes


def find_missing_counterarguments(recurso_text: str, contrarrazao_text: str) -> List[str]:
    rec = theme_map(recurso_text)
    con = theme_map(contrarrazao_text)
    return [theme for theme, hits in rec.items() if hits > 0 and con.get(theme, 0) == 0]


def score_counterargument_coverage(recurso_text: str, contrarrazao_text: str) -> Tuple[int, List[str]]:
    missing = find_missing_counterarguments(recurso_text, contrarrazao_text)
    total_themes = sum(1 for _, hits in theme_map(recurso_text).items() if hits > 0)
    if total_themes == 0:
        return 5, ["O recurso trouxe poucos temas identificáveis para comparação automática."]
    covered = max(0, total_themes - len(missing))
    ratio = covered / total_themes
    score = max(2, min(10, round(ratio * 10)))
    notes = [f"O recurso parece tocar em '{theme}' sem resposta clara na contrarrazão." for theme in missing]
    return score, notes


def score_evidence_strength(text: str) -> Tuple[int, List[str]]:
    low = normalize(text)
    evidence_terms = [
        "planilha", "nota fiscal", "notas fiscais", "laudo", "pesquisa de mercado",
        "composição de custos", "composicao de custos", "documento", "documentação", "documentacao"
    ]
    hits = sum(1 for term in evidence_terms if normalize(term) in low)
    score = min(10, max(2, hits + 2))
    notes: List[str] = []
    if "planilha" not in low and "composição de custos" not in low and "composicao de custos" not in low:
        notes.append("A defesa pode ficar mais forte se citar planilha, memória de cálculo ou composição de custos.")
    if "nota fiscal" not in low and "notas fiscais" not in low and "pesquisa de mercado" not in low:
        notes.append("Faltou mencionar prova material concreta, como nota fiscal, orçamento ou pesquisa de mercado.")
    return score, notes


def score_edital_adherence(edital_text: str, piece_text: str) -> Tuple[int, List[str]]:
    edital_low = normalize(edital_text)
    piece_low = normalize(piece_text)
    notes: List[str] = []
    score = 4

    if "edital" in piece_low:
        score += 1
    else:
        notes.append("A peça deveria citar o edital de modo mais direto.")

    if "termo de referência" in piece_low or "termo de referencia" in piece_low:
        score += 1
    else:
        notes.append("Vale amarrar melhor a tese ao termo de referência.")

    edital_lots = re.findall(r"lote\s*(\d{1,3})", edital_low)
    piece_lots = re.findall(r"lote\s*(\d{1,3})", piece_low)
    overlap = set(edital_lots).intersection(set(piece_lots))
    if overlap:
        score += 2
    else:
        notes.append("A peça não conectou claramente os lotes citados ao edital.")

    if any(a in piece_low for a in ["art. 59", "art. 64", "art. 165", "art. 170"]):
        score += 1

    return min(10, score), notes


def score_plain_language(text: str) -> Tuple[int, List[str]]:
    words = re.findall(r"\w+", text)
    long_words = [w for w in words if len(w) >= 14]
    latinisms = [
        "consubstanciado", "precípuo", "edilício", "edilicias", "ex vi", "data venia", "outrossim", "alhures"
    ]
    low = normalize(text)
    hits_latin = sum(1 for term in latinisms if normalize(term) in low)
    ratio_long = (len(long_words) / max(1, len(words)))
    score = 9
    notes: List[str] = []
    if ratio_long > 0.18:
        score -= 2
        notes.append("A linguagem está mais técnica do que o ideal para público leigo.")
    if hits_latin >= 2:
        score -= 2
        notes.append("Há expressões muito jurídicas; vale traduzir para uma escrita mais direta.")
    if len(re.findall(r";", text)) > 12:
        score -= 1
        notes.append("Há períodos longos demais; frases mais curtas melhoram a leitura.")
    return max(3, min(10, score)), notes


def risk_label(score: int) -> str:
    if score >= 8:
        return "baixo"
    if score >= 5:
        return "médio"
    return "alto"
