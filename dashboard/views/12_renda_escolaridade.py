"""Análises complementares — Renda e escolaridade: perfil de admitidos × desligados e dispersões municipais."""

import streamlit as st

from dashboard import formatting as fmt
from dashboard.components import charts, filters, tables, ui
from dashboard.services import analytics as A


def main() -> None:
    ui.header("Renda e escolaridade",
              "A causa-raiz: quem entra e quem sai, quanto cada nível de instrução recebe e como isso se "
              "relaciona com o saldo dos municípios.", eyebrow="Análises complementares")
    scope = filters.analysis_scope()
    ui.scope_bar(scope.describe())

    sg = A.table("salario_por_grau").sort_values("grau_ord")
    perfil = A.table("perfil_adm_desl")
    order = list(sg["grau"])
    pal = charts.palette()

    c = st.columns(2, gap="medium")
    with c[0], ui.card("Admitidos × desligados por escolaridade",
                       "Movimentações por grau de instrução (todo o estado). Onde os desligamentos superam as "
                       "admissões, o grupo está encolhendo.", key="re_perfil", scope="estado"):
        charts.show(charts.grouped_bars(perfil, "grau_instr", "mov", "n", order,
                                        {"Admitido": pal["blue"], "Desligado": pal["orange"]}, "Movimentações"),
                    key="re_perfil_chart")
    with c[1], ui.card("Salário mediano por grau de instrução",
                       "Há compressão salarial? Salário quase igual do analfabeto ao médio completo. "
                       "Mediana sem zeros, em R$ por mês.",
                       key="re_sal", scope="estado"):
        charts.show(charts.ordinal_bars(sg, "grau", "salario_mediano_s0", "Salário mediano", n_col="n_salario_s0"),
                    key="re_sal_chart")

    mun = A.municipal(scope)
    with ui.card("Dispersão municipal — salário × escolaridade média",
                 "Escolaridade média na escala ordinal de 1 (analfabeto) a 12 (doutorado). Cor = saldo por 10 mil "
                 "hab.; tamanho = saldo absoluto.", key="re_disp", scope="recorte"):
        d = mun.assign(saldo_abs=mun["saldo"].abs() + 1)
        charts.show(charts.bubble(d, "salario_medio", "grau_medio", "saldo_por_10k", "saldo_abs", "municipio",
                                  "Salário médio (R$)", "Escolaridade média (1–12)", "Saldo / 10 mil hab.",
                                  x_fmt=lambda v: fmt.brl(v, 0), y_fmt=lambda v: fmt.num(v, 2), height=500,
                                  hover=[("saldo", "Saldo", fmt.signed)]), key="re_disp_chart")

    c = st.columns(2, gap="medium")
    with c[0], ui.card("IDHM × saldo por 10 mil hab.", "IDHM de 2010 (último disponível).", key="re_idhm",
                       scope="recorte"):
        charts.show(charts.bubble(mun, "idhm", "saldo_por_10k", None, "populacao", "municipio", "IDHM (2010)",
                                  "Saldo / 10 mil hab.", x_fmt=lambda v: fmt.num(v, 3), height=420),
                    key="re_idhm_chart")
    with c[1], ui.card("PIB per capita × salário médio", "PIB per capita 2023 (base municipal).", key="re_pib",
                       scope="recorte"):
        charts.show(charts.bubble(mun, "pib_per_capita", "salario_medio", None, "populacao", "municipio",
                                  "PIB per capita (R$)", "Salário médio (R$)", x_fmt=lambda v: fmt.brl(v, 0),
                                  y_fmt=lambda v: fmt.brl(v, 0), height=420), key="re_pib_chart")

    with st.expander("Ver tabelas", icon=":material/table:"):
        tables.show(sg[["grau", "salario_mediano_s0", "salario_medio", "n_salario_s0", "n"]],
                    rename={"grau": "Grau de instrução", "salario_mediano_s0": "Salário mediano (R$, sem zeros)",
                            "salario_medio": "Salário médio (R$)", "n_salario_s0": "Registros com salário > 0",
                            "n": "Movimentações"},
                    money=["salario_mediano_s0", "salario_medio"], ints=["n_salario_s0", "n"])
        tables.show(perfil[["mov", "grau_instr", "n", "salario_mediano_s0", "salario_medio"]],
                    rename={"mov": "Movimento", "grau_instr": "Grau de instrução", "n": "Movimentações",
                            "salario_mediano_s0": "Salário mediano (R$, sem zeros)", "salario_medio": "Salário médio (R$)"},
                    money=["salario_mediano_s0", "salario_medio"], ints=["n"])


ui.guarded(main)
