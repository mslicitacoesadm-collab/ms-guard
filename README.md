# LicitaGuard V1 — Analisador de Recurso x Contrarrazão x Edital

Sistema em Streamlit para análise técnica inicial de peças licitatórias com foco na Lei 14.133/2021.

## O que faz

- Recebe **Edital**, **Recurso** e **Contrarrazão** em PDF.
- Extrai o texto dos documentos.
- Identifica lotes, temas jurídicos, indícios probatórios e artigos citados.
- Compara a aderência da contrarrazão ao recurso e ao edital.
- Gera notas por eixo:
  - Estrutura
  - Enfrentamento do recurso
  - Aderência ao edital
  - Base legal
  - Prova/lastro
  - Risco do caso
- Permite subir um PDF auxiliar da Lei 14.133/2021 para consulta local durante a sessão.
- Exporta relatório em PDF.

## Observação importante

O sistema **não substitui análise jurídica profissional**. Ele é um copiloto técnico para triagem, revisão e reforço argumentativo.

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
streamlit run app.py
```

## Estrutura

```text
licita_guard_v1/
├── app.py
├── analyzer.py
├── report_export.py
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml
├── knowledge/
│   └── lei_14133_base.json
└── utils/
    ├── pdf_utils.py
    └── text_rules.py
```

## Como usar

1. Abra o sistema.
2. Faça upload do **Edital**, **Recurso** e **Contrarrazão**.
3. Opcionalmente, envie um PDF de apoio da Lei 14.133/2021.
4. Clique em **Analisar documentos**.
5. Revise o painel técnico e exporte o relatório em PDF.

## Melhorias futuras sugeridas

- Histórico de casos por cliente
- Banco de teses reutilizáveis
- Módulo de geração de reforço argumentativo
- Módulo de minuta de decisão do pregoeiro
- Integração opcional com API de LLM

## Licença

Uso interno / privado. Ajuste conforme seu projeto comercial.
