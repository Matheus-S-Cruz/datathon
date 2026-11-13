"""Análises complementares — Setores: saldo e fluxos por seção CNAE, polos industriais e regiões × setores."""

import streamlit as st

from dashboard import formatting as fmt
from dashboard.components import charts, filters, tables, ui
from dashboard.services import analytics as A


def main() -> None:
    ui.header("Setores", "Setores que lideram a criação e a perda de vagas, e onde estão os polos industriais.",
              eyebrow="Análises complementares")
    scope = filters.analysis_scope()
    ui.scope_bar(scope.describe())
    sec = A.sectors_in_scope(scope)
    sec = sec.assign(rotulo=sec["secao"] + " · " + sec["setor"].str.slice(0, 40))

    c = st.columns([0.5, 0.5], gap="medium")
    with c[0], ui.card("Saldo de vagas por setor", "Azul = seções industriais (B, C, D, F).", key="set_saldo",
                       scope="recorte"):
        charts.show(charts.emphasis_bars(sec, "rotulo", "saldo", sec["industrial"], "Saldo de vagas",
                                         "Industrial", "Demais setores"), key="set_saldo_chart")
    with c[1], ui.card("Admissões e desligamentos por setor",
                       "Volume de fluxo: setores com barras altas e parecidas giram muito para pouco saldo.",
                       key="set_flow", scope="recorte"):
        top = sec.sort_values("movimentacoes", ascending=False).head(12)
        fig = charts.flow_bars(top, "secao", "")
        fig.update_xaxes(title="Seção CNAE (12 de maior movimentação)")
        charts.show(fig, key="set_flow_chart")

    ms = A.municipal_sector(scope)
    ind = ms[ms["secao"].isin(A.INDUSTRIAL_SECTIONS)]
    regions = A.table("agg_municipio")[["mun_cod", "regiao_intermediaria"]]
    with ui.card("Saldo industrial por região e setor",
                 "Região geográfica intermediária × seção industrial. Azul = cria vagas, laranja = perde.",
                 key="set_heat", tag="IBGE", scope="recorte"):
        if ind.empty:
            st.info("Nenhum setor industrial no recorte atual.")
        else:
            piv = (ind.merge(regions, on="mun_cod").pivot_table(index="regiao_intermediaria", columns="setor",
                                                                  values="saldo", aggfunc="sum", fill_value=0))
            fig = charts.heatmap(piv, "", "Saldo", diverging=True)
            charts.show(charts.in_card(fig), key="set_heat_chart")

    with ui.card("Maiores polos industriais (município × setor)",
                 "Os 20 maiores saldos em seções industriais no recorte.", key="set_poles", scope="recorte"):
        if ind.empty:
            st.caption("Nenhum setor industrial selecionado nos filtros.")
        else:
            top = ind.sort_values("saldo", ascending=False).head(20)
            cols = ["municipio", "setor", "saldo", "admissoes", "desligamentos", "salario_medio", "pct_superior"]
            tables.show(top[cols], rename={"municipio": "Município", "setor": "Setor", "saldo": "Saldo",
                                           "admissoes": "Admissões", "desligamentos": "Desligamentos",
                                           "salario_medio": "Salário médio", "pct_superior": "Com superior"},
                        ints=["saldo", "admissoes", "desligamentos"], money=["salario_medio"], pct=["pct_superior"])
            tables.download(top[cols], "polos_industriais.csv", key="set_dl")
    st.caption(f"{fmt.integer(len(sec))} seções no recorte. Seções sem nome no dicionário aparecem pelo código.")


ui.guarded(main)
