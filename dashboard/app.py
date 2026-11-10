"""
Dashboard Analítico — Datathon CDIA 2026
Raio-X do Mercado de Trabalho e Vagas Industriais em Santa Catarina

Entregável 2. Consome as tabelas-base geradas pelo pipeline
(notebooks/01_pipeline_caged_sc.ipynb -> outputs/*.parquet).

Execução:
    pip install -r dashboard/requirements.txt
    streamlit run dashboard/app.py
"""
import os
import pandas as pd
import streamlit as st
import plotly.express as px

# --------------------------------------------------------------------------- #
# Configuração
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="Raio-X do Trabalho Industrial — SC",
    page_icon="📊",
    layout="wide",
)

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
OUTPUTS = os.path.join(BASE, "outputs")

SETORES_INDUSTRIAIS = {"B", "C", "D", "F"}


# --------------------------------------------------------------------------- #
# Carga de dados (com cache)
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def carregar(nome):
    caminho = os.path.join(OUTPUTS, f"{nome}.parquet")
    if not os.path.exists(caminho):
        return None
    return pd.read_parquet(caminho)


def checar_dados():
    faltando = [n for n in [
        "agg_municipio", "agg_setor", "agg_municipio_setor",
        "perfil_adm_desl", "salario_por_grau", "macrofamilias_cbo",
    ] if carregar(n) is None]
    if faltando:
        st.error(
            "Tabelas-base não encontradas em `outputs/`: "
            + ", ".join(faltando)
            + ".\n\nExecute o pipeline primeiro:\n\n"
            "`jupyter nbconvert --to notebook --execute --inplace "
            "notebooks/01_pipeline_caged_sc.ipynb`"
        )
        st.stop()


checar_dados()

mun = carregar("agg_municipio")
setor = carregar("agg_setor")
mun_setor = carregar("agg_municipio_setor")
perfil = carregar("perfil_adm_desl")
sal_grau = carregar("salario_por_grau")
macro = carregar("macrofamilias_cbo")


# --------------------------------------------------------------------------- #
# Cabeçalho + pergunta de negócio
# --------------------------------------------------------------------------- #
st.title("📊 Raio-X do Mercado de Trabalho Industrial — Santa Catarina")
st.caption(
    "Datathon CDIA 2026 · Microdados do Novo CAGED (24 meses) cruzados com dados municipais"
)
st.info(
    "**Pergunta central:** Quais regiões e setores industriais de SC enfrentam "
    "**apagão de mão de obra** ou **expansão acelerada**, e como **renda e escolaridade** "
    "explicam esses gargalos?"
)

# --------------------------------------------------------------------------- #
# Filtros (sidebar)
# --------------------------------------------------------------------------- #
st.sidebar.header("Filtros")
apenas_ind = st.sidebar.checkbox(
    "Apenas setores industriais (B, C, D, F)", value=False,
    help="Extrativas, Transformação, Eletricidade/Gás e Construção",
)

setores_disp = setor.sort_values("saldo", ascending=False)
if apenas_ind:
    setores_disp = setores_disp[setores_disp["industrial"]]
opcoes_setor = setores_disp["setor"].tolist()
setores_sel = st.sidebar.multiselect(
    "Setores (CNAE)", options=opcoes_setor, default=opcoes_setor,
)

min_pop = st.sidebar.slider(
    "População mínima do município", 0, int(mun["populacao"].max()), 0, step=1000,
    help="Filtra municípios pequenos para reduzir ruído nas taxas por 10 mil hab.",
)

secoes_sel = set(setor[setor["setor"].isin(setores_sel)]["seção"])

# Views filtradas
mun_f = mun[mun["populacao"] >= min_pop].copy()
ms_f = mun_setor[
    mun_setor["seção"].isin(secoes_sel)
    & (mun_setor["populacao"].fillna(0) >= min_pop)
].copy()
setor_f = setor[setor["seção"].isin(secoes_sel)].copy()

# Saldo por município respeitando o filtro de setores
saldo_mun_filtrado = (
    ms_f.groupby(["mun_cod", "municipio"], as_index=False)
    .agg(saldo=("saldo", "sum"), giro=("giro", "sum"),
         admissoes=("admissoes", "sum"), desligamentos=("desligamentos", "sum"))
    .merge(mun_f[["mun_cod", "populacao", "idhm", "escolarizacao",
                  "salario_medio", "grau_medio"]], on="mun_cod", how="left")
)
saldo_mun_filtrado["saldo_por_10k"] = (
    saldo_mun_filtrado["saldo"] / saldo_mun_filtrado["populacao"] * 10_000
)
saldo_mun_filtrado["giro_por_10k"] = (
    saldo_mun_filtrado["giro"] / saldo_mun_filtrado["populacao"] * 10_000
)

# --------------------------------------------------------------------------- #
# KPIs (mínimo 3 exigidos)
# --------------------------------------------------------------------------- #
total_adm = int(setor_f["admissoes"].sum())
total_desl = int(setor_f["desligamentos"].sum())
saldo_total = int(setor_f["saldo"].sum())
sal_medio = (
    (setor_f["salario_medio"] * setor_f["movimentacoes"]).sum()
    / setor_f["movimentacoes"].sum()
) if setor_f["movimentacoes"].sum() else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Saldo de vagas", f"{saldo_total:+,}".replace(",", "."))
c2.metric("Admissões", f"{total_adm:,}".replace(",", "."))
c3.metric("Desligamentos", f"{total_desl:,}".replace(",", "."))
c4.metric("Salário médio", f"R$ {sal_medio:,.0f}".replace(",", "."))
c5.metric("Municípios", f"{saldo_mun_filtrado['mun_cod'].nunique()}")

st.divider()

# --------------------------------------------------------------------------- #
# Abas de storytelling
# --------------------------------------------------------------------------- #
aba_terr, aba_setor, aba_socio, aba_cbo = st.tabs(
    ["🗺️ Território", "🏭 Setores", "🎓 Renda × Escolaridade", "🤖 Macrofamílias (IA)"]
)

# ----------------------------------------------------------------- Território
with aba_terr:
    st.subheader("Onde estão os polos de expansão e o apagão de mão de obra")
    st.caption(
        "Saldo por 10 mil habitantes normaliza a comparação entre cidades de portes "
        "diferentes. Giro alto com saldo baixo/negativo sinaliza apagão (rotatividade)."
    )
    col_a, col_b = st.columns(2)
    with col_a:
        top_exp = saldo_mun_filtrado.sort_values("saldo_por_10k", ascending=False).head(15)
        fig = px.bar(
            top_exp, x="saldo_por_10k", y="municipio", orientation="h",
            color="saldo_por_10k", color_continuous_scale="Greens",
            title="Top 15 — Expansão acelerada (saldo / 10 mil hab.)",
            labels={"saldo_por_10k": "Saldo por 10 mil hab.", "municipio": ""},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
        st.plotly_chart(fig, width="stretch")
    with col_b:
        top_apg = saldo_mun_filtrado.sort_values("saldo_por_10k").head(15)
        fig = px.bar(
            top_apg, x="saldo_por_10k", y="municipio", orientation="h",
            color="saldo_por_10k", color_continuous_scale="Reds_r",
            title="Top 15 — Retração / apagão (saldo / 10 mil hab.)",
            labels={"saldo_por_10k": "Saldo por 10 mil hab.", "municipio": ""},
        )
        fig.update_layout(yaxis={"categoryorder": "total descending"}, height=500)
        st.plotly_chart(fig, width="stretch")

    st.markdown("**Expansão vs. rotatividade** — bolhas no alto à direita = apagão (giro alto)")
    disp = saldo_mun_filtrado[saldo_mun_filtrado["populacao"] > 0].copy()
    fig = px.scatter(
        disp, x="saldo_por_10k", y="giro_por_10k",
        size="populacao", color="salario_medio",
        hover_name="municipio", color_continuous_scale="Viridis",
        labels={"saldo_por_10k": "Saldo por 10 mil hab.",
                "giro_por_10k": "Giro (adm+desl) por 10 mil hab.",
                "salario_medio": "Salário médio"},
        height=520,
    )
    st.plotly_chart(fig, width="stretch")

# --------------------------------------------------------------------- Setores
with aba_setor:
    st.subheader("Setores que lideram a criação e a destruição de vagas")
    s = setor_f.sort_values("saldo")
    fig = px.bar(
        s, x="saldo", y="setor", orientation="h", color="industrial",
        color_discrete_map={True: "#1f77b4", False: "#aec7e8"},
        title="Saldo de vagas por setor (CNAE) — azul-escuro = industrial",
        labels={"saldo": "Saldo de vagas", "setor": "", "industrial": "Industrial"},
    )
    fig.update_layout(height=600)
    st.plotly_chart(fig, width="stretch")

    st.markdown("**Maiores polos industriais (município × setor)**")
    ind = ms_f[ms_f["seção"].isin(SETORES_INDUSTRIAIS)]
    if not ind.empty:
        top_ind = ind.sort_values("saldo", ascending=False).head(20)
        st.dataframe(
            top_ind[["municipio", "setor", "saldo", "admissoes", "desligamentos",
                     "salario_medio", "grau_medio"]]
            .rename(columns={"salario_medio": "salário médio",
                             "grau_medio": "escolaridade média (cód.)"}),
            width="stretch", hide_index=True,
        )
    else:
        st.caption("Nenhum setor industrial selecionado nos filtros.")

# ------------------------------------------------------------ Renda x Escolar.
with aba_socio:
    st.subheader("A causa-raiz: renda e escolaridade")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Salário médio por grau de instrução** (há compressão salarial?)")
        sg = sal_grau.sort_values("grau_cod")
        fig = px.bar(
            sg, x="grau", y="salario_medio",
            labels={"grau": "Grau de instrução", "salario_medio": "Salário médio (R$)"},
            color="salario_medio", color_continuous_scale="Blues",
        )
        fig.update_layout(xaxis={"tickangle": -40}, height=430)
        st.plotly_chart(fig, width="stretch")
    with col_b:
        st.markdown("**Admitidos vs. desligados por escolaridade**")
        fig = px.bar(
            perfil, x="grau_instr", y="n", color="mov", barmode="group",
            labels={"grau_instr": "Grau de instrução", "n": "Movimentações", "mov": ""},
            color_discrete_map={"Admitido": "#2ca02c", "Desligado": "#d62728"},
        )
        fig.update_layout(xaxis={"tickangle": -40}, height=430)
        st.plotly_chart(fig, width="stretch")

    st.markdown(
        "**Dispersão municipal — salário × escolaridade** "
        "(tamanho = saldo absoluto, cor = saldo por 10 mil hab.)"
    )
    d = saldo_mun_filtrado.dropna(subset=["salario_medio", "grau_medio"]).copy()
    d["saldo_abs"] = d["saldo"].abs() + 1
    fig = px.scatter(
        d, x="salario_medio", y="grau_medio",
        size="saldo_abs", color="saldo_por_10k",
        hover_name="municipio", color_continuous_scale="RdYlGn",
        labels={"salario_medio": "Salário médio (R$)",
                "grau_medio": "Escolaridade média (código 1–11)",
                "saldo_por_10k": "Saldo / 10 mil hab."},
        height=520,
    )
    st.plotly_chart(fig, width="stretch")

# ------------------------------------------------------------------- CBO / IA
with aba_cbo:
    st.subheader("Macrofamílias ocupacionais (agrupamento de CBOs via IA)")
    st.caption(
        "Os 2.207 CBOs foram agrupados em macrofamílias. Saldo negativo em famílias de "
        "alta qualificação revela se o apagão é técnico/engenharia ou operacional."
    )
    m = macro.sort_values("saldo")
    fig = px.bar(
        m, x="saldo", y="cbo_grande_grupo", orientation="h", color="saldo",
        color_continuous_scale="RdYlGn",
        labels={"saldo": "Saldo de vagas", "cbo_grande_grupo": ""},
        title="Saldo de vagas por macrofamília ocupacional",
    )
    fig.update_layout(height=480)
    st.plotly_chart(fig, width="stretch")

    st.markdown("**Salário × escolaridade por macrofamília** (tamanho = nº de CBOs)")
    fig = px.scatter(
        macro, x="salario_medio", y="grau_medio", size="n_cbos",
        color="saldo", color_continuous_scale="RdYlGn",
        hover_name="cbo_grande_grupo",
        labels={"salario_medio": "Salário médio (R$)",
                "grau_medio": "Escolaridade média (código)",
                "saldo": "Saldo", "n_cbos": "nº CBOs"},
        height=460,
    )
    st.plotly_chart(fig, width="stretch")

    st.dataframe(
        macro.sort_values("saldo")
        .rename(columns={"cbo_grande_grupo": "macrofamília",
                         "salario_medio": "salário médio",
                         "grau_medio": "escolaridade média (cód.)",
                         "n_cbos": "nº CBOs"}),
        width="stretch", hide_index=True,
    )

st.divider()
st.caption(
    "Fonte: Novo CAGED-SC (24 meses) + dados municipais. "
    "Limites: saldo/giro refletem fluxo (não estoque de vínculos); IDHM é de 2010; "
    "salários declarados podem conter outliers."
)
