from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from analyzer import LicitacaoAnalyzer, result_to_dict
from history_store import HistoryStore
from report_export import build_pdf_report
from utils.pdf_utils import extract_text_from_pdf

st.set_page_config(page_title='MS Licitações IA', page_icon='⚖️', layout='wide')

CUSTOM_CSS = """
<style>
.block-container {padding-top: 1rem; padding-bottom: 1rem; max-width: 1240px;}
.hero-shell {background:linear-gradient(135deg,#07162a 0%,#0d2f57 55%,#0ea5e9 100%);border-radius:28px;padding:28px 28px 24px 28px;color:white;box-shadow:0 14px 40px rgba(2,8,23,.18)}
.hero-badge {display:inline-block;padding:7px 12px;border-radius:999px;background:rgba(255,255,255,.12);font-size:12px;font-weight:700;letter-spacing:.2px}
.hero-title {font-size:2.25rem;font-weight:800;margin:10px 0 8px 0}
.hero-text {font-size:1rem;line-height:1.55;max-width:900px;color:#e2e8f0}
.card {background:#fff;border:1px solid #e2e8f0;border-radius:22px;padding:18px;box-shadow:0 8px 26px rgba(15,23,42,.05)}
.metric-card {background:#fff;border:1px solid #e2e8f0;border-radius:20px;padding:16px;box-shadow:0 6px 22px rgba(15,23,42,.04);height:100%}
.metric-label {font-size:13px;color:#64748b;margin-bottom:8px}
.metric-value {font-size:30px;font-weight:800;color:#0f172a}
.kicker {font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.12em;font-weight:700}
.pill-good,.pill-mid,.pill-risk{display:inline-block;padding:8px 12px;border-radius:999px;font-weight:700;font-size:13px}
.pill-good{background:#ecfdf5;color:#047857}.pill-mid{background:#fffbeb;color:#b45309}.pill-risk{background:#fef2f2;color:#b91c1c}
.small-muted{color:#64748b;font-size:13px}
textarea, input {border-radius:14px !important;}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_resource
def get_analyzer() -> LicitacaoAnalyzer:
    return LicitacaoAnalyzer(knowledge_path=str(Path('knowledge') / 'lei_14133_base.json'))


def score_color(value: int) -> str:
    if value >= 8:
        return '#15803d'
    if value >= 5:
        return '#b45309'
    return '#b91c1c'


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


def render_list(title: str, items: list[str], empty: str) -> None:
    st.markdown(f'### {title}')
    if not items:
        st.info(empty)
        return
    for item in items:
        st.markdown(f'- {item}')


history = HistoryStore(path='data/history.json')

with st.sidebar:
    st.image('assets/logo.png', width=140)
    st.markdown('## MS Licitações IA')
    st.caption('Análise prática de edital, recurso e contrarrazão com linguagem humana.')
    edital_file = st.file_uploader('Edital (PDF)', type=['pdf'], key='edital')
    recurso_file = st.file_uploader('Recurso (PDF)', type=['pdf'], key='recurso')
    contrarrazao_file = st.file_uploader('Contrarrazão (PDF)', type=['pdf'], key='contrarrazao')
    lei_file = st.file_uploader('Base legal complementar (PDF, opcional)', type=['pdf'], key='lei')
    lote_foco = st.text_input('Lote ou item em foco', placeholder='Ex.: 07')
    pergunta_usuario = st.text_area(
        'Pergunta do usuário',
        placeholder='Ex.: A contrarrazão respondeu bem ao ataque de inexequibilidade?',
        height=100,
    )
    run_analysis = st.button('Analisar agora', use_container_width=True, type='primary')

hero_c1, hero_c2 = st.columns([4, 1.3])
with hero_c1:
    st.markdown(
        """
        <div class='hero-shell'>
            <span class='hero-badge'>Versão comercial V3</span>
            <div class='hero-title'>MS Licitações IA</div>
            <div class='hero-text'>
                Envie o <strong>Edital</strong>, o <strong>Recurso</strong> e a <strong>Contrarrazão</strong>. O sistema compara o ataque e a defesa,
                cruza com a base jurídica da Lei 14.133, traduz o resultado para uma linguagem clara e ainda gera reforço da contrarrazão,
                minuta de decisão do pregoeiro e histórico das análises.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with hero_c2:
    st.markdown(
        """
        <div class='card'>
            <div class='kicker'>O que esta versão entrega</div>
            <p><strong>• Histórico de análises</strong><br/>
            <strong>• Painel por tese jurídica</strong><br/>
            <strong>• Resposta automática</strong><br/>
            <strong>• Reforço da contrarrazão</strong><br/>
            <strong>• Minuta do pregoeiro</strong></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.info('A análise é um apoio técnico. Ela não substitui a revisão de advogado, mas ajuda a enxergar forças, riscos e lacunas com muito mais velocidade.')

if not run_analysis:
    a, b, c = st.columns(3)
    with a:
        st.markdown("<div class='card'><h3>Linguagem humana</h3><p>O resultado sai em português claro, pensado para empresário, vendedor e equipe comercial.</p></div>", unsafe_allow_html=True)
    with b:
        st.markdown("<div class='card'><h3>Leitura do caso real</h3><p>O sistema não usa peças antigas como base fixa. Ele lê o que o cliente enviou no caso concreto.</p></div>", unsafe_allow_html=True)
    with c:
        st.markdown("<div class='card'><h3>Uso comercial</h3><p>Gera relatório, reforço sugerido e minuta de decisão para acelerar análise e posicionamento.</p></div>", unsafe_allow_html=True)

    hist = history.load()
    st.markdown('## Histórico recente')
    if hist:
        df_hist = pd.DataFrame(hist[:8])
        st.dataframe(df_hist[['data', 'quem_esta_mais_forte', 'solidez_geral', 'risco_geral', 'lote_foco']], use_container_width=True, hide_index=True)
    else:
        st.caption('Ainda não há análises salvas neste ambiente.')
    st.stop()

if not edital_file or not recurso_file or not contrarrazao_file:
    st.error('Envie obrigatoriamente os três documentos: edital, recurso e contrarrazão.')
    st.stop()

with st.spinner('Lendo os documentos e comparando os argumentos...'):
    edital_doc = extract_text_from_pdf(edital_file.read(), edital_file.name)
    recurso_doc = extract_text_from_pdf(recurso_file.read(), recurso_file.name)
    contrarrazao_doc = extract_text_from_pdf(contrarrazao_file.read(), contrarrazao_file.name)
    lei_text = None
    if lei_file:
        lei_doc = extract_text_from_pdf(lei_file.read(), lei_file.name)
        lei_text = lei_doc.text

    analyzer = get_analyzer()
    result = analyzer.analyze(
        edital_doc,
        recurso_doc,
        contrarrazao_doc,
        lei_pdf_text=lei_text,
        pergunta_usuario=pergunta_usuario,
        lote_foco=lote_foco,
    )
    result_dict = result_to_dict(result)

history.add({
    'data': datetime.now().strftime('%d/%m/%Y %H:%M'),
    'quem_esta_mais_forte': result.quem_esta_mais_forte,
    'solidez_geral': result.notas['solidez_geral'],
    'risco_geral': result.risco_geral,
    'lote_foco': lote_foco or '-',
})

st.success('Análise concluída com sucesso.')

if result.quem_esta_mais_forte == 'Contrarrazão mais forte':
    pill_class = 'pill-good'
elif result.quem_esta_mais_forte == 'Recurso mais forte':
    pill_class = 'pill-risk'
else:
    pill_class = 'pill-mid'

st.markdown(f"<span class='{pill_class}'>{result.quem_esta_mais_forte}</span>", unsafe_allow_html=True)
st.markdown('## Leitura rápida')
st.write(result.leitura_humana)

left, right = st.columns([1.2, 1])
with left:
    st.markdown('## Resumo executivo')
    st.write(result.resumo_executivo)
with right:
    st.markdown('## Resposta automática')
    st.write(result.resposta_automatica)

cols = st.columns(6)
helpers = result.explicacao_notas
keys = [
    ('Estrutura', 'estrutura'),
    ('Resposta ao recurso', 'enfrentamento_do_recurso'),
    ('Prova', 'prova_e_lastro'),
    ('Edital', 'aderencia_ao_edital'),
    ('Base legal', 'base_legal'),
    ('Clareza', 'clareza_para_leigos'),
]
for col, (label, key) in zip(cols, keys):
    with col:
        render_score_card(label, result.notas[key], helpers[key])

st.markdown('### Solidez geral')
render_score_card('Força técnica consolidada', result.notas['solidez_geral'], helpers['solidez_geral'])


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    'Visão prática', 'Painel por tese', 'Reforço e minuta', 'Base técnica', 'Histórico'
])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        render_list('Pontos fortes', result.pontos_fortes, 'Nenhum ponto forte foi identificado automaticamente.')
        render_list('O que melhorar', result.recomendacoes, 'Sem recomendações automáticas.')
    with c2:
        render_list('Fragilidades', result.fragilidades, 'Nenhuma fragilidade relevante foi detectada.')
        render_list('Pontos do recurso que ainda pedem resposta', result.argumentos_nao_enfrentados, 'O sistema não encontrou lacunas importantes de resposta.')

with tab2:
    st.markdown('### Painel por tese jurídica')
    if result.painel_teses:
        df = pd.DataFrame(result.painel_teses)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info('Nenhuma tese jurídica relevante foi identificada automaticamente.')

with tab3:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('### Gerador de reforço da contrarrazão')
        st.text_area('Texto sugerido', value=result.reforco_contrarrazao, height=320)
    with c2:
        st.markdown('### Minuta de decisão do pregoeiro')
        st.text_area('Minuta automática', value=result.minuta_decisao, height=320)

with tab4:
    st.markdown('### Artigos encontrados')
    st.json(result.artigos_identificados)
    st.markdown('### Trechos puxados automaticamente')
    for titulo, trecho in result.trechos_relevantes.items():
        with st.expander(titulo.replace('_', ' ').title()):
            st.write(trecho or 'O sistema não encontrou esse trecho de forma automática.')
    st.markdown('### Estatísticas básicas')
    df_docs = pd.DataFrame([
        {'documento': edital_doc.name, 'páginas': edital_doc.pages, 'caracteres': len(edital_doc.text), 'artigos': len(result.artigos_identificados['edital']), 'lotes': len(result.lotes_identificados['edital'])},
        {'documento': recurso_doc.name, 'páginas': recurso_doc.pages, 'caracteres': len(recurso_doc.text), 'artigos': len(result.artigos_identificados['recurso']), 'lotes': len(result.lotes_identificados['recurso'])},
        {'documento': contrarrazao_doc.name, 'páginas': contrarrazao_doc.pages, 'caracteres': len(contrarrazao_doc.text), 'artigos': len(result.artigos_identificados['contrarrazao']), 'lotes': len(result.lotes_identificados['contrarrazao'])},
    ])
    st.dataframe(df_docs, use_container_width=True, hide_index=True)

with tab5:
    hist = history.load()
    st.markdown('### Últimas análises salvas')
    if hist:
        st.dataframe(pd.DataFrame(hist), use_container_width=True, hide_index=True)
    else:
        st.caption('Ainda não há histórico salvo neste ambiente.')

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
pdf_bytes = build_pdf_report(result_dict, titulo=f'Relatório MS Licitações IA - {timestamp}')

c1, c2 = st.columns(2)
with c1:
    st.download_button(
        'Baixar relatório em PDF',
        data=pdf_bytes,
        file_name=f'relatorio_mslicitacoesia_{timestamp}.pdf',
        mime='application/pdf',
        use_container_width=True,
    )
with c2:
    st.download_button(
        'Baixar resultado em JSON',
        data=json.dumps(result_dict, ensure_ascii=False, indent=2).encode('utf-8'),
        file_name=f'resultado_mslicitacoesia_{timestamp}.json',
        mime='application/json',
        use_container_width=True,
    )
