# Raio-X do Mercado de Trabalho e Vagas Industriais em Santa Catarina

Projeto desenvolvido para o **Datathon CDIA 2026 — UniSENAI**. Atuando como uma consultoria
de dados, transformamos os microdados do **Novo CAGED** em um painel de inteligência
operacional e territorial para o setor industrial catarinense.

## 🎯 Pergunta central de negócio

> *"Quais regiões e setores industriais de SC enfrentam **apagão de mão de obra** ou
> **expansão acelerada**, e como **renda e escolaridade** explicam esses gargalos?"*

A análise percorre três eixos: **territorial/setorial**, **socioeconômico (renda × escolaridade)**
e **qualificação (agrupamento de CBOs por IA)**.

## 📂 Estrutura do repositório

```
datathon/
├── dataset/                      # Bases do desafio (+ referências do IBGE)
│   ├── Novo_Caged_MOV_Limpo.parquet   # Microdados CAGED-SC (~42 MB, zstd)
│   ├── Municipios_SC_limpo.csv        # Demografia/socioeconômico municipal
│   ├── Dicionario_de_dados.xlsx       # Metadados das variáveis
│   ├── municipios_sc_coords.parquet   # Centroides dos municípios (mapa de bolhas)
│   └── ibge/                          # Mesorregiões: malha (GeoJSON) e município → região
├── notebooks/                    # Entregável 1 — pipeline de dados
│   ├── 01_pipeline_caged_sc.ipynb     # Pipeline completo (ingestão → IA → export)
│   └── _build_notebook.py             # Gerador do notebook (edite este, não o .ipynb)
├── ia/                           # Enriquecimento com IA (CBO → macrofamília)
│   ├── prompt_classificacao_cbo.md    # Prompt exato enviado ao LLM
│   ├── cbo_macrofamilias.csv          # Resultado: 2.207 CBOs classificados
│   ├── classificar_cbos.py            # Reproduz a classificação via API (Claude)
│   └── validar_classificacao.py       # Cobertura, coerência e amostra para revisão humana
├── outputs/                      # Tabelas geradas pelo pipeline (lidas pelo dashboard)
├── dashboard/                    # Entregável 2 — painel analítico (Streamlit)
│   ├── app.py                         # Entrada: navegação em 3 seções
│   ├── paginas/                       # Visualizações essenciais e complementares
│   ├── mapa3d.py                      # Mapa 3D clicável das mesorregiões
│   ├── dados.py                       # Carga das tabelas e indicadores por recorte
│   ├── views/, services/, components/ # Consulta e exploração dos dados (CAGED Explorer)
├── docs/                         # Diagnóstico das bases, dicionário analítico, plano
├── reports/                      # Perfil das bases (auditoria reproduzível)
├── src/                          # Configuração de caminhos e validação das bases
├── tests/                        # Testes das páginas e serviços de exploração
├── documentos_apoio/             # Guia do participante e PPT do desafio
├── requirements.txt
└── ENTREGAVEIS.md                # Checklist dos entregáveis obrigatórios
```

## 🗃️ Dados

A planilha pesada do CAGED (~395 MB em CSV) foi convertida para **Parquet com compressão zstd
(~42 MB)**, sem perda de dados, para caber no limite do GitHub. Detalhes e dicionário em
[`dataset/README.md`](dataset/README.md).

- **Novo CAGED-SC:** 3.397.416 movimentações, 30 colunas, 295 municípios, 2.207 CBOs,
  declaradas de set/2025 a ago/2026 (12 meses; 1,09% são declarações fora do prazo
  referentes a meses anteriores). Cada linha é uma movimentação com `saldomovimentação`
  igual a `+1` (admissão) ou `−1` (desligamento).
- **Municípios:** população, IDHM, PIB per capita e escolarização — cruzados com o CAGED
  pelo código do município.

## 🚀 Como rodar

### Pré-requisitos
- **Python 3.10+**
- Recomendado: um ambiente virtual.

### 1. Clonar e preparar o ambiente

```bash
git clone https://github.com/Matheus-S-Cruz/datathon.git
cd datathon

# criar e ativar o ambiente virtual
python -m venv .venv
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate
```

> **Windows — erro de execução de scripts?** Rode uma vez:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

### 2. Instalar dependências

```bash
pip install -r requirements.txt                   # pipeline + dashboard
```

### 3. (Opcional) Reexecutar o pipeline

As tabelas em `outputs/` já estão versionadas, então **o dashboard roda sem este passo**.
Para regerá-las a partir do CAGED:

**No VS Code:** abra `notebooks/01_pipeline_caged_sc.ipynb`, selecione o kernel do `.venv`
e clique em **Run All**.

**Pela linha de comando:**
```bash
jupyter nbconvert --to notebook --execute --inplace notebooks/01_pipeline_caged_sc.ipynb
```

> O notebook **não chama API**: a etapa de IA carrega a classificação já gerada pelo LLM
> (`ia/cbo_macrofamilias.csv`). Para refazê-la: `python ia/classificar_cbos.py`
> (requer `ANTHROPIC_API_KEY`).

### 4. Abrir o dashboard

```bash
streamlit run dashboard/app.py
```
Acesse `http://localhost:8501`. Veja [`dashboard/README.md`](dashboard/README.md) para o
detalhamento das páginas.

### 5. (Opcional) Testes

```bash
python -m unittest tests.test_services tests.test_app_pages
```

## 🧭 Metodologia (resumo)

1. **Ingestão e validação** das três bases + dicionário de códigos.
2. **Limpeza/tipagem** e filtragem de exclusões (MOV × EX).
3. **Join** CAGED × municípios pelo código do município.
4. **Métricas:** saldo, **saldo por 10.000 habitantes** (normalização) e giro/turnover.
5. **Agregações** territorial, setorial e socioeconômica (renda × escolaridade).
6. **IA:** os 2.207 CBOs foram classificados por um LLM (Claude) em **14 macrofamílias**
   pensadas para a indústria (metalmecânica, têxtil, alimentos, técnicos, engenharia…),
   com nível de qualificação e indicação de ocupação industrial. Validação: 98% de
   coerência com a estrutura oficial da CBO + amostra para revisão humana (`ia/`).
7. **Exportação** das tabelas-base para o dashboard.

## 🔍 Principais achados (preliminares)

- **Todas as 6 mesorregiões têm saldo positivo** — no agregado não há "apagão" territorial.
  Grande Florianópolis lidera (+85 vagas por 10 mil hab.); Sul Catarinense é o mais fraco (+10).
- **O gargalo aparece por ocupação** (macrofamílias da IA): o **operacional têxtil** (−3.884) e o
  **metalmecânico** (−758) desligam mais do que contratam; 55% dos desligamentos no têxtil são
  **a pedido** do trabalhador — sinal de dificuldade de reter, com salário médio de ~R$ 2.240.
- **Vale do Itajaí × têxtil** concentra a maior movimentação do estado (66 mil admissões +
  desligamentos) com saldo negativo.
- **Técnicos industriais** desligam mais do que contratam em quase todas as regiões, mesmo com
  salário médio de ~R$ 3.300.
- **47% de todos os desligamentos são a pedido** — mercado aquecido.

> **Limites da análise:** o CAGED mede fluxo (não estoque nem vagas abertas) — saldo e
> rotatividade são **indícios**; exclusões (EXC) não foram fornecidas; promoções internas não
> aparecem (o saldo negativo de Gestão pode refletir vagas preenchidas internamente); IDHM é de
> 2010; salários fora de R$ 500–50.000 ficam fora das médias. Diagnóstico completo das bases em
> [`docs/diagnostico_inicial.md`](docs/diagnostico_inicial.md).

## 📦 Entregáveis

Acompanhe o status em [`ENTREGAVEIS.md`](ENTREGAVEIS.md).

1. **Notebook de pipeline** — `notebooks/01_pipeline_caged_sc.ipynb` ✅
2. **Dashboard analítico** — `dashboard/app.py` ✅
3. **Pitch executivo (3 min)** — em elaboração

## 🛠️ Tecnologias

Python · pandas · PyArrow (Parquet) · DuckDB · Jupyter · Streamlit · Plotly · Shapely · Claude (LLM)
