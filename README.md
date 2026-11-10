# Raio-X do Mercado de Trabalho Industrial em Santa Catarina

Projeto da equipe para o **Datathon 2026** da Semana Acadêmica do UniSENAI (Bacharelado em
Ciência de Dados e IA).

> **Pergunta central de negócio**
> "Quais regiões e setores industriais de Santa Catarina estão enfrentando apagão de mão de obra
> ou expansão acelerada, e como os indicadores de renda e escolaridade explicam esses gargalos?"

Transformamos os microdados do **Novo CAGED** (3,4 milhões de admissões e desligamentos em SC,
set/2025 a ago/2026) em um painel de inteligência territorial e setorial, cruzando com dados
demográficos dos 295 municípios e agrupando ocupações (CBO) em macrofamílias com apoio de IA generativa.

## Status

| Etapa | Situação |
|---|---|
| Auditoria do repositório e perfil das bases | ✅ concluída — ver [`docs/diagnostico_inicial.md`](docs/diagnostico_inicial.md) |
| **CAGED Explorer** (exploração e validação dos dados) | ✅ concluído — ver [`docs/guia_explorador.md`](docs/guia_explorador.md) |
| Pipeline de tratamento | ⏳ aguardando validação das decisões metodológicas |
| Agrupamento de CBOs com IA | ⏳ |
| Dashboard executivo | ⏳ |
| Pitch | ⏳ |

## CAGED Explorer — Santa Catarina

Aplicação web para a equipe **ver, consultar e conferir** as bases antes da modelagem. Ela não é o
dashboard executivo final: não calcula índice de escassez nem classifica municípios.

| Página | Para que serve |
|---|---|
| Visão geral | Volumes (admissões, desligamentos, saldo), período, bases e situação da validação. |
| Explorador do Novo CAGED | Tabela paginada com pesquisa, filtros, ordenação, amostras, registro individual e exportação CSV. |
| Municípios | Os 295 municípios, valores ausentes, registro completo e gráficos de população, PIB per capita e IDHM. |
| Dicionário de dados | As 23 abas do dicionário, pesquisa de códigos e correspondência campo × coluna. |
| Resultados da auditoria | 31 constatações recalculadas dos arquivos e comparadas com a auditoria inicial. |
| Exploração estatística | Estatísticas descritivas, correlações de Pearson e Spearman e gráficos de dispersão. |
| Relações territoriais e setoriais | Agregações por município × CNAE × CBO × escolaridade × salário × competência. |

Como usar cada página: [`docs/guia_explorador.md`](docs/guia_explorador.md).

### Tecnologias

- **Streamlit**: interface web, em Python puro.
- **DuckDB**: consultas SQL direto sobre o Parquet, sem carregar os 3,4 milhões de linhas na memória.
- **Plotly**: gráficos interativos.
- **Pandas**: apenas para resultados agregados e amostras pequenas.
- **OpenPyXL**: leitura do dicionário (.xlsx).

### Pré-requisitos

- Python 3.10 ou superior (testado com 3.14).
- Os três arquivos de dados nos caminhos da seção [Dados](#dados) (já estão no repositório).

### Instalação

```bash
git clone <url-do-repositorio>
cd datathon
python -m venv .venv
# Windows: .venv\Scripts\activate    |    Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

### Como executar

Sempre a partir da **raiz do repositório**:

```bash
streamlit run dashboard/app.py
```

Acesse **<http://localhost:8501>** no navegador. Para usar outra porta:
`streamlit run dashboard/app.py --server.port 8502`.

Depois que as dependências estiverem instaladas e os dados no lugar, a aplicação funciona
**sem internet**: não há chamadas externas e a telemetria do Streamlit está desligada em
`.streamlit/config.toml`.

**Google Colab** (opcional, não testado nesta versão): o Colab não abre `localhost` diretamente.
Uma forma possível:

```python
!git clone <url-do-repositorio>
%cd datathon
!pip install -q -r requirements.txt
!nohup streamlit run dashboard/app.py --server.port 8501 --server.headless true > streamlit.log 2>&1 &
from google.colab import output
output.serve_kernel_port_as_window(8501)   # abre a aplicação em outra aba
```

### Testes

```bash
python -m unittest tests.test_services -v    # camada de dados (~15 s)
python -m unittest tests.test_app_pages -v   # renderiza as 7 páginas sem navegador (~2 min)
```

## Estrutura

```text
.streamlit/config.toml       # configuração do Streamlit (sem telemetria; temas claro/escuro)
context/                     # regras do desafio
  Guia do Participante.md
  originais/                 # .docx e .pptx oficiais
dashboard/                   # CAGED Explorer (Streamlit)
  app.py                     # ponto de entrada e menu lateral
  formatting.py              # números, R$, datas e competências no padrão brasileiro
  views/                     # uma página por arquivo (01_overview … 07_relations)
  components/                # interface: filtros, tabelas, gráficos, selos e cartões
  services/                  # dados: conexão DuckDB, consultas SQL, auditoria, catálogo de colunas
data/                        # ver data/README.md
  raw/                       # Novo CAGED em Parquet (versionado, 44 MB)
  reference/                 # dicionário de dados e municípios de SC
  processed/                 # gerado pelo pipeline (não versionado)
docs/
  diagnostico_inicial.md     # diagnóstico técnico e de negócio
  dicionario_analitico.md    # campo a campo: significado, valores, uso
  plano_de_execucao.md       # arquitetura e próximas etapas
  guia_explorador.md         # como usar o CAGED Explorer
reports/
  perfil_bases.md            # perfil gerado automaticamente
src/
  config.py                  # caminhos do projeto (usados também pelo dashboard)
  validation/profile_sources.py
tests/                       # testes do CAGED Explorer (unittest)
requirements.txt
```

O perfil das bases em Markdown continua disponível:

```bash
python -m src.validation.profile_sources > reports/perfil_bases.md
```

## Dados

| Base | Arquivo | Registros |
|---|---|---|
| Novo CAGED — movimentações SC | `data/raw/Novo_Caged_MOV_Limpo.parquet` | 3.397.416 |
| Municípios de SC | `data/reference/Municipios_SC_limpo.csv` | 295 |
| Dicionário de dados | `data/reference/Dicionario_de_dados.xlsx` | 23 abas |

O CSV original do CAGED (~395 MB) **não é versionado** (limite de 100 MB do GitHub); o Parquet
contém os mesmos dados. Origem, formato e cuidados de leitura em [`data/README.md`](data/README.md).

### Como adicionar ou atualizar as bases

1. Substitua o arquivo **no mesmo caminho e com o mesmo nome** (caminhos definidos em `src/config.py`).
   O CAGED deve continuar em Parquet; para gerar a partir do CSV, veja `data/README.md`.
2. Não é preciso reiniciar: o Explorer detecta a mudança (data e tamanho do arquivo) e refaz as
   consultas na próxima interação. Na dúvida, use o menu ⋮ → *Clear cache* ou reinicie o `streamlit`.
3. Abra **Visão geral → Situação da validação** e **Resultados da auditoria**: as checagens comparam
   as contagens com a auditoria inicial (ex.: 3.397.416 registros). Uma base nova vai mostrar
   divergências esperadas; atualize os valores de referência em `dashboard/services/profiling.py`
   (`documentado`/`confere`) e em `docs/diagnostico_inicial.md` depois de validar.
4. Se colunas forem renomeadas, ajuste o catálogo em `dashboard/services/catalog.py`.
5. Rode os testes (`python -m unittest discover tests`).

## Tecnologias do projeto

Python · DuckDB (processamento sem carregar tudo na memória) · PyArrow/Parquet · Pandas
(tabelas agregadas) · Streamlit e Plotly (CAGED Explorer e dashboard) · IA generativa
(classificação de CBOs, com revisão humana — etapa futura).

## Regras do repositório

- Não versionar CSVs pesados, saídas de `data/processed/` nem credenciais (`.env`, chaves de API).
- Nunca editar arquivos em `data/raw/`; todo tratamento fica no código.
- Documentos em português; código, pastas e módulos em inglês.
