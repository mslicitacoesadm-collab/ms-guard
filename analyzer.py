from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

from utils.pdf_utils import PdfDocument, excerpt_around_keyword, find_articles, find_lots
from utils.text_rules import (
    THEMES,
    detect_structure_score,
    find_missing_counterarguments,
    risk_label,
    score_counterargument_coverage,
    score_edital_adherence,
    score_evidence_strength,
    score_plain_language,
    theme_map,
)


@dataclass
class AnalysisResult:
    resumo_executivo: str
    leitura_humana: str
    quem_esta_mais_forte: str
    notas: Dict[str, int]
    risco_geral: str
    pontos_fortes: List[str]
    fragilidades: List[str]
    argumentos_nao_enfrentados: List[str]
    artigos_identificados: Dict[str, List[str]]
    lotes_identificados: Dict[str, List[str]]
    trechos_relevantes: Dict[str, Optional[str]]
    recomendacoes: List[str]
    explicacao_notas: Dict[str, str]
    painel_teses: List[Dict[str, str]]
    resposta_automatica: str
    reforco_contrarrazao: str
    minuta_decisao: str


class LicitacaoAnalyzer:
    def __init__(self, knowledge_path: str = 'knowledge/lei_14133_base.json') -> None:
        self.knowledge_path = Path(knowledge_path)
        self.knowledge = self._load_knowledge()

    def _load_knowledge(self) -> Dict:
        if not self.knowledge_path.exists():
            return {'artigos': []}
        return json.loads(self.knowledge_path.read_text(encoding='utf-8'))

    def suggest_legal_articles(self, text: str) -> List[Dict[str, str]]:
        low = text.lower()
        out: List[Dict[str, str]] = []
        for item in self.knowledge.get('artigos', []):
            if any(k.lower() in low for k in item.get('palavras_chave', [])):
                out.append(item)
        dedup, seen = [], set()
        for item in out:
            if item['artigo'] not in seen:
                dedup.append(item)
                seen.add(item['artigo'])
        return dedup[:12]

    def analyze(
        self,
        edital: PdfDocument,
        recurso: PdfDocument,
        contrarrazao: PdfDocument,
        lei_pdf_text: Optional[str] = None,
        pergunta_usuario: str = '',
        lote_foco: str = '',
    ) -> AnalysisResult:
        estrutura_score, estrutura_notes = detect_structure_score(contrarrazao.text)
        cobertura_score, cobertura_notes = score_counterargument_coverage(recurso.text, contrarrazao.text)
        prova_score, prova_notes = score_evidence_strength(contrarrazao.text)
        edital_score, edital_notes = score_edital_adherence(edital.text, contrarrazao.text)
        clareza_score, clareza_notes = score_plain_language(contrarrazao.text)
        base_legal_score = self._score_legal_basis(contrarrazao.text, lei_pdf_text or '')
        solidez = round((estrutura_score + cobertura_score + prova_score + edital_score + base_legal_score) / 5)

        notas = {
            'estrutura': estrutura_score,
            'enfrentamento_do_recurso': cobertura_score,
            'prova_e_lastro': prova_score,
            'aderencia_ao_edital': edital_score,
            'base_legal': base_legal_score,
            'clareza_para_leigos': clareza_score,
            'solidez_geral': solidez,
        }

        argumentos_nao_enfrentados = self._friendly_missing_arguments(recurso.text, contrarrazao.text)
        pontos_fortes = self._build_strengths(contrarrazao.text, notas)
        fragilidades = self._build_weaknesses(
            estrutura_notes,
            cobertura_notes,
            prova_notes,
            edital_notes,
            clareza_notes,
            contrarrazao_text=contrarrazao.text,
        )
        recomendacoes = self._build_recommendations(argumentos_nao_enfrentados, contrarrazao.text)
        explicacao_notas = self._build_grade_explanations(notas)
        mais_forte = self._who_is_stronger(recurso.text, contrarrazao.text, notas)

        artigos_identificados = {
            'edital': find_articles(edital.text),
            'recurso': find_articles(recurso.text),
            'contrarrazao': find_articles(contrarrazao.text),
            'sugeridos_pela_base': [x['artigo'] for x in self.suggest_legal_articles(recurso.text + '\n' + contrarrazao.text + '\n' + edital.text)],
        }
        lotes_identificados = {
            'edital': find_lots(edital.text),
            'recurso': find_lots(recurso.text),
            'contrarrazao': find_lots(contrarrazao.text),
        }
        trechos_relevantes = {
            'edital_objeto': excerpt_around_keyword(edital.text, 'objeto'),
            'edital_regra_desclassificacao': excerpt_around_keyword(edital.text, 'desclass'),
            'recurso_tese_principal': excerpt_around_keyword(recurso.text, 'inexequ') or excerpt_around_keyword(recurso.text, 'ilegal'),
            'contrarrazao_resposta_principal': excerpt_around_keyword(contrarrazao.text, 'inexequ') or excerpt_around_keyword(contrarrazao.text, 'dilig'),
            'contrarrazao_pedidos': excerpt_around_keyword(contrarrazao.text, 'pedido'),
        }

        painel_teses = self._build_thesis_panel(recurso.text, contrarrazao.text, edital.text)
        resumo_executivo = self._build_summary(notas, argumentos_nao_enfrentados, lotes_identificados, mais_forte, lote_foco)
        leitura_humana = self._build_human_reading(notas, mais_forte, fragilidades, argumentos_nao_enfrentados)
        resposta_automatica = self._answer_user_question(pergunta_usuario, mais_forte, notas, fragilidades, argumentos_nao_enfrentados, painel_teses)
        reforco_contrarrazao = self._generate_reinforcement(painel_teses, argumentos_nao_enfrentados, recomendacoes)
        minuta_decisao = self._generate_decision_draft(mais_forte, painel_teses, lotes_identificados, fragilidades)

        return AnalysisResult(
            resumo_executivo=resumo_executivo,
            leitura_humana=leitura_humana,
            quem_esta_mais_forte=mais_forte,
            notas=notas,
            risco_geral=risk_label(solidez),
            pontos_fortes=pontos_fortes,
            fragilidades=fragilidades,
            argumentos_nao_enfrentados=argumentos_nao_enfrentados,
            artigos_identificados=artigos_identificados,
            lotes_identificados=lotes_identificados,
            trechos_relevantes=trechos_relevantes,
            recomendacoes=recomendacoes,
            explicacao_notas=explicacao_notas,
            painel_teses=painel_teses,
            resposta_automatica=resposta_automatica,
            reforco_contrarrazao=reforco_contrarrazao,
            minuta_decisao=minuta_decisao,
        )

    def _score_legal_basis(self, text: str, extra_text: str = '') -> int:
        cited = find_articles(text)
        score = min(10, max(2, len(cited) + 2))
        if self.suggest_legal_articles(text + '\n' + extra_text):
            score = min(10, score + 1)
        return score

    def _friendly_missing_arguments(self, recurso_text: str, contrarrazao_text: str) -> List[str]:
        labels = {
            'inexequibilidade': 'falta resposta mais direta sobre preço inexequível ou inexequibilidade',
            'diligencia': 'falta explicar melhor a diligência e o que ela significa no caso',
            'erro_material': 'falta tratar erro material ou erro de cotação, se isso fizer parte do caso',
            'desistencia': 'falta pedido alternativo, como desistência ou solução subsidiária',
            'prova': 'falta citar provas concretas, como planilha, nota fiscal ou pesquisa de mercado',
            'lotes': 'falta separar com mais clareza os lotes ou itens discutidos',
            'tempestividade': 'falta destacar a tempestividade da manifestação',
            'principios': 'falta conectar os fatos aos princípios da Lei 14.133',
            'pedido_subsidiario': 'falta pedido subsidiário claro',
            'edital': 'falta amarrar melhor os argumentos ao edital e ao termo de referência',
            'habilitacao': 'falta enfrentar melhor o tema de habilitação ou capacidade técnica',
            'amostra_marca': 'falta tratar o ponto de marca, modelo, amostra ou equivalência',
        }
        rec = theme_map(recurso_text)
        con = theme_map(contrarrazao_text)
        missing = []
        for key, hits in rec.items():
            if hits > 0 and con.get(key, 0) == 0:
                missing.append(labels.get(key, key))
        return missing[:8]

    def _build_strengths(self, contrarrazao_text: str, notas: Dict[str, int]) -> List[str]:
        low = contrarrazao_text.lower()
        strengths: List[str] = []
        if notas['enfrentamento_do_recurso'] >= 8:
            strengths.append('A contrarrazão responde bem aos pontos centrais do recurso.')
        if notas['aderencia_ao_edital'] >= 7:
            strengths.append('Os argumentos têm boa conexão com o edital, o que ajuda muito na decisão do pregoeiro.')
        if notas['prova_e_lastro'] >= 7:
            strengths.append('A peça dá sinais de apoio em documentos ou elementos objetivos, e isso reduz a sensação de defesa genérica.')
        if 'dilig' in low:
            strengths.append('A defesa explica a diligência como etapa de esclarecimento, o que costuma fortalecer a argumentação.')
        if 'art. 165' in low or 'art. 64' in low or 'art. 59' in low:
            strengths.append('Há base legal identificável na Lei 14.133, o que deixa a peça mais segura.')
        if 'edital' in low and ('termo de referência' in low or 'termo de referencia' in low):
            strengths.append('A contrarrazão conversa com os documentos do certame em vez de ficar só em tese abstrata.')
        if not strengths:
            strengths.append('A peça tem uma linha de defesa organizada, mas ainda pede reforços.')
        return strengths[:8]

    def _build_weaknesses(self, *note_groups: List[str], contrarrazao_text: str | None = None) -> List[str]:
        weaknesses: List[str] = []
        for group in note_groups:
            weaknesses.extend(group)
        low = (contrarrazao_text or '').lower()
        if 'subsidiariamente' not in low and 'caso não' not in low and 'caso nao' not in low:
            weaknesses.append('Faltou um pedido alternativo para o caso de o julgador não acolher a tese principal.')
        if 'nota fiscal' not in low and 'pesquisa de mercado' not in low and 'planilha' not in low:
            weaknesses.append('Ainda há pouca ancoragem em prova material concreta.')
        dedup, seen = [], set()
        for item in weaknesses:
            if item not in seen:
                dedup.append(item)
                seen.add(item)
        return dedup[:10]

    def _build_recommendations(self, missing_arguments: List[str], contrarrazao_text: str) -> List[str]:
        recs: List[str] = []
        for item in missing_arguments[:5]:
            recs.append(f'Reforçar este ponto de forma expressa: {item}.')
        low = contrarrazao_text.lower()
        if 'planilha' not in low and 'composição de custos' not in low and 'composicao de custos' not in low:
            recs.append('Se existir, citar planilha, memória de cálculo ou composição de custos para dar mais lastro à defesa.')
        if 'subsidiariamente' not in low:
            recs.append('Adicionar um pedido subsidiário para reduzir risco caso a tese principal não seja acolhida.')
        if 'termo de referência' not in low and 'termo de referencia' not in low:
            recs.append('Amarrar mais a defesa ao termo de referência e às regras do edital.')
        return recs[:8]

    def _build_grade_explanations(self, notas: Dict[str, int]) -> Dict[str, str]:
        return {
            'estrutura': 'Mede se a peça está organizada e com começo, meio e fim claros.',
            'enfrentamento_do_recurso': 'Mede se a contrarrazão responde os pontos realmente atacados no recurso.',
            'prova_e_lastro': 'Mede se a defesa aponta documentos ou bases concretas, e não apenas tese.',
            'aderencia_ao_edital': 'Mede o quanto a defesa conversa com o edital e o termo de referência.',
            'base_legal': 'Mede a presença de base normativa útil na Lei 14.133.',
            'clareza_para_leigos': 'Mede se o texto pode ser entendido por quem não é advogado.',
            'solidez_geral': 'É a média consolidada dos principais pilares da defesa.',
        }

    def _who_is_stronger(self, recurso_text: str, contrarrazao_text: str, notas: Dict[str, int]) -> str:
        rec_themes = theme_map(recurso_text)
        con_themes = theme_map(contrarrazao_text)
        rec_strength = sum(1 for _, v in rec_themes.items() if v > 0)
        con_strength = notas['solidez_geral'] + sum(1 for _, v in con_themes.items() if v > 0)
        if con_strength - rec_strength >= 3:
            return 'Contrarrazão mais forte'
        if rec_strength - con_strength >= 3:
            return 'Recurso mais forte'
        return 'Disputa equilibrada'

    def _build_thesis_panel(self, recurso_text: str, contrarrazao_text: str, edital_text: str) -> List[Dict[str, str]]:
        rec = theme_map(recurso_text)
        con = theme_map(contrarrazao_text)
        edi = theme_map(edital_text)
        panel: List[Dict[str, str]] = []
        labels = {
            'inexequibilidade': 'Inexequibilidade / preço inexequível',
            'diligencia': 'Diligência e saneamento',
            'erro_material': 'Erro material / erro de cotação',
            'desistencia': 'Desistência / saída subsidiária',
            'prova': 'Prova material',
            'lotes': 'Separação por lotes / itens',
            'tempestividade': 'Tempestividade',
            'principios': 'Princípios da Lei 14.133',
            'pedido_subsidiario': 'Pedido subsidiário',
            'edital': 'Aderência ao edital',
            'habilitacao': 'Habilitação / capacidade técnica',
            'amostra_marca': 'Marca / modelo / amostra'
        }
        for key in THEMES.keys():
            if rec.get(key, 0) == 0 and con.get(key, 0) == 0 and edi.get(key, 0) == 0:
                continue
            if rec.get(key, 0) > 0 and con.get(key, 0) == 0:
                status = 'Não enfrentado'
                impacto = 'alto'
                leitura = 'O recurso levantou este ponto, mas a contrarrazão não respondeu com clareza.'
            elif rec.get(key, 0) > 0 and con.get(key, 0) > 0:
                status = 'Enfrentado'
                impacto = 'médio' if con.get(key, 0) < rec.get(key, 0) else 'baixo'
                leitura = 'O tema aparece no recurso e também foi enfrentado na contrarrazão.'
            else:
                status = 'Tema lateral'
                impacto = 'baixo'
                leitura = 'O tema não parece central no conflito, mas apareceu em algum dos documentos.'
            panel.append({
                'tese': labels.get(key, key),
                'status': status,
                'impacto': impacto,
                'leitura': leitura,
            })
        return panel

    def _build_summary(self, notas: Dict[str, int], missing_arguments: List[str], lotes: Dict[str, List[str]], mais_forte: str, lote_foco: str) -> str:
        parts = [
            f'Leitura técnica geral: {mais_forte}.',
            f'A contrarrazão ficou com {notas["solidez_geral"]}/10 em solidez geral e {notas["enfrentamento_do_recurso"]}/10 em resposta ao recurso.',
        ]
        overlap = set(lotes.get('recurso', [])).intersection(set(lotes.get('contrarrazao', [])))
        if lote_foco:
            parts.append(f'O usuário indicou foco no lote/item {lote_foco}.')
        if overlap:
            parts.append(f'Os documentos parecem discutir os mesmos lotes: {", ".join(sorted(overlap))}.')
        if missing_arguments:
            parts.append(f'Os pontos que mais pedem reforço são: {", ".join(missing_arguments[:3])}.')
        return ' '.join(parts)

    def _build_human_reading(self, notas: Dict[str, int], mais_forte: str, fragilidades: List[str], missing_arguments: List[str]) -> str:
        if mais_forte == 'Contrarrazão mais forte':
            abertura = 'Hoje, olhando de forma simples, a defesa parece estar em posição melhor do que o recurso.'
        elif mais_forte == 'Recurso mais forte':
            abertura = 'Hoje, em linguagem simples, o recurso parece pressionar mais do que a defesa consegue responder.'
        else:
            abertura = 'Hoje, em linguagem simples, a disputa parece equilibrada.'

        meio = (
            f'A defesa foi melhor em organização ({notas["estrutura"]}/10) e em resposta ao recurso ({notas["enfrentamento_do_recurso"]}/10). '
            f'Já os pontos que mais merecem atenção são prova documental ({notas["prova_e_lastro"]}/10) e clareza para quem não é do jurídico ({notas["clareza_para_leigos"]}/10).'
        )
        finais = []
        if fragilidades:
            finais.append(f'Em termos práticos, o principal risco é este: {fragilidades[0]}')
        if missing_arguments:
            finais.append(f'O primeiro ponto que eu reforçaria é: {missing_arguments[0]}.')
        finais.append('Em resumo: o sistema não dá decisão jurídica final, mas mostra onde a peça está convincente e onde ainda pode ser reforçada.')
        return ' '.join([abertura, meio] + finais)

    def _answer_user_question(self, pergunta: str, mais_forte: str, notas: Dict[str, int], fragilidades: List[str], missing: List[str], painel_teses: List[Dict[str, str]]) -> str:
        if not pergunta.strip():
            return 'Pergunta não informada. Mesmo assim, a leitura automática indica quem está mais forte, onde há risco e o que pode ser reforçado.'
        p = pergunta.lower()
        if 'chance' in p or 'êxito' in p or 'exito' in p:
            if mais_forte == 'Contrarrazão mais forte':
                return f'Pela leitura automática, a defesa parece ter melhor posição neste momento. Isso não garante resultado final, mas os sinais são positivos: solidez geral {notas["solidez_geral"]}/10 e resposta ao recurso {notas["enfrentamento_do_recurso"]}/10.'
            if mais_forte == 'Recurso mais forte':
                return f'Pela leitura automática, o recurso conseguiu pressionar pontos que a defesa ainda não respondeu bem. O foco deve ser reforçar {missing[0] if missing else "a prova e a aderência ao edital"}.'
        if 'respondeu' in p or 'enfrentou' in p:
            not_faced = [x['tese'] for x in painel_teses if x['status'] == 'Não enfrentado']
            if not not_faced:
                return 'Sim. Em leitura automática, a contrarrazão enfrentou os principais eixos identificados no recurso. O ganho agora é refinar prova e clareza.'
            return f'Parcialmente. A defesa respondeu boa parte do ataque, mas ainda há lacunas em: {", ".join(not_faced[:3])}.'
        if 'edital' in p:
            return f'A aderência ao edital ficou em {notas["aderencia_ao_edital"]}/10. Isso sugere que a peça conversa com o edital, mas ainda pode melhorar se amarrar mais regra, lote e pedido.'
        return f'Resposta direta: {mais_forte}. Em linguagem simples, os pontos que mais puxam o resultado são solidez {notas["solidez_geral"]}/10, resposta ao recurso {notas["enfrentamento_do_recurso"]}/10 e estas fragilidades: {fragilidades[0] if fragilidades else "nenhuma fragilidade importante detectada"}.'

    def _generate_reinforcement(self, painel_teses: List[Dict[str, str]], missing_arguments: List[str], recomendacoes: List[str]) -> str:
        nao_enfrentados = [x['tese'] for x in painel_teses if x['status'] == 'Não enfrentado']
        par1 = (
            'Em reforço à contrarrazão, convém destacar de forma objetiva que a análise da proposta não pode se apoiar em presunções genéricas, '
            'exigindo verificação concreta do caso, com confronto entre edital, documentos apresentados e realidade do certame.'
        )
        par2 = (
            'Também é recomendável deixar claro, em linguagem simples, qual foi a resposta dada a cada ataque central do recurso, '
            'separando tese, prova e pedido final. Isso ajuda o julgador a enxergar a defesa sem esforço adicional.'
        )
        extras = []
        if nao_enfrentados:
            extras.append('Pontos que merecem reforço expresso: ' + '; '.join(nao_enfrentados[:3]) + '.')
        if missing_arguments:
            extras.append('Lacunas detectadas pelo sistema: ' + '; '.join(missing_arguments[:3]) + '.')
        if recomendacoes:
            extras.append('Ajustes práticos sugeridos: ' + '; '.join(recomendacoes[:3]))
        return '\n\n'.join([par1, par2] + extras)

    def _generate_decision_draft(self, mais_forte: str, painel_teses: List[Dict[str, str]], lotes: Dict[str, List[str]], fragilidades: List[str]) -> str:
        overlap = sorted(set(lotes.get('recurso', [])).intersection(set(lotes.get('contrarrazao', []))))
        lotes_txt = ', '.join(overlap) if overlap else 'os lotes indicados nos autos'
        fundamentos = []
        for row in painel_teses[:4]:
            fundamentos.append(f"- {row['tese']}: {row['leitura']}")
        dispositivo = 'nego provimento ao recurso e mantenho a posição da contrarrazão' if mais_forte == 'Contrarrazão mais forte' else 'dou parcial provimento ao recurso para reavaliação dos pontos sensíveis' if mais_forte == 'Recurso mais forte' else 'determino reanálise técnica dos pontos controvertidos, sem conclusão automática nesta fase'
        texto = (
            'Vistos. Trata-se de análise recursal relativa ao pregão em referência. '\
            f'Após exame do edital, do recurso e da contrarrazão, especialmente quanto a {lotes_txt}, observo que os principais eixos controvertidos foram os seguintes:\n\n' +
            '\n'.join(fundamentos) +
            '\n\nConsiderando a necessidade de julgamento objetivo, aderência ao edital e apreciação concreta dos argumentos e documentos, concluo, nesta minuta automática, que ' +
            dispositivo + '. '
        )
        if fragilidades:
            texto += f'Registra-se, por cautela, que ainda merecem atenção os seguintes pontos: {fragilidades[0]}. '
        texto += 'Esta minuta é apenas um apoio de trabalho e deve ser ajustada pelo responsável pelo julgamento.'
        return texto


def result_to_dict(result: AnalysisResult) -> Dict:
    return asdict(result)
