"""Carga das tabelas do pipeline (outputs/) e cálculo de indicadores por recorte.

Todas as páginas de visualização usam este módulo. As tabelas são geradas pelo notebook
`notebooks/01_pipeline_caged_sc.ipynb`; a principal é o **cubo** de movimentações
(município × seção CNAE × macrofamília × nível × tipo), que permite recalcular qualquer
indicador para Santa Catarina inteira ou para uma mesorregião sem reler os microdados.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
DATASET = ROOT / "dataset"

SETORES_INDUSTRIAIS = {"B", "C", "D", "F"}

NOMES_MACRO = {
    "OP_METAL": "Operacional: metalmecânica e eletroeletrônica",
    "OP_TEXTIL": "Operacional: têxtil, confecção e calçados",
    "OP_ALIM": "Operacional: alimentos, bebidas e agroindústria",
    "OP_OUTRAS": "Operacional: outras indústrias de transformação",
    "CONSTR": "Construção civil e infraestrutura",
    "MANUT": "Manutenção, reparação e instalação",
    "LOGIST": "Logística, transporte e armazenagem",
    "TEC_IND": "Técnicos industriais, de TI e qualidade",
    "ENG_TI": "Engenharia, TI e ciências (superior)",
    "GESTAO": "Gestão, supervisão e liderança",
    "ADM": "Administrativo e escritório",
    "COMERCIO": "Comércio, vendas e atendimento",
    "SERV": "Serviços (saúde, educação, alimentação etc.)",
    "AGRO": "Agropecuária, pesca e florestal",
    "NAO_CLASSIFICADO": "Não classificado",
}
# famílias ligadas à produção industrial (foco das recomendações)
MACRO_INDUSTRIAIS = ["OP_METAL", "OP_TEXTIL", "OP_ALIM", "OP_OUTRAS", "TEC_IND", "ENG_TI", "MANUT"]

TABELAS = [
    "cubo_movimentacoes", "municipios", "agg_municipio", "agg_mesorregiao",
    "agg_municipio_setor", "agg_setor", "escolaridade_regiao", "serie_mensal",
    "macrofamilias_cbo", "macrofamilia_mesorregiao",
]


# --------------------------------------------------------------------------- carga
@st.cache_data(show_spinner=False)
def carregar(nome: str) -> pd.DataFrame | None:
    caminho = OUTPUTS / f"{nome}.parquet"
    return pd.read_parquet(caminho) if caminho.exists() else None


def checar_tabelas() -> None:
    """Interrompe a página com instruções se o pipeline ainda não foi executado."""
    faltando = [t for t in TABELAS if carregar(t) is None]
    if faltando:
        st.error(
            "Tabelas do pipeline não encontradas em `outputs/`: "
            + ", ".join(f"`{t}`" for t in faltando)
            + "\n\nExecute o notebook: `jupyter nbconvert --to notebook --execute --inplace "
            "notebooks/01_pipeline_caged_sc.ipynb`",
            icon=":material/error:",
        )
        st.stop()


@st.cache_data(show_spinner=False)
def cubo() -> pd.DataFrame:
    """Cubo com mesorregião anexada (via tabela de municípios)."""
    c = carregar("cubo_movimentacoes")
    m = carregar("municipios")[["mun_cod", "municipio", "mesorregiao"]]
    return c.merge(m, on="mun_cod", how="left")


@st.cache_data(show_spinner=False)
def coordenadas() -> pd.DataFrame | None:
    caminho = DATASET / "municipios_sc_coords.parquet"
    if not caminho.exists():
        return None
    c = pd.read_parquet(caminho)
    c["mun_cod"] = c["mun_cod"].astype(str)
    return c[["mun_cod", "lat", "lon"]]


# ------------------------------------------------------------------- indicadores
def recorte(df: pd.DataFrame, regiao: str | None, apenas_industria: bool = False) -> pd.DataFrame:
    if regiao:
        df = df[df["mesorregiao"] == regiao]
    if apenas_industria and "seção" in df.columns:
        df = df[df["seção"].isin(SETORES_INDUSTRIAIS)]
    return df


def populacao(regiao: str | None) -> float:
    m = carregar("municipios")
    return float(m.loc[m["mesorregiao"] == regiao, "populacao"].sum() if regiao else m["populacao"].sum())


def indicadores(c: pd.DataFrame) -> pd.Series:
    """Indicadores a partir de um recorte do cubo (somas -> médias ponderadas)."""
    adm = c.loc[c["tipo"] == "ADM"]
    desl = c.loc[c["tipo"] == "DESL"]
    n_adm, n_desl = adm["n"].sum(), desl["n"].sum()

    def media(parte, soma, cont):
        d = parte[cont].sum()
        return parte[soma].sum() / d if d else float("nan")

    return pd.Series({
        "admissoes": n_adm,
        "desligamentos": n_desl,
        "saldo": n_adm - n_desl,
        "movimentacoes": n_adm + n_desl,
        "reposicao": n_desl / n_adm if n_adm else float("nan"),
        "pct_a_pedido": desl["a_pedido"].sum() / n_desl if n_desl else float("nan"),
        "salario_adm": media(adm, "sal_soma", "sal_n"),
        "salario_desl": media(desl, "sal_soma", "sal_n"),
        "salario_medio": media(c, "sal_soma", "sal_n"),
        "anos_estudo": media(c, "anos_soma", "anos_n"),
        "pct_superior": media(c, "sup_soma", "sup_n"),
    })


def por_grupo(c: pd.DataFrame, chaves: list[str]) -> pd.DataFrame:
    """Indicadores por grupo (ex.: por macrofamília, por seção)."""
    if c.empty:
        return pd.DataFrame(columns=chaves)
    return c.groupby(chaves).apply(indicadores, include_groups=False).reset_index()


# --------------------------------------------------------------------- formato
def fmt_int(v, sinal=False) -> str:
    if pd.isna(v):
        return "-"
    return (f"{int(round(v)):+,}" if sinal else f"{int(round(v)):,}").replace(",", ".")


def fmt_dec(v, casas=1, sinal=False) -> str:
    if pd.isna(v):
        return "-"
    s = f"{v:+,.{casas}f}" if sinal else f"{v:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(v, casas=0) -> str:
    return "-" if pd.isna(v) else fmt_dec(v * 100, casas) + "%"


def fmt_reais(v) -> str:
    return "-" if pd.isna(v) else "R$ " + fmt_int(v)
