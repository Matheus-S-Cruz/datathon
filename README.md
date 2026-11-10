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
├── dataset/                      # Bases de dados do desafio
│   ├── Novo_Caged_MOV_Limpo.parquet   # Microdados CAGED-SC (24 meses, ~42 MB, zstd)
│   ├── Municipios_SC_limpo.csv        # Demografia/socioeconômico municipal
│   ├── Dicionario_de_dados.xlsx       # Metadados das variáveis
│   └── README.md
├── notebooks/                    # Entregável 1 — pipeline de dados
│   ├── 01_pipeline_caged_sc.ipynb     # Pipeline completo (ingestão → export)
│   ├── _build_notebook.py             # Gerador do notebook (reprodutibilidade)
│   └── README.md
├── outputs/                      # Tabelas-base geradas pelo pipeline (consumidas pelo painel)
├── dashboard/                    # Entregável 2 — painel analítico
│   ├── app.py                         # Dashboard Streamlit
│   ├── requirements.txt
│   └── README.md
├── documentos_apoio/             # Guia do participante e PPT do desafio
├── ENTREGAVEIS.md                # Checklist dos entregáveis obrigatórios
└── README.md                     # Este arquivo
```

## 🗃️ Dados

A planilha pesada do CAGED (~395 MB em CSV) foi convertida para **Parquet com compressão zstd
(~42 MB)**, sem perda de dados, para caber no limite do GitHub. Detalhes e dicionário em
[`dataset/README.md`](dataset/README.md).

- **Novo CAGED-SC:** 3.397.416 movimentações, 30 colunas, 295 municípios, 2.207 CBOs,
  cobrindo set/2024 a ago/2026. Cada linha é uma movimentação com `saldomovimentação`
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
pip install pandas pyarrow openpyxl jupyter       # pipeline
pip install -r dashboard/requirements.txt         # dashboard
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

> O passo de enriquecimento com IA é **opcional**: só chama um LLM se a variável de ambiente
> `OPENAI_API_KEY` estiver definida; caso contrário usa um baseline determinístico (sem rede).

### 4. Abrir o dashboard

```bash
streamlit run dashboard/app.py
```
Acesse `http://localhost:8501`. Veja [`dashboard/README.md`](dashboard/README.md) para o
detalhamento das abas e filtros.

## 🧭 Metodologia (resumo)

1. **Ingestão e validação** das três bases + dicionário de códigos.
2. **Limpeza/tipagem** e filtragem de exclusões (MOV × EX).
3. **Join** CAGED × municípios pelo código do município.
4. **Métricas:** saldo, **saldo por 10.000 habitantes** (normalização) e giro/turnover.
5. **Agregações** territorial, setorial e socioeconômica (renda × escolaridade).
6. **IA:** agrupamento dos 2.207 CBOs em macrofamílias ocupacionais.
7. **Exportação** das tabelas-base para o dashboard.

## 🔍 Principais achados

- **Apagão em cargos qualificados:** macrofamílias de maior instrução apresentam **saldo
  negativo** (Dirigentes/Gerentes, Técnicos de nível médio e Nível superior/Engenharia),
  enquanto o **operacional cresce** — sinal de escassez no topo da pirâmide de qualificação.
- **Polos de expansão** concentrados em municípios do litoral/dinâmicos (ex.: Navegantes).
- **Rotatividade (apagão):** municípios com giro elevado e saldo baixo/negativo indicam
  reposição constante sem crescimento líquido.

> **Limites da análise:** saldo e giro refletem fluxo (não estoque de vínculos); o IDHM é de
> 2010; salários declarados podem conter outliers.

## 📦 Entregáveis

Acompanhe o status em [`ENTREGAVEIS.md`](ENTREGAVEIS.md).

1. **Notebook de pipeline** — `notebooks/01_pipeline_caged_sc.ipynb` ✅
2. **Dashboard analítico** — `dashboard/app.py` ✅
3. **Pitch executivo (3 min)** — em elaboração

## 🛠️ Tecnologias

Python · pandas · PyArrow (Parquet) · Jupyter · Streamlit · Plotly
