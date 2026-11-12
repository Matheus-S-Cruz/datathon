"""Exploração e consulta — Tabelas analíticas geradas pelo pipeline e bases do IBGE, com download."""

import pandas as pd
import streamlit as st

from dashboard import formatting as fmt
from dashboard.components import tables, ui
from dashboard.services import analytics as A
from src.config import EXTERNAL_DIR

CATALOG = {
    "agg_municipio": "Municípios — CAGED agregado + indicadores municipais e IBGE",
    "agg_municipio_setor": "Município × seção CNAE",
    "agg_setor": "Seções CNAE",
    "agg_regiao": "Regiões geográficas (intermediárias e imediatas)",
    "macrofamilias_cbo": "Macrofamílias de ocupações (todos os setores)",
    "macrofamilias_industria": "Macrofamílias de ocupações (setores industriais)",
    "salario_por_grau": "Salário médio por grau de instrução",
    "perfil_adm_desl": "Admitidos × desligados por grau de instrução",
}
EXTERNAL = {
    "ibge_cempre_2024": "IBGE — CEMPRE 2024 (empresas, pessoal ocupado, salário)",
    "ibge_pib_municipal": "IBGE — PIB 2023 e VAB por atividade 2021",
    "ibge_regioes_sc": "IBGE — divisão regional dos municípios",
}
COLUMN_HELP = {
    "saldo": "Admissões − desligamentos.",
    "giro": "Admissões + desligamentos.",
    "saldo_por_10k": "Saldo ÷ população × 10.000.",
    "giro_por_10k": "Giro ÷ população × 10.000.",
    "grau_medio": "Escolaridade média na escala ordinal 1 (analfabeto) a 12 (doutorado); 'não identificado' fora.",
    "pct_superior": "Fração das movimentações com superior completo, pós, mestrado ou doutorado.",
    "cresc_emprego_pct": "Saldo ÷ assalariados CEMPRE 2024 × 100.",
    "rotatividade_pct": "Mín(admissões, desligamentos) ÷ assalariados CEMPRE 2024 × 100 (conceito DIEESE).",
    "part_industria_vab_2021": "VAB da indústria ÷ VAB total, 2021.",
}


def main() -> None:
    ui.header("Tabelas analíticas",
              "As tabelas-base geradas pelo pipeline e as bases públicas do IBGE, prontas para consulta e download.",
              eyebrow="Exploração e consulta")
    origem = st.segmented_control("Origem", ["Pipeline (outputs/)", "IBGE (data/external/)"],
                                  default="Pipeline (outputs/)", key="tb_origem") or "Pipeline (outputs/)"
    catalog = CATALOG if origem.startswith("Pipeline") else EXTERNAL
    name = st.selectbox("Tabela", list(catalog), format_func=lambda n: f"{catalog[n]}  ·  {n}", key="tb_name")
    df = A.table(name) if origem.startswith("Pipeline") else pd.read_parquet(EXTERNAL_DIR / f"{name}.parquet")

    busca = st.text_input("Filtrar linhas (texto em qualquer coluna)", key="tb_busca",
                          placeholder="ex.: Joinville, Transformação, Blumenau")
    if busca:
        mask = df.astype(str).apply(lambda s: s.str.contains(busca, case=False, regex=False)).any(axis=1)
        df = df[mask]
    with ui.card(catalog[name], f"{fmt.integer(len(df))} linhas · {len(df.columns)} colunas", key="tb_card"):
        st.dataframe(df, hide_index=True, width="stretch", height=min(38 * len(df) + 40, 620))
        tables.download(df, f"{name}.csv", key="tb_dl")
    helps = {c: h for c, h in COLUMN_HELP.items() if c in df.columns}
    if helps:
        with st.expander("O que significam as colunas calculadas", icon=":material/help:", expanded=True):
            st.markdown("\n".join(f"- `{c}` — {h}" for c, h in helps.items()))


ui.guarded(main)
