from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

from utils.pdf_utils import PdfDocument, find_articles, find_lots, excerpt_around_keyword
from utils.text_rules import (
    theme_map,
    detect_structure_score,
    score_counterargument_coverage,
    score_evidence_strength,
    score_edital_adherence,
    risk_label,
)


@dataclass
class AnalysisResult:
    resumo_executivo: str
    notas: Dict[str, int]
    risco_geral: str
    pontos_fortes: List[str]
    fragilidades: List[str]
    argumentos_nao_enfrentados: List[str]
    artigos_identificados: Dict[str, List[str]]
    lotes_identificados: Dict[str, List[str]]
    trechos_relevantes: Dict[str, Optional[str]]
    recomendacoes: List[str]


class LicitacaoAnalyzer:
    def __init__(self, knowledge_path: str = "knowledge/lei_14133_base.json") -> None:
        self.knowledge_path = Path(knowledge_path)
        self.knowledge = self._load_knowledge()

    def _load_knowledge(self) -> Dict:
        if not self.knowledge_path.exists():
            return {"artigos": []}
        with self.knowledge_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def suggest_legal_articles(self, text: str) -> List[Dict[str, str]]:
        low = text.lower()
        suggestions: List[Dict[str, str]] = []
        for item in self.knowledge.get("artigos", []):
            if any(keyword.lower() in low for keyword in item.get("palavras_chave", [])):
                suggestions.append(item)
        dedup = []
        seen = set()
        for item in suggestions:
            art = item["artigo"]
            if art not in seen:
                seen.add(art)
                dedup.append(item)
        return dedup[:8]

    def analyze(
        self,
        edital: PdfDocument,
        recurso: PdfDocument,
        contrarrazao: PdfDocument,
        lei_pdf_text: Optional[str] = None,
    ) -> AnalysisResult:
        # Notas principais
        estrutura_score, estrutura_notes = detect_structure_score(contrarrazao.text)
        cobertura_score, cobertura_notes = score_counterargument_coverage(recurso.text, contrarrazao.text)
        prova_score, prova_notes = score_evidence_strength(contrarrazao.text)
        edital_score, edital_notes = score_edital_adherence(edital.text, contrarrazao.text)
        base_legal_score = self._score_legal_basis(contrarrazao.text)
        risco_score = round((estrutura_score + cobertura_score + prova_score + edital_score + base_legal_score) / 5)

        notas = {
            "estrutura": estrutura_score,
            "enfrentamento_do_recurso": cobertura_score,
            "prova_e_lastro": prova_score,
            "aderencia_ao_edital": edital_score,
            "base_legal": base_legal_score,
            "solidez_geral": risco_score,
        }

        argumentos_nao_enfrentados = self._friendly_missing_arguments(recurso.text, contrarrazao.text)
        pontos_fortes = self._build_strengths(edital.text, recurso.text, contrarrazao.text, notas)
        fragilidades = self._build_weaknesses(estrutura_notes, cobertura_notes, prova_notes, edital_notes, contrarrazao_text=contrarrazao.text)
        recomendacoes = self._build_recommendations(argumentos_nao_enfrentados, contrarrazao.text)

        artigos_identificados = {
            "recurso": find_articles(recurso.text),
            "contrarrazao": find_articles(contrarrazao.text),
            "edital": find_articles(edital.text),
            "sugeridos_pela_base": [item["artigo"] for item in self.suggest_legal_articles(recurso.text + "\n" + contrarrazao.text)]
        }

        lotes_identificados = {
            "recurso": find_lots(recurso.text),
            "contrarrazao": find_lots(contrarrazao.text),
            "edital": find_lots(edital.text),
        }

        trechos_relevantes = {
            "trecho_inexequibilidade_recurso": excerpt_around_keyword(recurso.text, "inexequ"),
            "trecho_diligencia_contrarrazao": excerpt_around_keyword(contrarrazao.text, "dilig"),
            "trecho_erro_material_contrarrazao": excerpt_around_keyword(contrarrazao.text, "erro material"),
            "trecho_pedido_contrarrazao": excerpt_around_keyword(contrarrazao.text, "pedidos"),
            "trecho_edital_lotes": excerpt_around_keyword(edital.text, "lote"),
        }

        resumo = self._build_summary(notas, argumentos_nao_enfrentados, lotes_identificados, contrarrazao.text, recurso.text, lei_pdf_text)

        return AnalysisResult(
            resumo_executivo=resumo,
            notas=notas,
            risco_geral=risk_label(risco_score),
            pontos_fortes=pontos_fortes,
            fragilidades=fragilidades,
            argumentos_nao_enfrentados=argumentos_nao_enfrentados,
            artigos_identificados=artigos_identificados,
            lotes_identificados=lotes_identificados,
            trechos_relevantes=trechos_relevantes,
            recomendacoes=recomendacoes,
        )

    def _score_legal_basis(self, text: str) -> int:
        cited = find_articles(text)
        score = min(10, max(2, len(cited) + 2))
        suggested = self.suggest_legal_articles(text)
        if suggested:
            score = min(10, score + 1)
        return score

    def _friendly_missing_arguments(self, recurso_text: str, contrarrazao_text: str) -> List[str]:
        rec = theme_map(recurso_text)
        con = theme_map(contrarrazao_text)
        labels = {
            "inexequibilidade": "tese de inexequibilidade / preço inexequível",
            "diligencia": "tratamento da diligência administrativa",
            "erro_material": "erro material / erro de cotação",
            "desistencia": "pedido de desistência ou solução subsidiária",
            "prova": "enfrentamento probatório com planilha, notas ou estudo",
            "lote_autonomo": "autonomia dos lotes",
            "tempestividade": "tempestividade recursal",
            "principios": "princípios da Lei 14.133/2021",
            "pedido_subsidiario": "pedido subsidiário",
            "vinculacao_edital": "vinculação ao edital / termo de referência"
        }
        missing = []
        for key, hits in rec.items():
            if hits > 0 and con.get(key, 0) == 0:
                missing.append(labels.get(key, key))
        return missing

    def _build_strengths(self, edital_text: str, recurso_text: str, contrarrazao_text: str, notas: Dict[str, int]) -> List[str]:
        strengths: List[str] = []
        if notas["enfrentamento_do_recurso"] >= 8:
            strengths.append("A contrarrazão enfrenta de forma consistente os eixos centrais do recurso.")
        if notas["aderencia_ao_edital"] >= 7:
            strengths.append("Há boa conexão entre os argumentos da defesa e a lógica do edital/lotes.")
        if "erro material" in contrarrazao_text.lower():
            strengths.append("A peça apresenta tese subsidiária de erro material, útil para reduzir risco de penalidade.")
        if "desist" in contrarrazao_text.lower():
            strengths.append("Há estratégia processual alternativa com pedido de desistência, o que protege a parte em cenário de risco.")
        if "dilig" in contrarrazao_text.lower():
            strengths.append("A contrarrazão trata a diligência como instrumento de saneamento e esclarecimento, o que costuma fortalecer a defesa.")
        if "marçal" in contrarrazao_text.lower() or "justen" in contrarrazao_text.lower():
            strengths.append("A peça usa apoio doutrinário, o que aumenta sua densidade argumentativa.")
        if not strengths:
            strengths.append("A peça possui uma linha defensiva minimamente organizada.")
        return strengths

    def _build_weaknesses(self, *note_groups: List[str], contrarrazao_text: str | None = None) -> List[str]:
        weaknesses: List[str] = []
        for group in note_groups:
            weaknesses.extend(group)
        low = (contrarrazao_text or "").lower()
        if "subsidiariamente" not in low and "caso não" not in low and "caso nao" not in low:
            weaknesses.append("A peça pode ganhar robustez com pedido subsidiário expresso.")
        if "nota fiscal" not in low and "notas fiscais" not in low:
            weaknesses.append("A defesa pode ficar mais forte com referência direta a prova documental específica.")
        # remover duplicados
        dedup = []
        seen = set()
        for item in weaknesses:
            if item not in seen:
                seen.add(item)
                dedup.append(item)
        return dedup[:10]

    def _build_recommendations(self, missing_arguments: List[str], contrarrazao_text: str) -> List[str]:
        recs: List[str] = []
        if missing_arguments:
            for arg in missing_arguments[:5]:
                recs.append(f"Reforçar expressamente o ponto: {arg}.")
        if "erro material" in contrarrazao_text.lower() and "desist" in contrarrazao_text.lower():
            recs.append("Anexar, se possível, justificativa objetiva do erro de cotação para robustecer a boa-fé.")
        if "planilha" not in contrarrazao_text.lower():
            recs.append("Mencionar ou anexar planilha/memória de cálculo, quando existir, para aumentar o lastro técnico.")
        if "termo de referência" not in contrarrazao_text.lower() and "termo de referencia" not in contrarrazao_text.lower():
            recs.append("Amarrar a defesa aos itens do termo de referência e às regras do edital.")
        if not recs:
            recs.append("Ajustes finos podem focar em anexos probatórios e reforço do pedido final.")
        return recs[:10]

    def _build_summary(
        self,
        notas: Dict[str, int],
        missing_arguments: List[str],
        lotes_identificados: Dict[str, List[str]],
        contrarrazao_text: str,
        recurso_text: str,
        lei_pdf_text: Optional[str],
    ) -> str:
        summary = [
            f"A análise automática indica solidez geral {notas['solidez_geral']}/10, com risco processual {risk_label(notas['solidez_geral'])}.",
            f"A contrarrazão obteve notas de estrutura {notas['estrutura']}/10, enfrentamento do recurso {notas['enfrentamento_do_recurso']}/10, aderência ao edital {notas['aderencia_ao_edital']}/10, prova/lastro {notas['prova_e_lastro']}/10 e base legal {notas['base_legal']}/10.",
        ]
        if set(lotes_identificados.get("recurso", [])) and set(lotes_identificados.get("contrarrazao", [])):
            overlap = set(lotes_identificados["recurso"]).intersection(set(lotes_identificados["contrarrazao"]))
            if overlap:
                summary.append(f"Há correspondência objetiva de lotes entre recurso e contrarrazão: {', '.join(sorted(overlap))}.")
        if "erro material" in contrarrazao_text.lower():
            summary.append("A defesa contém tese de erro material, o que tende a reduzir risco quando o documento busca afastar má-fé e justificar desistência ou correção.")
        if "inexequ" in recurso_text.lower():
            summary.append("O recurso gira em torno de inexequibilidade/preço, exigindo resposta com foco em prova, diligência, edital e análise concreta do caso.")
        if missing_arguments:
            summary.append(f"Ainda assim, há pontos que merecem reforço: {', '.join(missing_arguments[:4])}.")
        if lei_pdf_text:
            summary.append("Foi fornecido PDF auxiliar da Lei 14.133/2021 na sessão, podendo apoiar conferência textual durante a revisão humana.")
        return " ".join(summary)


def result_to_dict(result: AnalysisResult) -> Dict:
    return asdict(result)
