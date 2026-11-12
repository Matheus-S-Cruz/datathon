"""Análises complementares — Contexto regional com as bases públicas do IBGE."""

import streamlit as st

from dashboard import formatting as fmt
from dashboard.components import charts, tables, ui
from dashboard.services import analytics as A


def main() -> None:
    ui.header("Contexto regional (IBGE)",
              "Estoque de emprego formal (CEMPRE 2024), peso da indústria na economia (PIB dos Municípios) e "
              "divisão regional oficial, cruzados com o saldo do CAGED.", eyebrow="Análises complementares")
    with st.sidebar:
        st.subheader("Recorte da análise")
        level = st.radio("Nível regional", list(A.REGION_LEVELS), format_func=A.REGION_LEVELS.get, key="ib_level")
    reg = A.regions(level)
    mun = A.municipal(A.Scope())

    c = st.columns([0.5, 0.5], gap="medium")
    with c[0], ui.card(f"Crescimento do emprego formal por {A.REGION_LEVELS[level].lower()}",
                       "Saldo do CAGED ÷ assalariados do CEMPRE 2024.", key="ib_growth"):
        charts.show(charts.signed_hbars(reg.sort_values("cresc_emprego_pct", ascending=False), "regiao",
                                        "cresc_emprego_pct", "Crescimento do emprego (%)",
                                        [("saldo", "Saldo", fmt.signed),
                                         ("rotatividade_pct", "Rotatividade", lambda v: fmt.num(v, 1) + "%")]),
                    key="ib_growth_chart")
    with c[1], ui.card("Peso da indústria no valor adicionado (2021)",
                       "VAB da indústria ÷ VAB total, por município. 2021 é o último ano com a abertura por "
                       "atividade publicada para municípios.", key="ib_vab", tag="PIB dos Municípios"):
        charts.show(charts.choropleth(mun, A.geojson(), "part_industria_vab_2021", "Indústria no VAB",
                                      [("saldo", "Saldo", fmt.signed),
                                       ("regiao_intermediaria", "Região", str)], diverging=False, height=520,
                                      tick_format=".0%", z_hover=".1%"),
                    key="ib_vab_map")

    with ui.card("Economias mais industriais crescem mais?",
                 "Municípios: peso da indústria no VAB × crescimento do emprego formal. Tamanho = assalariados.",
                 key="ib_scatter"):
        d = mun.assign(ind_pct=mun["part_industria_vab_2021"] * 100)
        charts.show(charts.bubble(d, "ind_pct", "cresc_emprego_pct", None, "assalariados", "municipio",
                                  "Indústria no VAB (%)", "Crescimento do emprego (%)", height=460,
                                  x_fmt=lambda v: fmt.num(v, 1) + "%", y_fmt=lambda v: fmt.num(v, 2) + "%",
                                  hover=[("regiao_intermediaria", "Região", str)]), key="ib_scatter_chart")
        corr = d[["ind_pct", "cresc_emprego_pct"]].corr(method="spearman").iloc[0, 1]
        st.caption(f"Correlação de Spearman entre as duas medidas: {fmt.corr(corr)} (295 municípios). "
                   "Correlação não implica causa.")

    with ui.card("Tabela regional", key="ib_table"):
        cols = ["regiao", "populacao", "assalariados", "admissoes", "desligamentos", "saldo", "saldo_por_10k",
                "cresc_emprego_pct", "rotatividade_pct", "part_industria_vab_2021", "salario_medio", "pct_superior"]
        tables.show(reg[cols], rename={"regiao": "Região", "populacao": "População", "assalariados": "Assalariados",
                                       "admissoes": "Admissões", "desligamentos": "Desligamentos", "saldo": "Saldo",
                                       "saldo_por_10k": "Saldo / 10 mil hab.", "cresc_emprego_pct": "Crescimento (%)",
                                       "rotatividade_pct": "Rotatividade (%)",
                                       "part_industria_vab_2021": "Indústria no VAB (2021)",
                                       "salario_medio": "Salário médio", "pct_superior": "Com superior"},
                    ints=["populacao", "assalariados", "admissoes", "desligamentos", "saldo"],
                    dec={"saldo_por_10k": 1, "cresc_emprego_pct": 2, "rotatividade_pct": 1},
                    pct=["part_industria_vab_2021", "pct_superior"], money=["salario_medio"])
        tables.download(reg[cols], f"{level}.csv", key="ib_dl")

    src = A.external_sources()
    if src:
        with st.expander("Fontes e data de download", icon=":material/link:"):
            st.markdown("\n".join(f"- **{k}:** {v}" for k, v in src["fontes"].items()))
            st.caption(f"Baixado em {src['baixado_em']} por `python -m src.enrichment.ibge`.")


ui.guarded(main)
