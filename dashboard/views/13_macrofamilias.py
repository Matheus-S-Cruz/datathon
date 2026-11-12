"""Análises complementares — Macrofamílias ocupacionais (agrupamento dos CBOs)."""

import streamlit as st

from dashboard import formatting as fmt
from dashboard.components import charts, tables, ui
from dashboard.services import analytics as A


def main() -> None:
    ui.header("Macrofamílias de ocupações",
              "Os 2.207 CBOs agrupados em macrofamílias. Saldo negativo em famílias de alta qualificação "
              "indica gargalo técnico; na base operacional, gargalo de mão de obra de entrada.",
              eyebrow="Análises complementares")
    with st.sidebar:
        st.subheader("Recorte da análise")
        recorte = st.radio("Setores", ["Indústria (B, C, D, F)", "Todos os setores"], key="mf_recorte")
    ind = recorte.startswith("Indústria")
    m = A.macro(industrial_only=ind)
    ui.active_filters([recorte.lower()] if ind else [])
    st.caption("Agrupamento determinístico pelo Grande Grupo da CBO-2002 (1º dígito do código). O refino por "
               "LLM do pipeline é opcional e só roda com chave de API — ver notebook, seção 8.")

    c = st.columns([0.55, 0.45], gap="medium")
    with c[0], ui.card("Saldo de vagas por macrofamília", "Azul = cria vagas; laranja = perde.", key="mf_saldo"):
        charts.show(charts.signed_hbars(m.sort_values("saldo", ascending=False), "cbo_grande_grupo", "saldo",
                                        "Saldo de vagas", [("n_cbos", "Nº de CBOs", fmt.integer)]),
                    key="mf_saldo_chart")
    with c[1], ui.card("Salário × escolaridade por macrofamília",
                       "Cor = saldo; tamanho = nº de CBOs distintos.", key="mf_scatter"):
        charts.show(charts.bubble(m, "salario_medio", "grau_medio", "saldo", "n_cbos", "cbo_grande_grupo",
                                  "Salário médio (R$)", "Escolaridade média (1–12)", "Saldo",
                                  x_fmt=lambda v: fmt.brl(v, 0), y_fmt=lambda v: fmt.num(v, 2), height=440,
                                  hover=[("saldo", "Saldo", fmt.signed)]), key="mf_scatter_chart")

    with ui.card("Tabela das macrofamílias", key="mf_table"):
        cols = ["cbo_grande_grupo", "saldo", "admissoes", "desligamentos", "salario_medio", "grau_medio",
                "pct_superior", "n_cbos"]
        tables.show(m[cols], rename={"cbo_grande_grupo": "Macrofamília", "saldo": "Saldo", "admissoes": "Admissões",
                                     "desligamentos": "Desligamentos", "salario_medio": "Salário médio",
                                     "grau_medio": "Escolaridade média (1–12)", "pct_superior": "Com superior",
                                     "n_cbos": "Nº de CBOs"},
                    ints=["saldo", "admissoes", "desligamentos", "n_cbos"], money=["salario_medio"],
                    pct=["pct_superior"], dec={"grau_medio": 2})
        tables.download(m[cols], "macrofamilias.csv", key="mf_dl")


ui.guarded(main)
