from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from analyzer import LicitacaoAnalyzer, result_to_dict
from report_export import build_pdf_report
from utils.pdf_utils import extract_text_from_pdf


st.set_page_config(page_title="LicitaGuard V1", page_icon="⚖️", layout="wide")


def score_color(value: int) -> str:
    if value >= 8:
        return "#16a34a"
    if value >= 5:
        return "#d97706"
    return "#dc2626"


def render_score_card(title: str, value: int) -> None:
    color = score_color(value)
    st.markdown(
        f"""
        <div style='padding:16px;border-radius:18px;background:#F6F7FB;border:1px solid #E5E7EB;'>
            <div style='font-size:14px;color:#6B7280;margin-bottom:6px;'>{title}</div>
            <div style='font-size:30px;font-weight:700;color:{color};'>{value}/10</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_list(title: str, items: list[str], empty_text: str = "Nenhum item identificado.") -> None:
    st.markdown(f"### {title}")
    if not items:
        st.info(empty_text)
        return
    for item in items:
        st.markdown(f"- {item}")


st.title("⚖️ LicitaGuard V1")
st.caption("Analisador técnico de Edital × Recurso × Contrarrazão com foco na Lei 14.133/2021")

with st.sidebar:
    st.header("Arquivos")
    edital_file = st.file_uploader("Edital (PDF)", type=["pdf"], key="edital")
    recurso_file = st.file_uploader("Recurso (PDF)", type=["pdf"], key="recurso")
    contrarrazao_file = st.file_uploader("Contrarrazão (PDF)", type=["pdf"], key="contrarrazao")
    lei_file = st.file_uploader("Lei 14.133 / material auxiliar (PDF, opcional)", type=["pdf"], key="lei")

    lote_foco = st.text_input("Lote em foco (opcional)", placeholder="Ex.: 07")
    pergunta_usuario = st.text_area(
        "Pergunta estratégica (opcional)",
        placeholder="Ex.: A contrarrazão enfrenta bem a tese de inexequibilidade?",
        height=100,
    )

    run_analysis = st.button("Analisar documentos", use_container_width=True, type="primary")

st.markdown(
    """
    Este sistema faz uma **triagem técnica inicial**: extrai texto dos PDFs, identifica lotes, temas, artigos, lastro probatório e confronto entre as peças.  
    O resultado serve como base de revisão jurídica e fortalecimento da defesa.
    """
)

if run_analysis:
    if not edital_file or not recurso_file or not contrarrazao_file:
        st.error("Envie obrigatoriamente o Edital, o Recurso e a Contrarrazão em PDF.")
        st.stop()

    with st.spinner("Lendo PDFs e executando análise..."):
        edital_doc = extract_text_from_pdf(edital_file.read(), edital_file.name)
        recurso_doc = extract_text_from_pdf(recurso_file.read(), recurso_file.name)
        contrarrazao_doc = extract_text_from_pdf(contrarrazao_file.read(), contrarrazao_file.name)
        lei_text = None
        if lei_file:
            lei_doc = extract_text_from_pdf(lei_file.read(), lei_file.name)
            lei_text = lei_doc.text

        analyzer = LicitacaoAnalyzer(knowledge_path=str(Path("knowledge") / "lei_14133_base.json"))
        result = analyzer.analyze(edital_doc, recurso_doc, contrarrazao_doc, lei_pdf_text=lei_text)
        result_dict = result_to_dict(result)

    st.success("Análise concluída.")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        render_score_card("Estrutura", result.notas["estrutura"])
    with c2:
        render_score_card("Enfrentamento", result.notas["enfrentamento_do_recurso"])
    with c3:
        render_score_card("Prova", result.notas["prova_e_lastro"])
    with c4:
        render_score_card("Edital", result.notas["aderencia_ao_edital"])
    with c5:
        render_score_card("Base legal", result.notas["base_legal"])
    with c6:
        render_score_card("Solidez geral", result.notas["solidez_geral"])

    st.markdown("## Resumo executivo")
    st.write(result.resumo_executivo)

    if lote_foco:
        st.info(f"Lote em foco informado pelo usuário: {lote_foco}")
    if pergunta_usuario:
        st.markdown("### Pergunta estratégica do usuário")
        st.write(pergunta_usuario)
        st.markdown("### Leitura automática frente à pergunta")
        if "inexequ" in pergunta_usuario.lower() and "inexequ" in (recurso_doc.text + contrarrazao_doc.text).lower():
            st.write("O tema de inexequibilidade aparece nos documentos enviados e foi levado em conta na comparação automática.")
        else:
            st.write("A pergunta foi registrada, mas a V1 ainda não faz resposta redacional específica por pergunta. Ela usa a pergunta como orientação visual para a revisão humana.")

    t1, t2 = st.tabs(["Parecer técnico", "Base documental"])

    with t1:
        col_a, col_b = st.columns(2)
        with col_a:
            render_list("Pontos fortes", result.pontos_fortes)
            render_list("Argumentos não enfrentados", result.argumentos_nao_enfrentados, "A comparação automática não encontrou lacunas relevantes.")
        with col_b:
            render_list("Fragilidades", result.fragilidades)
            render_list("Recomendações", result.recomendacoes)

        st.markdown("### Risco geral")
        risco_cor = {"baixo": "#16a34a", "médio": "#d97706", "alto": "#dc2626"}.get(result.risco_geral, "#374151")
        st.markdown(
            f"<div style='padding:12px 16px;background:#F9FAFB;border:1px solid #E5E7EB;border-radius:14px;'>"
            f"<strong style='color:{risco_cor};text-transform:uppercase;'>Risco {result.risco_geral}</strong>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with t2:
        st.markdown("### Artigos identificados")
        st.json(result.artigos_identificados)

        st.markdown("### Lotes identificados")
        st.json(result.lotes_identificados)

        st.markdown("### Trechos relevantes")
        for titulo, trecho in result.trechos_relevantes.items():
            with st.expander(titulo.replace("_", " ").title()):
                st.write(trecho or "Trecho não localizado automaticamente.")

        st.markdown("### Estatísticas básicas")
        df = pd.DataFrame(
            [
                {"documento": edital_doc.name, "paginas": edital_doc.pages, "caracteres": len(edital_doc.text), "artigos": len(result.artigos_identificados["edital"]), "lotes": len(result.lotes_identificados["edital"])} ,
                {"documento": recurso_doc.name, "paginas": recurso_doc.pages, "caracteres": len(recurso_doc.text), "artigos": len(result.artigos_identificados["recurso"]), "lotes": len(result.lotes_identificados["recurso"])} ,
                {"documento": contrarrazao_doc.name, "paginas": contrarrazao_doc.pages, "caracteres": len(contrarrazao_doc.text), "artigos": len(result.artigos_identificados["contrarrazao"]), "lotes": len(result.lotes_identificados["contrarrazao"])} ,
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_bytes = build_pdf_report(result_dict, titulo=f"Relatório Técnico LicitaGuard - {timestamp}")

    col_d1, col_d2 = st.columns([1, 1])
    with col_d1:
        st.download_button(
            label="Baixar relatório em PDF",
            data=pdf_bytes,
            file_name=f"relatorio_licitaguard_{timestamp}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with col_d2:
        st.download_button(
            label="Baixar resultado em JSON",
            data=json.dumps(result_dict, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=f"resultado_licitaguard_{timestamp}.json",
            mime="application/json",
            use_container_width=True,
        )
else:
    st.info("Envie os arquivos no menu lateral e clique em **Analisar documentos**.")
    st.markdown("## O que esta versão já entrega")
    st.markdown(
        """
- comparação técnica entre recurso e contrarrazão
- aderência da defesa ao edital
- leitura de lotes e artigos citados
- detecção de tese de inexequibilidade, diligência, erro material, desistência e lastro probatório
- relatório para download em PDF e JSON
        """
    )
