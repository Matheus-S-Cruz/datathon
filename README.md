# Pulso Industry

**Decisões inteligentes para uma indústria mais forte.** Painel de inteligência sobre o mercado de
trabalho industrial de Santa Catarina — solução da equipe para o desafio *Raio-X do Mercado de
Trabalho e Vagas Industriais em Santa Catarina*.

Projeto da equipe para o **Datathon CDIA 2026 — UniSENAI** (Bacharelado em Ciência de Dados e IA).
Atuando como uma consultoria de dados, transformamos os microdados do **Novo CAGED** em um painel de
inteligência territorial e setorial para a indústria catarinense.

> **Pergunta central de negócio**
> "Quais regiões e setores industriais de Santa Catarina estão enfrentando **apagão de mão de obra**
> ou **expansão acelerada**, e como os indicadores de **renda e escolaridade** explicam esses gargalos?"

O projeto cruza 3,4 milhões de admissões e desligamentos em SC (declarados de set/2025 a ago/2026)
com os dados dos 295 municípios e com **bases públicas do IBGE**: estoque de emprego formal (CEMPRE),
PIB dos Municípios, divisão regional e malha municipal. Também agrupa as ocupações (CBO) em
macrofamílias.

## Status

| Entregável / etapa | Situação |
|---|---|
| Auditoria do repositório e perfil das bases | ✅ [`docs/diagnostico_inicial.md`](docs/diagnostico_inicial.md) |
| **1. Pipeline** (notebook) | ✅ [`notebooks/01_pipeline_caged_sc.ipynb`](notebooks/01_pipeline_caged_sc.ipynb) |
| Enriquecimento com bases públicas (IBGE) | ✅ [`src/enrichment/ibge.py`](src/enrichment/ibge.py) → `data/external/` |
| **2. Dashboard** (Streamlit) | ✅ `dashboard/` — painel executivo + explorador + análises |
| Agrupamento de CBOs com IA | ✅ baseline determinístico; refino por LLM opcional (`OPENAI_API_KEY`) |
| **3. Pitch** (3 min) | ⏳ |

Checklist completo em [`ENTREGAVEIS.md`](ENTREGAVEIS.md).

## Dashboard

Organizado em **três seções** no menu lateral:

| Seção | Páginas | Para que serve |
|---|---|---|
| **Visão geral** | Painel executivo | 5 indicadores-chave e os 6 gráficos que respondem à pergunta central: mapa coroplético, regiões (crescimento × rotatividade), setores, macrofamílias na indústria, salário por escolaridade e dispersão renda × escolaridade. |
| **Exploração e consulta** | Explorador do Novo CAGED · Municípios · Tabelas analíticas · Dicionário de dados · Bases e validação | Filtros, tabelas paginadas, registro individual, exportação CSV, dicionário pesquisável, tabelas do pipeline e do IBGE para download. |
| **Análises complementares** | Território · Setores · Renda e escolaridade · Macrofamílias · Contexto regional (IBGE) · Exploração estatística · Relações · Auditoria | Os demais gráficos do projeto, para aprofundar sem poluir a visão geral. |

Os filtros das páginas analíticas (só indústria, seções CNAE, região intermediária do IBGE,
população mínima) ficam na barra lateral e acompanham a navegação entre páginas. Os temas claro e
escuro seguem o sistema. Como usar cada página: [`docs/guia_explorador.md`](docs/guia_explorador.md).

## Como rodar

**Pré-requisito:** Python 3.10+ (testado com 3.14). Todos os dados já estão no repositório.

```bash
git clone https://github.com/Matheus-S-Cruz/datathon.git
cd datathon
python -m venv .venv
# Windows (PowerShell): .\.venv\Scripts\Activate.ps1   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
streamlit run dashboard/app.py
```

Acesse **<http://localhost:8501>**. Depois de instalado, o dashboard funciona **sem internet**: as
bases do IBGE estão versionadas em `data/external/`. Só o mapa de fundo do mapa de bolhas
(página Território) e a fonte Inter precisam de rede; sem ela, as bolhas e uma fonte do sistema
aparecem no lugar.

> **Windows — erro ao ativar o ambiente?** Rode uma vez:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

### Reexecutar o pipeline (opcional)

As tabelas em `outputs/` já estão versionadas. Para regerá-las:

```bash
python notebooks/_build_notebook.py        # regera o .ipynb a partir do código-fonte
jupyter nbconvert --to notebook --execute --inplace notebooks/01_pipeline_caged_sc.ipynb
```

Para atualizar as bases do IBGE (precisa de internet):

```bash
python -m src.enrichment.ibge
```

### Testes

```bash
python -m pytest tests/test_analytics.py -q       # tabelas do pipeline + IBGE (~5 s)
python -m unittest tests.test_services -v         # camada DuckDB (~15 s)
python -m unittest tests.test_app_pages -v        # renderiza as 14 páginas sem navegador (~8 min)
```

## Metodologia (resumo)

1. **Ingestão e validação** das três bases + dicionário de códigos (DuckDB sobre o Parquet).
2. **Limpeza e tipagem** (salário com vírgula decimal, idade, códigos com zero à esquerda).
3. **Join** CAGED × municípios pelo código de 6 dígitos (o IBGE usa 7, com dígito verificador).
4. **Métricas:** saldo, **saldo por 10 mil habitantes** (métrica do guia), giro, escolaridade em
   **escala ordinal 1–12** e **% com superior completo**.
5. **Enriquecimento com o IBGE:** **crescimento do emprego formal** (saldo ÷ assalariados do CEMPRE
   2024), **taxa de rotatividade** (mín(admissões, desligamentos) ÷ estoque, conceito do DIEESE),
   peso da indústria no VAB e agregação por **regiões geográficas** oficiais.
6. **Macrofamílias:** os 2.207 CBOs agrupados pelo Grande Grupo da CBO-2002, com refino opcional por LLM.
7. **Exportação** das tabelas-base em `outputs/` para o dashboard.

## Principais achados

- **Gargalo de qualificação na indústria:** nas seções B, C, D e F, o saldo é **negativo** entre
  técnicos de nível médio (−2.782), dirigentes e gerentes (−1.955) e profissionais de nível superior
  (−1.052), enquanto a base operacional cresce (+6.232).
- **Expansão regional:** Caçador (+2,44%) e Florianópolis (+2,12%) lideram o crescimento do emprego
  formal sobre o estoque; Criciúma tem o menor (+0,43%).
- **Reposição:** Caçador e Blumenau têm as maiores rotatividades (~70% e ~69%): muita troca de
  trabalhadores.
- **Renda × escolaridade:** o salário médio quase não muda do analfabeto ao médio completo
  (R$ 2.076 a R$ 2.354) e salta no superior completo (R$ 3.990).

> **Limites:** o CAGED mede fluxo, não estoque; as taxas sobre o CEMPRE 2024 são aproximações (o
> CEMPRE municipal não é aberto por setor, por isso essas taxas não aparecem com recorte setorial);
> o VAB por atividade municipal mais recente é de 2021; o IDHM é de 2010; salários declarados podem
> conter valores extremos.

## Dados

| Base | Arquivo | Fonte |
|---|---|---|
| Novo CAGED — movimentações SC | `data/raw/Novo_Caged_MOV_Limpo.parquet` | Organização do Datathon (MTE) — 3.397.416 registros |
| Municípios de SC | `data/reference/Municipios_SC_limpo.csv` | Organização (IBGE, PNUD, DATASUS, Siconfi) — 295 municípios |
| Dicionário de dados | `data/reference/Dicionario_de_dados.xlsx` | Layout oficial do Novo CAGED — 23 abas |
| Centroides dos municípios | `data/reference/municipios_sc_coords.parquet` | Malha IBGE via [geodata-br](https://github.com/tbrugz/geodata-br) |
| CEMPRE 2024 | `data/external/ibge_cempre_2024.parquet` | IBGE, SIDRA tabela 9509 |
| PIB dos Municípios | `data/external/ibge_pib_municipal.parquet` | IBGE, SIDRA tabela 5938 (PIB 2023; VAB por atividade 2021) |
| Divisão regional | `data/external/ibge_regioes_sc.parquet` | IBGE, API de Localidades |
| Malha municipal | `data/external/ibge_malha_sc.geojson` | IBGE, API de Malhas v3 |

O CSV original do CAGED (~395 MB) **não é versionado** por causa do limite de 100 MB do GitHub; o
Parquet tem os mesmos dados. Origem, formato e cuidados de leitura: [`data/README.md`](data/README.md).

## Estrutura

```text
.streamlit/config.toml       # tema (claro/escuro), sem telemetria
context/                     # regras do desafio (Guia do Participante; .docx e .pptx originais)
dashboard/
  app.py                     # ponto de entrada: menu com as 3 seções
  views/                     # uma página por arquivo (00_painel, 01–07 explorador, 10–15 análises)
  components/                # interface: cards, KPIs, filtros, tabelas, gráficos
  services/                  # dados: DuckDB (explorador) e analytics (pipeline + IBGE)
  assets/                    # logotipo
data/
  raw/ · reference/          # bases do desafio (ver data/README.md)
  external/                  # bases públicas do IBGE (versionadas)
notebooks/                   # Entregável 1 — pipeline (+ gerador _build_notebook.py)
outputs/                     # tabelas-base geradas pelo pipeline (consumidas pelo painel)
docs/ · reports/             # diagnóstico, dicionário analítico, plano, guia, perfil das bases
src/
  config.py                  # caminhos do projeto
  enrichment/ibge.py         # download das bases do IBGE
  validation/profile_sources.py
tests/
requirements.txt
```

## Regras do repositório

- Não versionar CSVs pesados, saídas de `data/processed/` nem credenciais (`.env`, chaves de API).
- Nunca editar arquivos em `data/raw/`; todo tratamento fica no código.
- Documentos em português; código, pastas e módulos em inglês.

## Tecnologias

Python · DuckDB · PyArrow/Parquet · pandas · Jupyter · Streamlit · Plotly · APIs do IBGE (SIDRA,
Localidades, Malhas)
