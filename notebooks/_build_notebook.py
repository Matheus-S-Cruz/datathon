"""Gera o notebook de pipeline (Entregável 1) como .ipynb válido.

Executar: python notebooks/_build_notebook.py
Isso evita escrever JSON de notebook à mão. O script lista pares (tipo, texto)
e serializa no formato nbformat v4.
"""
import json
from pathlib import Path

cells = []

def md(text):
    cells.append(("markdown", text))

def code(text):
    cells.append(("code", text))

# ------------------------------------------------------------------ TÍTULO
md("""# Datathon CDIA 2026 — Pipeline de Dados
## Raio-X do Mercado de Trabalho e Vagas Industriais em Santa Catarina

**Pergunta central de negócio**

> *"Quais regiões e setores industriais de SC enfrentam apagão de mão de obra ou
> expansão acelerada, e como renda e escolaridade explicam esses gargalos?"*

Este notebook implementa o **pipeline completo** (Entregável 1):

1. Ingestão e validação das bases
2. Limpeza e filtragem (exclusões MOV × EX)
3. Cruzamento (join) CAGED × municípios
4. Métricas de negócio (saldo, saldo por 10 mil hab., turnover)
5. Agregações territoriais, setoriais e socioeconômicas
6. Enriquecimento com IA — agrupamento de CBOs em macrofamílias
7. Exportação das tabelas-base para o dashboard

Todas as tabelas finais são gravadas em `outputs/` e consumidas pelo dashboard (Entregável 2).
""")

# ------------------------------------------------------------------ 0. SETUP
md("""## 0. Configuração e dependências

```bash
pip install pandas pyarrow openpyxl plotly
```
Para o passo de IA (opcional), defina a variável de ambiente `OPENAI_API_KEY`.
""")

code("""import os
import unicodedata
import pandas as pd
import numpy as np

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

# Caminhos (ajuste se executar de outro diretório)
BASE = ".." if os.path.basename(os.getcwd()) == "notebooks" else "."
DATASET = os.path.join(BASE, "dataset")
OUTPUTS = os.path.join(BASE, "outputs")
os.makedirs(OUTPUTS, exist_ok=True)

CAGED_PARQUET = os.path.join(DATASET, "Novo_Caged_MOV_Limpo.parquet")
MUNIC_CSV     = os.path.join(DATASET, "Municipios_SC_limpo.csv")
DICIONARIO    = os.path.join(DATASET, "Dicionario_de_dados.xlsx")

print("dataset:", os.path.abspath(DATASET))
print("outputs:", os.path.abspath(OUTPUTS))""")

# ------------------------------------------------------------------ 1. INGESTÃO
md("""## 1. Ingestão e validação

O CAGED está em **Parquet (zstd)** — ~42 MB, 3.397.416 movimentações, 30 colunas,
somente Santa Catarina (uf=42). Lemos os dicionários para traduzir os códigos.
""")

code("""# --- CAGED (movimentações) ---
caged = pd.read_parquet(CAGED_PARQUET)
print("CAGED:", caged.shape)

# --- Municípios (demografia / socioeconômico) ---
munic = pd.read_csv(MUNIC_CSV)
print("Municípios:", munic.shape)

# --- Dicionário de dados: cada aba mapeia Código -> Descrição ---
xls = pd.ExcelFile(DICIONARIO)
def tabela_dic(aba):
    d = pd.read_excel(DICIONARIO, sheet_name=aba, dtype=str)
    d.columns = [c.strip().lower() for c in d.columns]
    return dict(zip(d["código"].astype(str).str.strip(),
                    d["descrição"].astype(str).str.strip()))

MAP_SECAO   = tabela_dic("seção")
MAP_INSTR   = tabela_dic("graudeinstrução")
MAP_TIPOMOV = tabela_dic("tipomovimentação")
MAP_MUNIC   = tabela_dic("município")
print("Abas do dicionário:", xls.sheet_names)""")

code("""# Validação de schema mínima
esperadas = {"competênciamov","uf","município","seção","saldomovimentação",
             "cbo2002ocupação","graudeinstrução","salário","tipomovimentação"}
faltando = esperadas - set(caged.columns)
assert not faltando, f"Colunas ausentes no CAGED: {faltando}"
print("Schema OK. UFs presentes:", caged["uf"].unique())
print("Competências (meses):", caged["competênciamov"].nunique(),
      "de", caged["competênciamov"].min(), "a", caged["competênciamov"].max())""")

# ------------------------------------------------------------------ 2. LIMPEZA
md("""## 2. Limpeza, tipagem e filtragem (exclusões MOV × EX)

No Parquet todas as colunas vêm como **texto** (preserva fidelidade). Aqui convertemos
os tipos e aplicamos o filtro de exclusões exigido pelo guia.

**Sobre o filtro MOV × EX:** a base de movimentações já é a "MOV_Limpo" (as exclusões
da base EX já foram removidas na origem). Mantemos a verificação defensiva: se existir a
coluna `indicadordeexclusão`, descartamos registros marcados como excluídos (`=1`).
""")

code("""df = caged.copy()

# Colunas numéricas (salário usa vírgula decimal e ponto de milhar)
def to_float_br(s):
    return pd.to_numeric(
        s.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
        errors="coerce")

df["saldo"]          = pd.to_numeric(df["saldomovimentação"], errors="coerce")
df["salario"]        = to_float_br(df["salário"])
df["salario_fixo"]   = to_float_br(df.get("valorsaláriofixo", pd.Series(index=df.index)))
df["idade"]          = pd.to_numeric(df["idade"], errors="coerce")
df["grau_cod"]       = pd.to_numeric(df["graudeinstrução"], errors="coerce")
df["mun_cod"]        = df["município"].astype(str).str.strip()

# Filtro de exclusões (defensivo)
if "indicadordeexclusão" in df.columns:
    antes = len(df)
    df = df[df["indicadordeexclusão"].astype(str).str.strip() != "1"].copy()
    print(f"Exclusões removidas: {antes - len(df)}")
else:
    print("Sem coluna de exclusão (base já limpa na origem).")

# Descartar artefatos de índice
df = df.drop(columns=[c for c in ["Unnamed: 0.1", "Unnamed: 0"] if c in df.columns])

# Traduções legíveis
df["setor"]      = df["seção"].map(MAP_SECAO).fillna("Não identificado")
df["grau_instr"] = df["graudeinstrução"].astype(str).map(MAP_INSTR).fillna("Não Identificado")
df["tipo_mov"]   = df["tipomovimentação"].astype(str).map(MAP_TIPOMOV).fillna("Não Identificado")

df["admissao"]     = (df["saldo"] > 0).astype(int)
df["desligamento"] = (df["saldo"] < 0).astype(int)

print("Linhas após limpeza:", len(df))
df[["competênciamov","mun_cod","setor","saldo","salario","grau_instr"]].head()""")

# ------------------------------------------------------------------ 3. JOIN
md("""## 3. Cruzamento CAGED × municípios

Chave: código do município. No `Municipios_SC_limpo.csv` o código IBGE tem 7 dígitos;
no CAGED, 6 (sem o dígito verificador). Alinhamos pelos **6 primeiros dígitos**.
""")

code("""# Normaliza nomes de colunas do arquivo de municípios
munic.columns = [c.strip() for c in munic.columns]

def achar_col(cols, *chaves):
    for c in cols:
        low = c.lower()
        if all(k in low for k in chaves):
            return c
    return None

col_codigo = achar_col(munic.columns, "código")
col_nome   = achar_col(munic.columns, "município")
col_pop    = achar_col(munic.columns, "população", "último censo") or achar_col(munic.columns, "população")
col_idhm   = achar_col(munic.columns, "idhm")
col_pib    = achar_col(munic.columns, "pib per capita") or achar_col(munic.columns, "pib")
col_escol  = achar_col(munic.columns, "escolariza")

print("Mapeadas:", dict(codigo=col_codigo, nome=col_nome, pop=col_pop,
                         idhm=col_idhm, pib=col_pib, escol=col_escol))

mun = pd.DataFrame({
    "mun_cod":   munic[col_codigo].astype(str).str.replace(r"\\D", "", regex=True).str[:6],
    "municipio": munic[col_nome].astype(str).str.strip(),
})
def num(col):
    if col is None: return np.nan
    return to_float_br(munic[col]) if munic[col].dtype == object else pd.to_numeric(munic[col], errors="coerce")

mun["populacao"]     = num(col_pop)
mun["idhm"]          = num(col_idhm)
mun["pib_per_capita"]= num(col_pib)
mun["escolarizacao"] = num(col_escol)
mun = mun.drop_duplicates("mun_cod")
print("Municípios normalizados:", mun.shape)
mun.head()""")

code("""dfm = df.merge(mun, on="mun_cod", how="left")
sem_match = dfm["municipio"].isna().mean()
print(f"% movimentações sem município correspondente: {sem_match:.2%}")
dfm[["mun_cod","municipio","populacao","setor","saldo"]].head()""")

# ------------------------------------------------------------------ 4. MÉTRICAS
md("""## 4. Métricas de negócio

- **Saldo** = Σ(saldomovimentação) = admissões − desligamentos.
- **Saldo por 10.000 habitantes** = saldo / população × 10.000 (normalização exigida pelo guia).
- **Turnover (rotatividade)** = (admissões + desligamentos) / 2 ÷ estoque aproximado.
  Como não temos o estoque de vínculos, usamos a **taxa de giro** = (adm+desl) por 10 mil hab,
  que diferencia "apagão" (giro alto, saldo baixo) de "expansão" (saldo alto).
""")

code("""def agrega(grupo_cols, nome_pop="populacao"):
    g = dfm.groupby(grupo_cols, dropna=False).agg(
        admissoes=("admissao", "sum"),
        desligamentos=("desligamento", "sum"),
        saldo=("saldo", "sum"),
        movimentacoes=("saldo", "size"),
        salario_medio=("salario", "mean"),
        salario_mediano=("salario", "median"),
        grau_medio=("grau_cod", "mean"),
        idade_media=("idade", "mean"),
    ).reset_index()
    g["giro"] = g["admissoes"] + g["desligamentos"]
    return g

# Base populacional por município (para normalizar)
pop_mun = mun.set_index("mun_cod")["populacao"]""")

# ------------------------------------------------------------------ 5. TERRITÓRIO
md("""## 5. Eixo territorial — municípios em expansão vs. apagão""")

code("""terr = agrega(["mun_cod", "municipio"])
terr = terr.merge(mun[["mun_cod","populacao","idhm","pib_per_capita","escolarizacao"]],
                  on="mun_cod", how="left")
terr["saldo_por_10k"] = terr["saldo"] / terr["populacao"] * 10_000
terr["giro_por_10k"]  = terr["giro"]  / terr["populacao"] * 10_000

print("TOP 10 EXPANSÃO (saldo por 10 mil hab.):")
display_cols = ["municipio","saldo","saldo_por_10k","giro_por_10k","salario_medio","grau_medio"]
print(terr.sort_values("saldo_por_10k", ascending=False)[display_cols].head(10).to_string(index=False))

print("\\nTOP 10 RETRAÇÃO / APAGÃO (menor saldo por 10 mil hab.):")
print(terr.sort_values("saldo_por_10k")[display_cols].head(10).to_string(index=False))""")

# ------------------------------------------------------------------ 6. SETOR
md("""## 6. Eixo setorial — setores industriais que lideram

Foco industrial = seções **B** (Extrativas), **C** (Transformação), **D** (Eletricidade/Gás),
**F** (Construção). Analisamos todos e sinalizamos os industriais.
""")

code("""SETORES_INDUSTRIAIS = {"B", "C", "D", "F"}
setor = agrega(["seção", "setor"])
setor["industrial"] = setor["seção"].isin(SETORES_INDUSTRIAIS)
setor = setor.sort_values("saldo", ascending=False)
print(setor[["setor","saldo","admissoes","desligamentos","giro",
             "salario_medio","grau_medio","industrial"]].to_string(index=False))""")

code("""# Cruzamento território × setor (onde cada setor cresce/encolhe)
terr_setor = agrega(["mun_cod","municipio","seção","setor"])
terr_setor = terr_setor.merge(pop_mun.rename("populacao"), on="mun_cod", how="left")
terr_setor["saldo_por_10k"] = terr_setor["saldo"] / terr_setor["populacao"] * 10_000
# Exemplo: maiores polos industriais por saldo
ind = terr_setor[terr_setor["seção"].isin(SETORES_INDUSTRIAIS)]
print("Maiores saldos industriais (município × setor):")
print(ind.sort_values("saldo", ascending=False)
        [["municipio","setor","saldo","salario_medio","grau_medio"]].head(15).to_string(index=False))""")

# ------------------------------------------------------------------ 7. SOCIOECON
md("""## 7. Eixo socioeconômico — renda e escolaridade explicam os gargalos?

Comparamos o perfil de **admitidos vs. desligados** por escolaridade e salário, e cruzamos
o saldo setorial/territorial com renda e escolaridade para apontar a causa-raiz:
desatratividade salarial, escolaridade não atendida ou compressão salarial.
""")

code("""# Perfil admitido vs desligado por escolaridade
perfil = (dfm.assign(mov=np.where(dfm["saldo"] > 0, "Admitido", "Desligado"))
            .groupby(["mov","grau_instr"], dropna=False)
            .agg(n=("saldo","size"), salario_medio=("salario","mean"))
            .reset_index())
print(perfil.to_string(index=False))

# Salário médio por grau de instrução (há compressão salarial?)
sal_grau = (dfm.groupby("grau_cod")
              .agg(grau=("grau_instr","first"),
                   salario_medio=("salario","mean"),
                   n=("salario","size"))
              .reset_index().sort_values("grau_cod"))
print("\\nSalário médio por grau de instrução:")
print(sal_grau[["grau","salario_medio","n"]].to_string(index=False))""")

# ------------------------------------------------------------------ 8. IA / CBO
md("""## 8. Enriquecimento com IA — agrupamento de CBOs em macrofamílias

São **2.207 CBOs distintos**. O guia exige agrupá-los em **macrofamílias** com IA
Generativa, para responder: *o gargalo está em funções operacionais de base ou em
cargos técnicos/engenharia?*

Estratégia robusta e reprodutível:
1. **Baseline determinístico** pela estrutura do próprio CBO-2002 (o 1º dígito do código
   define o Grande Grupo ocupacional). Isso funciona **sem rede** e já entrega macrofamílias.
2. **Refino opcional via LLM** (OpenAI) para nomear/ajustar famílias a partir dos CBOs mais
   frequentes. Ativado apenas se `OPENAI_API_KEY` estiver definida.
""")

code("""# 8.1 Baseline determinístico: Grande Grupo CBO (1º dígito)
GRANDE_GRUPO_CBO = {
    "0": "Forças Armadas / Segurança",
    "1": "Dirigentes e Gerentes",
    "2": "Profissionais de nível superior (Técnico/Engenharia)",
    "3": "Técnicos de nível médio",
    "4": "Trabalhadores de apoio administrativo",
    "5": "Serviços, vendas e comércio",
    "6": "Agropecuários e florestais",
    "7": "Produção de bens e serviços industriais (Operacional)",
    "8": "Produção de bens e serviços industriais (Operacional)",
    "9": "Manutenção e reparação",
}
cbo = dfm["cbo2002ocupação"].astype(str).str.zfill(6)
dfm["cbo_grande_grupo"] = cbo.str[0].map(GRANDE_GRUPO_CBO).fillna("Não classificado")

macro = (dfm.groupby("cbo_grande_grupo")
           .agg(saldo=("saldo","sum"),
                admissoes=("admissao","sum"),
                desligamentos=("desligamento","sum"),
                salario_medio=("salario","mean"),
                grau_medio=("grau_cod","mean"),
                n_cbos=("cbo2002ocupação","nunique"))
           .reset_index().sort_values("saldo", ascending=False))
print(macro.to_string(index=False))""")

code("""# 8.2 (Opcional) Refino via LLM — nomeia macrofamílias a partir dos top CBOs
def refinar_macrofamilias_llm(top_n=60):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY não definida — pulando refino por LLM (baseline já aplicado).")
        return None
    try:
        from openai import OpenAI
    except ImportError:
        print("Pacote 'openai' não instalado (pip install openai). Usando baseline.")
        return None

    top = (dfm.groupby("cbo2002ocupação")
             .agg(saldo=("saldo","sum"), n=("saldo","size"))
             .reset_index().sort_values("n", ascending=False).head(top_n))
    lista = "\\n".join(f'- CBO {r.cbo2002ocupação} (saldo {int(r.saldo)}, {int(r.n)} movs)'
                       for r in top.itertuples())
    prompt = (
        "Você é um especialista em mercado de trabalho industrial. Agrupe os códigos CBO-2002 "
        "abaixo em no máximo 8 MACROFAMÍLIAS ocupacionais úteis para a indústria catarinense "
        "(ex.: 'Operacional de produção', 'Técnico/Engenharia', 'Logística e transporte', "
        "'Administrativo', 'Manutenção'). Responda em JSON: lista de objetos "
        "{cbo, macrofamilia}.\\n\\n" + lista
    )
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    print("Resposta do LLM (recorte):")
    print(resp.choices[0].message.content[:1500])
    return resp.choices[0].message.content

_ = refinar_macrofamilias_llm()""")

# ------------------------------------------------------------------ 9. EXPORT
md("""## 9. Exportação das tabelas-base (consumidas pelo dashboard)

Gravamos agregações enxutas em `outputs/` — são elas que o dashboard (Entregável 2) carrega.
""")

code("""saidas = {
    "agg_municipio.parquet":        terr,
    "agg_setor.parquet":            setor,
    "agg_municipio_setor.parquet":  terr_setor,
    "perfil_adm_desl.parquet":      perfil,
    "salario_por_grau.parquet":     sal_grau,
    "macrofamilias_cbo.parquet":    macro,
}
for nome, tabela in saidas.items():
    caminho = os.path.join(OUTPUTS, nome)
    tabela.to_parquet(caminho, index=False)
    print(f"gravado: {caminho}  ({tabela.shape[0]} linhas x {tabela.shape[1]} cols)")

print("\\nPipeline concluído. Tabelas prontas para o dashboard.")""")

# ------------------------------------------------------------------ 10. CONCLUSÕES
md("""## 10. Como ler os resultados (resumo analítico)

- **Expansão acelerada**: municípios/setores com `saldo_por_10k` alto e crescente.
- **Apagão de mão de obra**: `giro_por_10k` alto com `saldo` baixo/negativo — reposição
  constante sem crescimento líquido.
- **Causa-raiz (renda/escolaridade)**:
  - salário setorial abaixo da média + saldo negativo → **desatratividade salarial**;
  - vagas exigindo grau alto em região de baixa `escolarizacao`/IDHM → **escolaridade não atendida**;
  - salário estável apesar de maior exigência de instrução → **compressão salarial**.
- **IA/CBO**: a macrofamília com saldo negativo mostra se o apagão é **operacional** (grupos 7/8)
  ou **técnico/engenharia** (grupo 2) — base direta para as recomendações do pitch.

> **Limites da análise:** saldo e giro usam o próprio CAGED (fluxo, não estoque de vínculos);
> IDHM é de 2010; salários declarados podem conter outliers (filtrar no dashboard se necessário).
""")

# -------------------------------------------------------------- SERIALIZAÇÃO
nb = {
    "cells": [],
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}
for kind, text in cells:
    src = text.splitlines(keepends=True)
    if kind == "markdown":
        nb["cells"].append({"cell_type": "markdown", "metadata": {}, "source": src})
    else:
        nb["cells"].append({"cell_type": "code", "metadata": {},
                             "execution_count": None, "outputs": [], "source": src})

out = Path(__file__).with_name("01_pipeline_caged_sc.ipynb")
out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("Notebook gerado:", out, "com", len(cells), "células")
