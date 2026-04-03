from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from analyzer import LicitacaoAnalyzer, result_to_dict
from report_export import build_pdf_report
from utils.pdf_utils import extract_text_from_pdf

st.set_page_config(page_title="LicitaGuard", page_icon="⚖️", layout="wide")

CUSTOM_CSS = """
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 1rem; max-width: 1200px;}
.main-shell {background: linear-gradient(180deg,#f8fafc 0%, #ffffff 100%); border:1px solid #e5e7eb; border-radius:24px; padding:24px;}
.hero {padding: 4px 0 14px 0;}
.hero-badge {display:inline-block;padding:6px 10px;border-radius:999px;background:#eef2ff;color:#4338ca;font-size:12px;font-weight:700;}
.hero h1 {font-size: 2.2rem; margin: 10px 0 6px 0; color:#0f172a;}
.hero p {font-size: 1rem; color:#475569; max-width: 850px;}
.metric-card {background:#ffffff;border:1px solid #e5e7eb;border-radius:20px;padding:16px;box-shadow:0 8px 24px rgba(15,23,42,.04);}
.metric-label {font-size:13px;color:#64748b;margin-bottom:6px;}
.metric-value {font-size:30px;font-weight:800;color:#0f172a;}
.panel {background:#fff;border:1px solid #e5e7eb;border-radius:20px;padding:18px;}
.panel h3 {margin-top:0; color:#0f172a;}
.tag-ok, .tag-mid, .tag-risk {display:inline-block;padding:8px 12px;border-radius:999px;font-weight:700;font-size:13px;}
.tag-ok {background:#ecfdf5;color:#047857;}
.tag-mid {background:#fffbeb;color:#b45309;}
.tag-risk {background:#fef2f2;color:#b91c1c;}
.small-muted {color:#64748b;font-size:13px;}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def score_color(value: int) -> str:
    if value >= 8:
        return "#15803d"
    if value >= 5:
        return "#b45309"
    return "#b91c1c"


def render_score_card(title: str, value: int, helper: str) -> None:
    st.markdown(
        f"""
        <div class='metric-card'>
            <div class='metric-label'>{title}</div>
            <div class='metric-value' style='color:{score_color(value)}'>{value}/10</div>
            <div class='small-muted'>{helper}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_bullets(title: str, items: list[str], empty: str) -> None:
    st.markdown(f"### {title}")
    if not items:
        st.info(empty)
        return
    for item in items:
        st.markdown(f"- {item}")


with st.sidebar:
    st.header("Entrada dos documentos")
    edital_file = st.file_uploader("Edital (PDF)", type=["pdf"], key="edital")
    recurso_file = st.file_uploader("Recurso (PDF)", type=["pdf"], key="recurso")
    contrarrazao_file = st.file_uploader("Contrarrazão (PDF)", type=["pdf"], key="contrarrazao")
    lei_file = st.file_uploader("Base legal complementar (PDF, opcional)", type=["pdf"], key="lei")

    st.markdown("---")
    lote_foco = st.text_input("Lote ou item em foco", placeholder="Ex.: 07")
    pergunta_usuario = st.text_area(
        "O que você quer descobrir?",
        placeholder="Ex.: A defesa respondeu bem ao ataque de inexequibilidade?",
        height=110,
    )
    run_analysis = st.button("Analisar agora", use_container_width=True, type="primary")

st.markdown("<div class='main-shell'>", unsafe_allow_html=True)
st.markdown(
    """
    <div class='hero'>
        <span class='hero-badge'>Leitura técnica com linguagem humana</span>
        <h1>LicitaGuard</h1>
        <p>
            Compare <strong>Edital</strong>, <strong>Recurso</strong> e <strong>Contrarrazão</strong> em um só lugar.
            O sistema organiza a leitura, mede a força da defesa e traduz o resultado para uma linguagem mais simples,
            útil para quem não domina o jurídico.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "Este sistema não usa peças prontas como base fixa. Ele lê os PDFs enviados no caso concreto, cruza os argumentos com a base legal interna da Lei 14.133 e devolve uma análise técnica em linguagem acessível."
)

if not run_analysis:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='panel'><h3>O que ele faz</h3><p>Compara o que o recurso atacou com o que a contrarrazão realmente respondeu.</p></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='panel'><h3>O que ele mede</h3><p>Estrutura, aderência ao edital, prova, base legal, clareza e risco geral.</p></div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='panel'><h3>O que ele entrega</h3><p>Resumo executivo, leitura humana, pontos fortes, fragilidades e relatório em PDF.</p></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

if not edital_file or not recurso_file or not contrarrazao_file:
    st.error("Envie obrigatoriamente os três documentos: edital, recurso e contrarrazão.")
    st.stop()

with st.spinner("Lendo os arquivos e cruzando as informações..."):
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

st.success("Análise concluída com sucesso.")

if result.quem_esta_mais_forte == "Contrarrazão mais forte":
    tag_class = "tag-ok"
elif result.quem_esta_mais_forte == "Recurso mais forte":
    tag_class = "tag-risk"
else:
    tag_class = "tag-mid"

st.markdown(f"<span class='{tag_class}'>{result.quem_esta_mais_forte}</span>", unsafe_allow_html=True)

st.markdown("## Leitura rápida")
st.write(result.leitura_humana)

st.markdown("## Resumo executivo")
st.write(result.resumo_executivo)

if lote_foco:
    st.caption(f"Lote ou item informado pelo usuário: {lote_foco}")
if pergunta_usuario:
    st.caption(f"Pergunta registrada: {pergunta_usuario}")

cols = st.columns(6)
helpers = result.explicacao_notas
keys = [
    ("Estrutura", "estrutura"),
    ("Resposta ao recurso", "enfrentamento_do_recurso"),
    ("Prova", "prova_e_lastro"),
    ("Edital", "aderencia_ao_edital"),
    ("Base legal", "base_legal"),
    ("Clareza", "clareza_para_leigos"),
]
for col, (label, key) in zip(cols, keys):
    with col:
        render_score_card(label, result.notas[key], helpers[key])

st.markdown("### Solidez geral")
render_score_card("Força técnica consolidada", result.notas["solidez_geral"], helpers["solidez_geral"])

tab1, tab2, tab3 = st.tabs(["Visão prática", "Base técnica", "Dados dos documentos"])

with tab1:
    left, right = st.columns(2)
    with left:
        render_bullets("Pontos fortes", result.pontos_fortes, "Nenhum ponto forte foi identificado automaticamente.")
        render_bullets("O que melhorar", result.recomendacoes, "Sem recomendações automáticas.")
    with right:
        render_bullets("Fragilidades", result.fragilidades, "Nenhuma fragilidade relevante foi detectada.")
        render_bullets("Pontos do recurso que ainda pedem resposta", result.argumentos_nao_enfrentados, "O sistema não encontrou lacunas importantes de resposta.")

with tab2:
    st.markdown("### Artigos encontrados")
    st.json(result.artigos_identificados)

    st.markdown("### Trechos puxados automaticamente")
    for titulo, trecho in result.trechos_relevantes.items():
        with st.expander(titulo.replace("_", " ").title()):
            st.write(trecho or "O sistema não encontrou esse trecho de forma automática.")

with tab3:
    st.markdown("### Estatísticas básicas")
    df = pd.DataFrame([
        {"documento": edital_doc.name, "páginas": edital_doc.pages, "caracteres": len(edital_doc.text), "artigos": len(result.artigos_identificados["edital"]), "lotes": len(result.lotes_identificados["edital"])},
        {"documento": recurso_doc.name, "páginas": recurso_doc.pages, "caracteres": len(recurso_doc.text), "artigos": len(result.artigos_identificados["recurso"]), "lotes": len(result.lotes_identificados["recurso"])},
        {"documento": contrarrazao_doc.name, "páginas": contrarrazao_doc.pages, "caracteres": len(contrarrazao_doc.text), "artigos": len(result.artigos_identificados["contrarrazao"]), "lotes": len(result.lotes_identificados["contrarrazao"])}
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.markdown("### Lotes e itens identificados")
    st.json(result.lotes_identificados)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
pdf_bytes = build_pdf_report(result_dict, titulo=f"Relatório LicitaGuard - {timestamp}")

c1, c2 = st.columns(2)
with c1:
    st.download_button(
        "Baixar relatório em PDF",
        data=pdf_bytes,
        file_name=f"relatorio_licitaguard_{timestamp}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
with c2:
    st.download_button(
        "Baixar resultado em JSON",
        data=json.dumps(result_dict, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name=f"resultado_licitaguard_{timestamp}.json",
        mime="application/json",
        use_container_width=True,
    )

st.markdown("</div>", unsafe_allow_html=True)
