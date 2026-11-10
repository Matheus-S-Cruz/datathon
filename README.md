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
| Pipeline de tratamento | ⏳ aguardando validação das decisões metodológicas |
| Agrupamento de CBOs com IA | ⏳ |
| Dashboard | ⏳ |
| Pitch | ⏳ |

## Estrutura

```text
context/                     # regras do desafio
  Guia do Participante.md
  originais/                 # .docx e .pptx oficiais
data/                        # ver data/README.md
  raw/                       # Novo CAGED em Parquet (versionado, 44 MB)
  reference/                 # dicionário de dados e municípios de SC
  processed/                 # gerado pelo pipeline (não versionado)
docs/
  diagnostico_inicial.md     # diagnóstico técnico e de negócio
  dicionario_analitico.md    # campo a campo: significado, valores, uso
  plano_de_execucao.md       # arquitetura e próximas etapas
reports/
  perfil_bases.md            # perfil gerado automaticamente
src/
  config.py                  # caminhos do projeto
  validation/profile_sources.py
requirements.txt
```

## Como executar

Requer Python 3.10+.

```bash
git clone <url-do-repositorio>
cd datathon
python -m venv .venv
# Windows: .venv\Scripts\activate    |    Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

# Regenera o perfil das bases (somente leitura, ~1 min)
python -m src.validation.profile_sources > reports/perfil_bases.md
```

**Google Colab**:

```python
!git clone <url-do-repositorio>
%cd datathon
!pip install -q -r requirements.txt
!python -m src.validation.profile_sources
```

Execute sempre a partir da raiz do repositório; os caminhos são definidos em `src/config.py`.

## Dados

| Base | Arquivo | Registros |
|---|---|---|
| Novo CAGED — movimentações SC | `data/raw/Novo_Caged_MOV_Limpo.parquet` | 3.397.416 |
| Municípios de SC | `data/reference/Municipios_SC_limpo.csv` | 295 |
| Dicionário de dados | `data/reference/Dicionario_de_dados.xlsx` | 23 abas |

O CSV original do CAGED (~395 MB) **não é versionado** (limite de 100 MB do GitHub); o Parquet
contém os mesmos dados. Origem, formato e cuidados de leitura em [`data/README.md`](data/README.md).

## Tecnologias

Python · DuckDB (processamento sem carregar tudo na memória) · PyArrow/Parquet · Pandas
(tabelas agregadas) · Plotly e Streamlit (dashboard, próximas etapas) · IA generativa
(classificação de CBOs, com revisão humana).

## Regras do repositório

- Não versionar CSVs pesados, saídas de `data/processed/` nem credenciais (`.env`, chaves de API).
- Nunca editar arquivos em `data/raw/`; todo tratamento fica no código.
- Documentos em português; código, pastas e módulos em inglês.
