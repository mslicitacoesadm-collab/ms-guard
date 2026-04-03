# MS Licitações IA - V3 Comercial

Sistema em Streamlit para comparar **Edital + Recurso + Contrarrazão** com leitura prática, visual profissional e linguagem humana.

## Principais recursos
- logo da marca integrada
- histórico de análises
- painel por tese jurídica
- resposta automática à pergunta do usuário
- gerador de reforço da contrarrazão
- minuta automática de decisão do pregoeiro
- exportação em PDF e JSON
- base jurídica neutra da Lei 14.133 em JSON

## Como rodar
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Estrutura
- `app.py`: interface principal
- `analyzer.py`: motor de análise
- `history_store.py`: histórico simples em JSON
- `knowledge/lei_14133_base.json`: base jurídica resumida
- `utils/pdf_utils.py`: leitura dos PDFs
- `utils/text_rules.py`: regras de tese, pontuação e clareza
- `report_export.py`: exportação do relatório PDF

## Observação
Ferramenta de apoio técnico. Não substitui revisão jurídica especializada.
