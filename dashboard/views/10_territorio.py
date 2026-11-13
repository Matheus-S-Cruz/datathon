"""Análises complementares — Território: mapas, rankings de municípios e expansão × rotatividade.

Reúne a aba "Território" do dashboard original (mapa de bolhas, Top 15, dispersão) com o mapa de
rotatividade calculado sobre o estoque do IBGE/CEMPRE.
"""

import plotly.express as px
import streamlit as st

from dashboard import formatting as fmt
from dashboard.components import charts, filters, tables, ui
from dashboard.services import analytics as A


def bubble_map(mun) -> None:
    coords = A.coords()
    with ui.card("Mapa de calor: saldo e rotatividade por município",
                 "Cor = saldo por 10 mil hab. (azul = expansão, laranja = retração); tamanho = giro (admissões + "
                 "desligamentos) por 10 mil hab. Bolha grande e laranja = alta rotatividade com saldo negativo. "
                 "O mapa de fundo precisa de internet; as bolhas aparecem mesmo sem ele.", key="ter_bubble",
                 scope="recorte"):
        if coords is None:
            st.warning("Arquivo de coordenadas não encontrado (`data/reference/municipios_sc_coords.parquet`).")
            return
        d = mun.merge(coords, on="mun_cod", how="inner").dropna(subset=["saldo_por_10k"])
        if d.empty:
            st.info("Sem municípios para exibir com o recorte atual.")
            return
        lim = float(d["saldo_por_10k"].abs().quantile(0.95)) or 1.0
        d["tam"] = d["giro_por_10k"].fillna(0).clip(lower=1)
        fig = px.scatter_map(d, lat="lat", lon="lon", color="saldo_por_10k", size="tam", size_max=26,
                             zoom=6.0, center={"lat": -27.45, "lon": -50.6}, hover_name="municipio",
                             color_continuous_scale=[c for _, c in charts.DIVERGING], range_color=[-lim, lim],
                             custom_data=["saldo", "saldo_por_10k", "giro_por_10k", "salario_medio", "populacao"],
                             labels={"saldo_por_10k": "Saldo / 10 mil hab."}, height=560)
        fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>Saldo: %{customdata[0]:+,.0f} vagas<br>"
                                        "Saldo / 10 mil hab.: %{customdata[1]:,.1f}<br>"
                                        "Giro / 10 mil hab.: %{customdata[2]:,.0f}<br>"
                                        "Salário médio: R$ %{customdata[3]:,.0f}<br>"
                                        "População: %{customdata[4]:,.0f}<extra></extra>")
        fig.update_layout(map_style="carto-positron", margin=dict(l=0, r=0, t=0, b=0), separators=",.",
                          paper_bgcolor="rgba(0,0,0,0)",
                          coloraxis_colorbar=dict(thickness=12, len=0.75, outlinewidth=0))
        charts.show(fig, key="ter_bubble_map")


def turnover_map(scope: A.Scope, mun) -> None:
    with ui.card("Rotatividade sobre o estoque de emprego formal",
                 "Mín(admissões, desligamentos) ÷ assalariados do CEMPRE 2024. Quanto mais escuro, maior a "
                 "parcela do emprego formal que foi trocada no período.", key="ter_turn", tag="IBGE",
                 scope="recorte"):
        if not scope.all_sections:
            st.info("Indisponível com recorte setorial: o CEMPRE municipal não é aberto por setor.",
                    icon=":material/info:")
            return
        geo = A.geojson()
        charts.show(charts.choropleth(mun, geo, "rotatividade_pct", "Rotatividade (%)",
                                      [("cresc_emprego_pct", "Crescimento", lambda v: fmt.num(v, 2) + "%"),
                                       ("assalariados", "Assalariados (2024)", fmt.integer)],
                                      diverging=False, height=470), key="ter_turn_map")


def rankings(mun) -> None:
    c = st.columns(2, gap="medium")
    cols = [("saldo", "Saldo", fmt.signed), ("populacao", "População", fmt.integer)]
    with c[0], ui.card("Top 15 — expansão acelerada", "Maiores saldos por 10 mil habitantes.", key="ter_top",
                       scope="recorte"):
        top = mun.sort_values("saldo_por_10k", ascending=False).head(15)
        charts.show(charts.signed_hbars(top, "municipio", "saldo_por_10k", "Saldo por 10 mil hab.", cols),
                    key="ter_top_chart")
    with c[1], ui.card("Top 15 — retração", "Menores saldos por 10 mil habitantes.", key="ter_bottom",
                       scope="recorte"):
        bot = mun.sort_values("saldo_por_10k").head(15)
        charts.show(charts.signed_hbars(bot, "municipio", "saldo_por_10k", "Saldo por 10 mil hab.", cols),
                    key="ter_bottom_chart")


def expansion_vs_turnover(mun) -> None:
    with ui.card("Expansão × giro",
                 "Cada bolha é um município. À direita, mais saldo; no alto, mais giro (admissões + "
                 "desligamentos). Tamanho = população; cor = salário médio.", key="ter_scatter",
                 scope="recorte"):
        d = mun[mun["populacao"] > 0]
        charts.show(charts.bubble(d, "saldo_por_10k", "giro_por_10k", "salario_medio", "populacao", "municipio",
                                  "Saldo por 10 mil hab.", "Giro por 10 mil hab.", "Salário médio (R$)",
                                  diverging=False, height=470,
                                  hover=[("salario_medio", "Salário médio", lambda v: fmt.brl(v, 0)),
                                         ("populacao", "População", fmt.integer)]), key="ter_scatter_chart")


def main() -> None:
    ui.header("Território", "Municípios em expansão, em retração e com alta rotatividade.",
              eyebrow="Análises complementares")
    scope = filters.analysis_scope()
    ui.scope_bar(scope.describe())
    mun = A.municipal(scope)
    bubble_map(mun)
    c = st.columns([0.45, 0.55], gap="medium")
    with c[0]:
        turnover_map(scope, mun)
    with c[1]:
        expansion_vs_turnover(mun)
    rankings(mun)
    with st.expander("Ver tabela dos municípios no recorte", icon=":material/table:"):
        cols = ["municipio", "regiao_intermediaria", "populacao", "admissoes", "desligamentos", "saldo",
                "saldo_por_10k", "giro_por_10k", "cresc_emprego_pct", "rotatividade_pct", "salario_medio"]
        view = mun[cols].sort_values("saldo_por_10k", ascending=False)
        tables.show(view, rename={"municipio": "Município", "regiao_intermediaria": "Região", "populacao": "População",
                                  "admissoes": "Admissões", "desligamentos": "Desligamentos", "saldo": "Saldo",
                                  "saldo_por_10k": "Saldo / 10 mil hab.", "giro_por_10k": "Giro / 10 mil hab.",
                                  "cresc_emprego_pct": "Crescimento (%)", "rotatividade_pct": "Rotatividade (%)",
                                  "salario_medio": "Salário médio"},
                    ints=["populacao", "admissoes", "desligamentos", "saldo"], money=["salario_medio"],
                    dec={"saldo_por_10k": 1, "giro_por_10k": 0, "cresc_emprego_pct": 2, "rotatividade_pct": 1},
                    height=420)
        tables.download(view, "municipios_recorte.csv", key="ter_dl")


ui.guarded(main)
