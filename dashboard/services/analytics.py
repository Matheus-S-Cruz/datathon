"""Tabelas analíticas do painel: saídas do pipeline (`outputs/`) + bases do IBGE (`data/external/`).

As páginas do CAGED Explorer consultam o Parquet bruto pelo DuckDB (services/queries.py).
As páginas analíticas (Visão geral e Análises complementares) usam as agregações já
calculadas pelo pipeline `notebooks/01_pipeline_caged_sc.ipynb`, que são pequenas e
carregam instantaneamente. Os cálculos de filtro abaixo são os mesmos do dashboard
original (saldo e giro por 10 mil habitantes), agora com as métricas do IBGE.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
import pandas as pd
import streamlit as st

from src.config import COORDS_PARQUET, EXTERNAL_DIR, OUTPUTS_DIR

INDUSTRIAL_SECTIONS = ("B", "C", "D", "F")  # Extrativas, Transformação, Eletricidade/Gás, Construção
OUTPUT_TABLES = ("agg_municipio", "agg_setor", "agg_municipio_setor", "perfil_adm_desl",
                 "salario_por_grau", "macrofamilias_cbo", "macrofamilias_industria", "agg_regiao")
REGION_LEVELS = {"regiao_intermediaria": "Região geográfica intermediária",
                 "regiao_imediata": "Região geográfica imediata"}


class MissingOutputs(RuntimeError):
    pass


@st.cache_data(show_spinner=False)
def table(name: str) -> pd.DataFrame:
    path = OUTPUTS_DIR / f"{name}.parquet"
    if not path.exists():
        raise MissingOutputs(
            f"Tabela-base `outputs/{name}.parquet` não encontrada. Execute o pipeline: "
            "`jupyter nbconvert --to notebook --execute --inplace notebooks/01_pipeline_caged_sc.ipynb`")
    df = pd.read_parquet(path)
    return df.rename(columns={"seção": "secao"})


def missing_outputs() -> list[str]:
    return [n for n in OUTPUT_TABLES if not (OUTPUTS_DIR / f"{n}.parquet").exists()]


@st.cache_data(show_spinner=False)
def coords() -> pd.DataFrame | None:
    if not COORDS_PARQUET.exists():
        return None
    c = pd.read_parquet(COORDS_PARQUET)
    c["mun_cod"] = c["mun_cod"].astype(str)
    return c[["mun_cod", "lat", "lon"]]


@st.cache_data(show_spinner=False)
def geojson() -> dict | None:
    """Malha municipal do IBGE com `id` = código de 6 dígitos (o mesmo do CAGED)."""
    path = EXTERNAL_DIR / "ibge_malha_sc.geojson"
    if not path.exists():
        return None
    geo = json.loads(path.read_text(encoding="utf-8"))
    for feat in geo["features"]:
        feat["id"] = feat["properties"]["codarea"][:6]
        _rewind(feat["geometry"])
    return geo


def _signed_area(ring: list) -> float:
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1])) / 2


def _rewind(geometry: dict) -> None:
    """A malha do IBGE segue a RFC 7946 (anel externo anti-horário); o go.Choropleth do Plotly
    (d3-geo) espera o externo no sentido horário — sem isso, cada município vira "o mundo menos ele"."""
    polys = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    for poly in polys:
        for i, ring in enumerate(poly):
            exterior = i == 0
            if (_signed_area(ring) > 0) == exterior:   # externo anti-horário ou buraco horário
                ring.reverse()


@st.cache_data(show_spinner=False)
def external_sources() -> dict:
    path = EXTERNAL_DIR / "fontes.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


@st.cache_data(show_spinner=False)
def sectors() -> pd.DataFrame:
    s = table("agg_setor").copy()
    s["industrial"] = s["secao"].isin(INDUSTRIAL_SECTIONS)
    return s.sort_values("saldo", ascending=False)


# ----------------------------------------------------------------- filtros


@dataclass(frozen=True)
class Scope:
    """Recorte usado pelas páginas analíticas (barra lateral)."""
    secoes: tuple[str, ...] = ()          # vazio = todas
    min_pop: int = 0
    regiao: str | None = None            # região geográfica intermediária

    @property
    def all_sections(self) -> bool:
        return not self.secoes or set(self.secoes) == set(sectors()["secao"])

    def describe(self) -> list[str]:
        items = []
        if not self.all_sections:
            ind = set(self.secoes) == set(INDUSTRIAL_SECTIONS)
            items.append("setores industriais (B, C, D, F)" if ind else f"{len(self.secoes)} seções CNAE")
        if self.regiao:
            items.append(f"região {self.regiao}")
        if self.min_pop:
            items.append(f"municípios com {self.min_pop:,} hab. ou mais".replace(",", "."))
        return items


def _weighted(df: pd.DataFrame, col: str, by: str | list[str]) -> pd.Series:
    d = df.dropna(subset=[col])
    return d.groupby(by).apply(lambda g: np.average(g[col], weights=g["movimentacoes"]),
                               include_groups=False).rename(col)


@st.cache_data(show_spinner=False)
def municipal(scope: Scope) -> pd.DataFrame:
    """Uma linha por município, respeitando o recorte de setores, região e população.

    - Todas as seções: usa `agg_municipio` (inclui taxas sobre o estoque do CEMPRE).
    - Recorte setorial: soma `agg_municipio_setor` nas seções escolhidas. Nesse caso as taxas
      sobre o estoque (crescimento e rotatividade) ficam vazias, porque o CEMPRE municipal
      não é aberto por setor — dividir o saldo de um setor pelo emprego total seria enganoso.
    """
    base = table("agg_municipio")
    if scope.all_sections:
        df = base.copy()
    else:
        ms = table("agg_municipio_setor")
        ms = ms[ms["secao"].isin(scope.secoes)]
        sums = ms.groupby(["mun_cod", "municipio"], as_index=False)[
            ["admissoes", "desligamentos", "saldo", "movimentacoes", "giro"]].sum()
        for col in ["salario_medio", "grau_medio", "pct_superior"]:
            sums = sums.merge(_weighted(ms, col, "mun_cod"), left_on="mun_cod", right_index=True, how="left")
        keep = [c for c in base.columns if c not in sums.columns or c == "mun_cod"]
        df = sums.merge(base[keep], on="mun_cod", how="left")
        df["cresc_emprego_pct"] = np.nan
        df["rotatividade_pct"] = np.nan
    df = df[df["populacao"].fillna(0) >= scope.min_pop]
    if scope.regiao:
        df = df[df["regiao_intermediaria"] == scope.regiao]
    df = df.copy()
    df["saldo_por_10k"] = df["saldo"] / df["populacao"] * 10_000
    df["giro_por_10k"] = df["giro"] / df["populacao"] * 10_000
    return df


@st.cache_data(show_spinner=False)
def municipal_sector(scope: Scope) -> pd.DataFrame:
    ms = table("agg_municipio_setor")
    if not scope.all_sections:
        ms = ms[ms["secao"].isin(scope.secoes)]
    keep = municipal(Scope(min_pop=scope.min_pop, regiao=scope.regiao))["mun_cod"]
    return ms[ms["mun_cod"].isin(keep)].copy()


@st.cache_data(show_spinner=False)
def sectors_in_scope(scope: Scope) -> pd.DataFrame:
    """Setores no recorte. Com região ou população mínima, recalcula a partir de município × setor."""
    s = sectors()
    if scope.regiao or scope.min_pop:
        ms = municipal_sector(Scope(secoes=(), min_pop=scope.min_pop, regiao=scope.regiao))
        agg = ms.groupby("secao", as_index=False)[
            ["admissoes", "desligamentos", "saldo", "movimentacoes", "giro"]].sum()
        for col in ["salario_medio", "grau_medio", "pct_superior"]:
            agg = agg.merge(_weighted(ms, col, "secao"), left_on="secao", right_index=True, how="left")
        s = agg.merge(s[["secao", "setor", "industrial"]], on="secao", how="left")
    if not scope.all_sections:
        s = s[s["secao"].isin(scope.secoes)]
    return s.sort_values("saldo", ascending=False)


def kpis(scope: Scope) -> dict:
    mun = municipal(scope)
    sec = sectors_in_scope(scope)
    mov = sec["movimentacoes"].sum()
    out = {
        "saldo": int(sec["saldo"].sum()),
        "admissoes": int(sec["admissoes"].sum()),
        "desligamentos": int(sec["desligamentos"].sum()),
        "salario_medio": float((sec["salario_medio"] * sec["movimentacoes"]).sum() / mov) if mov else np.nan,
        "pct_superior": float((sec["pct_superior"] * sec["movimentacoes"]).sum() / mov) if mov else np.nan,
        "municipios": int(mun["mun_cod"].nunique()),
        "populacao": float(mun["populacao"].sum()),
    }
    out["saldo_por_10k"] = out["saldo"] / out["populacao"] * 10_000 if out["populacao"] else np.nan
    if scope.all_sections:
        estoque = mun["assalariados"].sum()
        out["cresc_emprego_pct"] = out["saldo"] / estoque * 100 if estoque else np.nan
        out["rotatividade_pct"] = min(out["admissoes"], out["desligamentos"]) / estoque * 100 if estoque else np.nan
        out["assalariados"] = float(estoque)
    else:
        out["cresc_emprego_pct"] = out["rotatividade_pct"] = out["assalariados"] = np.nan
    return out


@st.cache_data(show_spinner=False)
def regions(level: str = "regiao_intermediaria") -> pd.DataFrame:
    r = table("agg_regiao")
    return r[r["nivel"] == level].sort_values("cresc_emprego_pct", ascending=False).reset_index(drop=True)


def region_names() -> list[str]:
    return sorted(regions()["regiao"])


def macro(industrial_only: bool) -> pd.DataFrame:
    return table("macrofamilias_industria" if industrial_only else "macrofamilias_cbo").sort_values("saldo")
