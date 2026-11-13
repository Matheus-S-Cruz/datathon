# Dashboard — Pulso Industry (Entregável 2)

Identidade visual em `assets/`: logo (`logo_light.svg` / `logo_dark.svg`, conforme o tema), símbolo
(`icon.svg`, também usado como ícone da aba) e avatar circular do Assistente Pulso (`assistant_avatar.svg`).

Painel em **Streamlit** que responde à pergunta central do desafio. Execute a partir da raiz:

```bash
pip install -r requirements.txt
streamlit run dashboard/app.py      # http://localhost:8501
```

## Organização

| Seção | Página | Dados |
|---|---|---|
| **Visão geral** | Painel executivo — 5 KPIs + 6 gráficos essenciais e leituras calculadas | `outputs/` + `data/external/` |
| **Exploração e consulta** | Explorador do Novo CAGED (filtros, paginação, amostras, registro, CSV) | Parquet bruto via DuckDB |
| | Municípios · Dicionário de dados · Bases e validação | bases de `data/` |
| | Tabelas analíticas (pipeline e IBGE, com busca e download) | `outputs/` + `data/external/` |
| **Análises complementares** | Território · Setores · Renda e escolaridade · Macrofamílias · Contexto regional (IBGE) | `outputs/` + `data/external/` |
| | Exploração estatística · Relações · Resultados da auditoria | Parquet bruto via DuckDB |

### Painel executivo — gráficos essenciais

| Gráfico | Responde |
|---|---|
| Mapa coroplético (malha IBGE) — saldo por 10 mil hab. ou crescimento do emprego | **Onde** há expansão e retração |
| Regiões: crescimento do emprego × rotatividade | Expansão real ou **só reposição** |
| Saldo por seção CNAE, indústria em destaque | **Quais setores** |
| Saldo por macrofamília de CBO na indústria | Gargalo **operacional ou técnico** |
| Salário médio por grau de instrução | Quanto a **escolaridade** paga |
| Dispersão municipal salário × % com superior | **Renda × escolaridade** explicam o saldo? |

**KPIs:** saldo de vagas; saldo por 10 mil habitantes; crescimento do emprego formal (saldo ÷
assalariados CEMPRE 2024); taxa de rotatividade (conceito DIEESE); salário médio e % com superior.

### Filtros

Nas páginas analíticas, a barra lateral tem: **apenas setores industriais** (B, C, D, F), **seções
CNAE**, **região geográfica intermediária** (IBGE) e **população mínima**. O recorte acompanha a
navegação entre páginas. Com recorte setorial, as taxas sobre o estoque ficam indisponíveis: o
CEMPRE municipal não é aberto por setor. O Explorador mantém seu próprio formulário de filtros,
que só consulta ao clicar em *Aplicar filtros*.

## Identidade visual

- Tema claro/escuro em `.streamlit/config.toml`; cards, KPIs e cabeçalhos em `components/ui.py`.
- Paleta de gráficos em `components/charts.py`, validada para daltonismo: **azul = admissões/saldo
  positivo**, **laranja = desligamentos/saldo negativo**, escala divergente com meio cinza,
  magnitudes em uma única matiz. Nunca dois eixos Y.
- Números no padrão brasileiro (`formatting.py`).

## Código

```text
app.py                 # menu (st.navigation) com as 3 seções, logotipo e CSS
views/00_painel.py     # Visão geral
views/01–07_*.py       # Explorador do Novo CAGED e páginas de exploração/validação
views/10–15_*.py       # análises complementares e tabelas analíticas
components/            # ui (cards, KPIs), charts, filters, tables
services/analytics.py  # tabelas do pipeline + IBGE e recortes
services/queries.py    # consultas DuckDB das páginas de exploração
```
