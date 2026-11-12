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
pip install -r requirements.txt   # pandas, pyarrow, openpyxl (+ streamlit/pydeck/plotly p/ dashboard)
```
A etapa de IA (seção 8) **não chama API ao executar o notebook**: ela carrega a classificação
gerada pelo LLM e versionada em `ia/cbo_macrofamilias.csv`. Para refazê-la via API, veja
`ia/classificar_cbos.py` (requer `ANTHROPIC_API_KEY`).
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
IBGE_MUNIC    = os.path.join(DATASET, "ibge", "municipios_sc.json")   # município -> mesorregião (API IBGE)
CBO_IA        = os.path.join(BASE, "ia", "cbo_macrofamilias.csv")     # classificação gerada por LLM
CBO_ENTRADA   = os.path.join(BASE, "ia", "cbos_para_classificar.csv") # CBOs + títulos enviados ao LLM

print("dataset:", DATASET)
print("outputs:", OUTPUTS)""")

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
print("Competências de declaração (competênciadec):", caged["competênciadec"].nunique(),
      "meses, de", caged["competênciadec"].min(), "a", caged["competênciadec"].max())
fora = (caged["indicadordeforadoprazo"] == "1").mean()
print(f"Declarações fora do prazo (competênciamov anterior a set/2025): {fora:.2%}")""")

# ------------------------------------------------------------------ 2. LIMPEZA
md("""## 2. Limpeza, tipagem e filtragem (exclusões MOV × EX)

No Parquet todas as colunas vêm como **texto** (preserva fidelidade). Aqui convertemos
os tipos e aplicamos o filtro de exclusões exigido pelo guia.

**Sobre o filtro MOV × EX (premissa explícita):** o Novo CAGED é publicado em três arquivos —
MOV (movimentações no prazo), FOR (fora do prazo) e EXC (exclusões). Recebemos apenas a base
**MOV já limpa** (`Novo_Caged_MOV_Limpo`), que não traz a coluna `indicadordeexclusão` nem o
arquivo EXC. Portanto: (1) mantemos uma verificação defensiva — se a coluna existir, removemos
`=1`; (2) declaramos como **limite** que exclusões posteriores não puderam ser abatidas.

Outros tratamentos:
- **Salário:** 1% dos registros têm salário 0 e o máximo chega a R$ 3,4 milhões (erros de
  declaração). Para médias salariais consideramos apenas a faixa **R$ 500 – R$ 50.000**; os
  registros fora dela continuam contando no saldo, só não entram no salário médio.
- **Escolaridade:** o código CAGED não é ordinal (80 = pós-graduação, 99 = não identificado),
  então a média dos códigos não faz sentido. Convertemos para **anos de estudo** aproximados
  e criamos o indicador **% com ensino superior completo**.
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
df["cbo"]            = df["cbo2002ocupação"].astype(str).str.strip().str.zfill(6)

# Salário válido para médias (fora da faixa vira NaN só na coluna de salário)
df.loc[~df["salario"].between(500, 50_000), "salario"] = np.nan

# Escolaridade -> anos de estudo (aprox.) e flag de superior completo
ANOS_ESTUDO = {1: 0, 2: 2, 3: 5, 4: 7, 5: 9, 6: 10, 7: 12, 8: 13.5,
               9: 16, 80: 17, 10: 18, 11: 22}            # 99 = não identificado -> NaN
df["anos_estudo"] = df["grau_cod"].map(ANOS_ESTUDO)
df["superior"]    = df["grau_cod"].isin([9, 10, 11, 80]).astype(float)
df.loc[df["grau_cod"] == 99, "superior"] = np.nan

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
# Motivo do desligamento: "a pedido" (40) = trabalhador saiu por vontade própria — sinal de
# mercado aquecido / dificuldade de reter (indício de apagão); demissão (31, 32) = iniciativa da empresa
df["a_pedido"] = (df["tipomovimentação"].astype(str) == "40").astype(int)
df["demissao"] = df["tipomovimentação"].astype(str).isin(["31", "32"]).astype(int)

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
# população estimada 2026 (mais próxima do período analisado, 2025-26); fallback: censo 2022
col_pop    = achar_col(munic.columns, "população", "estimada") or achar_col(munic.columns, "população", "último censo")
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
    # este CSV usa PONTO decimal (ex.: IDHM 0.694, PIB 44644.04) -> conversão direta
    if col is None: return np.nan
    return pd.to_numeric(munic[col], errors="coerce")

mun["populacao"]     = num(col_pop)
mun["idhm"]          = num(col_idhm)
mun["pib_per_capita"]= num(col_pib)
mun["escolarizacao"] = num(col_escol)
# o CSV termina com linhas de notas/fontes (HTML) -> só ficam linhas com código numérico
mun = mun[mun["mun_cod"].str.fullmatch(r"\\d{6}")].drop_duplicates("mun_cod")

# Mesorregião IBGE (6 regiões de SC) — base do mapa do dashboard
import json
with open(IBGE_MUNIC, encoding="utf-8") as f:
    ibge = json.load(f)
meso = pd.DataFrame({
    "mun_cod":        [str(m["id"])[:6] for m in ibge],
    "cod_meso":       [m["microrregiao"]["mesorregiao"]["id"] for m in ibge],
    "mesorregiao":    [m["microrregiao"]["mesorregiao"]["nome"] for m in ibge],
    "microrregiao":   [m["microrregiao"]["nome"] for m in ibge],
})
# inner join com a lista oficial do IBGE: descarta linhas de rodapé que não são municípios
antes = len(mun)
mun = mun.merge(meso, on="mun_cod", how="inner")
print(f"Linhas descartadas (não-municípios): {antes - len(mun)}")
assert len(mun) == 295, "SC tem 295 municípios"
print("Municípios normalizados:", mun.shape)
print(mun.groupby("mesorregiao")["populacao"].agg(["size", "sum"]).rename(columns={"size": "municipios"}))
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
        anos_estudo=("anos_estudo", "mean"),
        pct_superior=("superior", "mean"),
        idade_media=("idade", "mean"),
    ).reset_index()
    g["giro"] = g["admissoes"] + g["desligamentos"]
    # taxa de reposição: desligamentos para cada admissão (≈1 = só repõe quem sai -> rotatividade)
    g["reposicao"] = g["desligamentos"] / g["admissoes"].where(g["admissoes"] > 0)
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
display_cols = ["municipio","saldo","saldo_por_10k","giro_por_10k","salario_medio","anos_estudo"]
print(terr.sort_values("saldo_por_10k", ascending=False)[display_cols].head(10).to_string(index=False))

print("\\nTOP 10 RETRAÇÃO / APAGÃO (menor saldo por 10 mil hab.):")
print(terr.sort_values("saldo_por_10k")[display_cols].head(10).to_string(index=False))""")

code("""# Agregação por MESORREGIÃO (6 regiões de SC) — nível principal do mapa do dashboard
pop_meso = mun.groupby("mesorregiao")["populacao"].sum()
reg = agrega(["cod_meso", "mesorregiao"])
reg["populacao"]     = reg["mesorregiao"].map(pop_meso)
reg["saldo_por_10k"] = reg["saldo"] / reg["populacao"] * 10_000
reg["giro_por_10k"]  = reg["giro"]  / reg["populacao"] * 10_000
print(reg.sort_values("saldo_por_10k", ascending=False)
        [["mesorregiao","saldo","saldo_por_10k","giro_por_10k","reposicao",
          "salario_medio","anos_estudo","pct_superior"]].round(3).to_string(index=False))""")

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
             "salario_medio","anos_estudo","industrial"]].to_string(index=False))""")

code("""# Cruzamento território × setor (onde cada setor cresce/encolhe)
terr_setor = agrega(["mun_cod","municipio","seção","setor"])
terr_setor = terr_setor.merge(pop_mun.rename("populacao"), on="mun_cod", how="left")
terr_setor["saldo_por_10k"] = terr_setor["saldo"] / terr_setor["populacao"] * 10_000
# Exemplo: maiores polos industriais por saldo
ind = terr_setor[terr_setor["seção"].isin(SETORES_INDUSTRIAIS)]
print("Maiores saldos industriais (município × setor):")
print(ind.sort_values("saldo", ascending=False)
        [["municipio","setor","saldo","salario_medio","anos_estudo"]].head(15).to_string(index=False))""")

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

**Problema:** o CAGED-SC tem **2.207 CBOs distintos** — impossível analisar ocupação por
ocupação. A estrutura oficial da CBO (1º dígito = Grande Grupo) separa por *nível*, mas não
por *cadeia industrial*: soldador, costureira e magarefe caem todos no mesmo grupo "7/8".
Para responder *"o apagão é operacional ou técnico? em qual indústria?"* precisamos de
macrofamílias pensadas para a indústria catarinense.

**Como fizemos (IA Generativa):**
1. Montamos a lista `código | título` dos 2.207 CBOs (títulos do dicionário oficial; 28 CBOs
   sem título receberam como contexto os títulos da mesma família CBO) → `ia/cbos_para_classificar.csv`.
2. Escrevemos um prompt com **14 macrofamílias fixas** e regras de desempate →
   `ia/prompt_classificacao_cbo.md`. Cada CBO recebe: `macrofamilia`, `nivel`
   (operacional / técnico / superior / gestão) e `industrial` (S/N).
3. Enviamos ao LLM (**Claude Opus 5.5**) em **5 lotes de ~440 CBOs**, exigindo resposta CSV
   com os mesmos códigos e na mesma ordem; cada lote foi validado automaticamente
   (códigos idênticos, valores dentro do domínio).
4. Resultado versionado em `ia/cbo_macrofamilias.csv` — o notebook **não chama API**
   (reprodutível, sem custo, sem depender de rede). Para refazer via API:
   `python ia/classificar_cbos.py`.
5. **Validação:** `python ia/validar_classificacao.py` (cobertura, coerência com o Grande
   Grupo oficial, amostra para revisão humana em `ia/amostra_revisao.csv`).
""")

code("""# 8.1 Carrega a classificação gerada pelo LLM
NOMES_MACRO = {
    "OP_METAL":  "Operacional – Metalmecânica e eletroeletrônica",
    "OP_TEXTIL": "Operacional – Têxtil, confecção e calçados",
    "OP_ALIM":   "Operacional – Alimentos, bebidas e agroindústria",
    "OP_OUTRAS": "Operacional – Outras indústrias de transformação",
    "CONSTR":    "Construção civil e infraestrutura",
    "MANUT":     "Manutenção, reparação e instalação",
    "LOGIST":    "Logística, transporte e armazenagem",
    "TEC_IND":   "Técnicos industriais, de TI e qualidade",
    "ENG_TI":    "Engenharia, TI e ciências (superior)",
    "GESTAO":    "Gestão, supervisão e liderança",
    "ADM":       "Administrativo e escritório",
    "COMERCIO":  "Comércio, vendas e atendimento",
    "SERV":      "Serviços (saúde, educação, alimentação etc.)",
    "AGRO":      "Agropecuária, pesca e florestal",
    "NAO_CLASSIFICADO": "Não classificado",
}
cbo_ia = pd.read_csv(CBO_IA, dtype=str)
cbo_ia["macrofamilia_nome"] = cbo_ia["macrofamilia"].map(NOMES_MACRO)
titulos = pd.read_csv(CBO_ENTRADA, dtype={"cbo": str})[["cbo", "titulo"]]
cbo_ia = cbo_ia.merge(titulos, on="cbo", how="left")
print("CBOs classificados:", len(cbo_ia))
print(cbo_ia["macrofamilia"].value_counts().to_string())

# Exemplos de como o LLM classificou
cbo_ia[cbo_ia["cbo"].isin(["724315","763215","848520","784205","214905","313410","717020","782510"])]""")

code("""# 8.2 Junta a classificação às movimentações
dfm = dfm.merge(cbo_ia[["cbo","macrofamilia","macrofamilia_nome","nivel"]]
                  .rename(columns={"nivel": "nivel_ocup"}),
                on="cbo", how="left")
cobertura = dfm["macrofamilia"].notna().mean()
print(f"Movimentações com macrofamília: {cobertura:.2%}")
assert cobertura > 0.999""")

code("""# 8.3 Validação rápida: coerência com a estrutura oficial da CBO (1º dígito = Grande Grupo)
GG_ESPERADO = {"ENG_TI": {"2"}, "TEC_IND": {"3"}, "AGRO": {"6"}, "CONSTR": {"7"},
               "OP_METAL": {"7","8"}, "OP_TEXTIL": {"7","8"}, "OP_ALIM": {"7","8"},
               "OP_OUTRAS": {"7","8"}, "MANUT": {"7","9"}}
gg = cbo_ia["cbo"].str[0]
coerente = [g in GG_ESPERADO.get(m, {g}) for g, m in zip(gg, cbo_ia["macrofamilia"])]
print(f"Coerência com o Grande Grupo oficial: {np.mean(coerente):.1%} dos CBOs")
print("Divergências não são necessariamente erros (ex.: 'Auxiliar de Produção Farmacêutica'"
      " está no GG 5 da CBO, mas é trabalho fabril) — são a lista para revisão humana.")""")

code("""# 8.4 Macrofamílias: saldo, rotatividade, renda e escolaridade
macro = agrega(["macrofamilia", "macrofamilia_nome"])
macro["n_cbos"] = macro["macrofamilia"].map(cbo_ia["macrofamilia"].value_counts())
print(macro.sort_values("giro", ascending=False)
        [["macrofamilia_nome","n_cbos","admissoes","desligamentos","saldo","reposicao",
          "salario_medio","anos_estudo","pct_superior"]].round(3).to_string(index=False))""")

code("""# 8.5 O que a IA revela que o Grande Grupo esconde:
# no baseline, todo o operacional industrial é um bloco só (GG 7/8)
GRANDE_GRUPO_CBO = {"0": "Forças Armadas", "1": "Dirigentes", "2": "Prof. nível superior",
                    "3": "Técnicos nível médio", "4": "Apoio administrativo",
                    "5": "Serviços e comércio", "6": "Agropecuária",
                    "7": "Produção industrial (7)", "8": "Produção industrial (8)",
                    "9": "Manutenção"}
dfm["cbo_grande_grupo"] = dfm["cbo"].str[0].map(GRANDE_GRUPO_CBO)
oper = dfm[dfm["cbo_grande_grupo"].str.startswith("Produção")]
print("Dentro do bloco 'Produção industrial' (GG 7/8), a IA separa:")
print(oper.groupby("macrofamilia_nome")
        .agg(movs=("saldo","size"), saldo=("saldo","sum"), salario_medio=("salario","mean"))
        .sort_values("movs", ascending=False).round(0).to_string())""")

code("""# 8.6 Macrofamília × mesorregião (onde está o gargalo de cada família ocupacional)
macro_reg = agrega(["cod_meso","mesorregiao","macrofamilia","macrofamilia_nome"])
macro_reg["populacao"] = macro_reg["mesorregiao"].map(pop_meso)
macro_reg["saldo_por_10k"] = macro_reg["saldo"] / macro_reg["populacao"] * 10_000
# Sinais de apagão: muita movimentação + reposição ~1 (contrata só para repor)
sinais = macro_reg[(macro_reg["giro"] > 5000) & (macro_reg["macrofamilia"].str.startswith(("OP_","TEC","ENG","MANUT")))]
print(sinais.sort_values("reposicao", ascending=False)
        [["mesorregiao","macrofamilia_nome","giro","saldo","reposicao","salario_medio","anos_estudo"]]
        .head(15).round(3).to_string(index=False))""")

# ------------------------------------------------------------------ 9. EXPORT
md("""## 9. Exportação das tabelas-base (consumidas pelo dashboard)

Gravamos agregações enxutas em `outputs/` — são elas que o dashboard (Entregável 2) carrega.
O **cubo** (`cubo_movimentacoes.parquet`) guarda somas por município × seção CNAE ×
macrofamília × nível × tipo de movimento, permitindo ao dashboard recalcular qualquer recorte
(região, setor, família) sem reler os 3,4 milhões de linhas.
""")

code("""# Cubo de somas (médias são recalculadas no dashboard como soma/contagem)
dfm["tipo"] = np.where(dfm["saldo"] > 0, "ADM", "DESL")
cubo = (dfm.groupby(["mun_cod","seção","macrofamilia","nivel_ocup","tipo"], dropna=False)
          .agg(n=("saldo","size"),
               a_pedido=("a_pedido","sum"),  demissao=("demissao","sum"),
               sal_soma=("salario","sum"),   sal_n=("salario","count"),
               anos_soma=("anos_estudo","sum"), anos_n=("anos_estudo","count"),
               sup_soma=("superior","sum"),  sup_n=("superior","count"))
          .reset_index())
print("Cubo:", cubo.shape, "| soma de n =", cubo["n"].sum(), "(deve = nº de movimentações)")
assert cubo["n"].sum() == len(dfm)

# Escolaridade × tipo de movimento por mesorregião (perfil admitido × desligado, salário por grau)
esc_reg = (dfm.groupby(["mesorregiao","tipo","grau_cod","grau_instr"], dropna=False)
             .agg(n=("saldo","size"), sal_soma=("salario","sum"), sal_n=("salario","count"))
             .reset_index())

# Série mensal (mês do fato, restrita à janela de declaração set/2025–ago/2026)
serie = (dfm[dfm["competênciamov"].between("202509", "202608")]
           .groupby(["competênciamov","mesorregiao","macrofamilia"])
           .agg(admissoes=("admissao","sum"), desligamentos=("desligamento","sum"),
                saldo=("saldo","sum"))
           .reset_index())

saidas = {
    "escolaridade_regiao.parquet":  esc_reg,
    "serie_mensal.parquet":         serie,
    "agg_municipio.parquet":        terr,
    "agg_mesorregiao.parquet":      reg,
    "agg_setor.parquet":            setor,
    "agg_municipio_setor.parquet":  terr_setor,
    "perfil_adm_desl.parquet":      perfil,
    "salario_por_grau.parquet":     sal_grau,
    "macrofamilias_cbo.parquet":    macro,
    "macrofamilia_mesorregiao.parquet": macro_reg,
    "cubo_movimentacoes.parquet":   cubo,
    "municipios.parquet":           mun,
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
- **IA/CBO**: as macrofamílias geradas pelo LLM mostram se o gargalo é **operacional**
  (e de qual cadeia: metalmecânica, têxtil, alimentos...) ou **técnico/engenharia** —
  base direta para as recomendações do pitch.

> **Limites da análise:** saldo e giro usam o próprio CAGED (fluxo, não estoque de vínculos);
> exclusões (arquivo EXC) não foram fornecidas; IDHM é de 2010; salários fora de
> R$ 500–50.000 foram ignorados nas médias; anos de estudo são aproximação do grau de
> instrução; promoções internas não aparecem no CAGED (o saldo negativo de Gestão/supervisão
> pode refletir vagas preenchidas internamente, não só cortes); a classificação de CBOs por LLM pode errar em ocupações ambíguas (validada por
> coerência com a CBO oficial e por amostra revisada pela equipe).
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
for i, (kind, text) in enumerate(cells):
    src = text.splitlines(keepends=True)
    cid = f"cell-{i:02d}"  # ids estáveis (exigidos pelo nbformat 4.5)
    if kind == "markdown":
        nb["cells"].append({"cell_type": "markdown", "id": cid, "metadata": {}, "source": src})
    else:
        nb["cells"].append({"cell_type": "code", "id": cid, "metadata": {},
                             "execution_count": None, "outputs": [], "source": src})

out = Path(__file__).with_name("01_pipeline_caged_sc.ipynb")
out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("Notebook gerado:", out, "com", len(cells), "células")
