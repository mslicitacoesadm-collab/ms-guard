# LicitaGuard V2 Clean

Sistema em Streamlit para comparar **Edital + Recurso + Contrarrazão** com foco em:
- aderência ao edital
- resposta efetiva ao recurso
- base legal da Lei 14.133/2021
- leitura simples para usuários não jurídicos

## O que mudou nesta versão
- interface mais limpa e profissional
- linguagem final mais humana
- sem peças-modelo embutidas
- base jurídica neutra em JSON
- leitura centrada no caso concreto enviado pelo usuário
- relatório em PDF com resumo executivo e leitura simples

## Como rodar
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Estrutura
- `app.py`: interface Streamlit
- `analyzer.py`: motor de análise
- `knowledge/lei_14133_base.json`: base legal neutra e resumida
- `utils/pdf_utils.py`: leitura de PDF
- `utils/text_rules.py`: regras de análise textual
- `report_export.py`: exportação do relatório

## Observação importante
Este sistema é uma ferramenta de apoio e triagem técnica. Ele **não substitui** a revisão de um advogado ou consultor especializado.
