"""Painel de filtros reutilizado pelas páginas que consultam o CAGED.

Os filtros ficam num formulário na barra lateral: nada é consultado enquanto a
usuária escolhe; a consulta roda só ao clicar em "Aplicar filtros".
As opções mostram código + descrição oficial do dicionário.
"""

from __future__ import annotations

import streamlit as st

from dashboard import formatting as fmt
from dashboard.services import queries as Q
from dashboard.services.catalog import EDUCATION_ORDER

ALL = ("municipio", "periodo", "secao", "divisao", "subclasse", "cbo", "escolaridade",
       "movimento", "tipo_mov", "salario")


def _options(expr: str, sheet: str | None) -> tuple[list[str], dict[str, str]]:
    df = Q.distinct_values(expr)
    codes = sorted(df["valor"].dropna().astype(str))
    if sheet:
        labels = {c: f"{c} · {Q.describe(sheet, c)}" for c in codes}
    else:
        labels = {c: c for c in codes}
    return codes, labels


def _division_labels() -> tuple[list[str], dict[str, str]]:
    df = Q.run("SELECT divisao_cnae, string_agg(DISTINCT secao, ', ') AS secoes FROM caged GROUP BY 1 ORDER BY 1")
    return list(df["divisao_cnae"]), {r.divisao_cnae: f"{r.divisao_cnae} (seção {r.secoes})"
                                      for r in df.itertuples()}


def filter_panel(key: str, include=ALL, title: str = "Filtros") -> Q.Filters:
    names = Q.municipality_names()
    with st.sidebar:
        st.subheader(title)
        with st.form(f"{key}_filters", border=True):
            kw: dict = {}
            if "municipio" in include:
                codes = sorted(names, key=lambda c: names[c])
                kw["municipios"] = tuple(st.multiselect(
                    "Município", codes, format_func=lambda c: f"{names.get(c, c)} ({c})",
                    key=f"{key}_mun", placeholder="Todos"))
            if "periodo" in include:
                col = st.radio("Competência usada no período", Q.PERIOD_COLUMNS, horizontal=True,
                               format_func=lambda c: "Declaração" if c == "competencia_dec" else "Movimentação",
                               key=f"{key}_percol",
                               help="Declaração: mês em que a empresa informou (12 meses). "
                                    "Movimentação: mês em que o fato ocorreu (inclui declarações fora do prazo).")
                months = sorted(Q.distinct_values(col)["valor"].dropna())
                if months:
                    ini, fim = st.select_slider("Período", options=months, value=(months[0], months[-1]),
                                                format_func=fmt.competencia, key=f"{key}_per_{col}")
                    kw["periodo_coluna"] = col
                    kw["competencia_inicio"] = ini if ini != months[0] else None
                    kw["competencia_fim"] = fim if fim != months[-1] else None
            if "secao" in include:
                codes, labels = _options("secao", "seção")
                kw["secoes"] = tuple(st.multiselect("Seção CNAE", codes, format_func=labels.get,
                                                    key=f"{key}_sec", placeholder="Todas"))
            if "divisao" in include:
                codes, labels = _division_labels()
                kw["divisoes"] = tuple(st.multiselect(
                    "Divisão CNAE (2 dígitos)", codes, format_func=labels.get, key=f"{key}_div",
                    placeholder="Todas",
                    help="Dois primeiros dígitos da subclasse. O dicionário não traz o nome das divisões."))
            if "subclasse" in include:
                codes, labels = _options("subclasse7", "subclasse")
                kw["subclasses"] = tuple(st.multiselect("Subclasse CNAE", codes, format_func=labels.get,
                                                        key=f"{key}_sub", placeholder="Todas"))
            if "cbo" in include:
                codes, labels = _options("cbo", "cbo2002ocupação")
                kw["cbos"] = tuple(st.multiselect("Ocupação (CBO)", codes, format_func=labels.get,
                                                  key=f"{key}_cbo", placeholder="Todas"))
            if "escolaridade" in include:
                codes, labels = _options("escolaridade", "graudeinstrução")
                codes = sorted(codes, key=lambda c: EDUCATION_ORDER.index(c) if c in EDUCATION_ORDER else 99)
                kw["escolaridades"] = tuple(st.multiselect("Grau de instrução", codes, format_func=labels.get,
                                                           key=f"{key}_esc", placeholder="Todos"))
            if "movimento" in include:
                mov = st.radio("Movimento", ["Todos", "Admissão", "Desligamento"], horizontal=True,
                               key=f"{key}_mov")
                kw["movimento"] = None if mov == "Todos" else mov
            if "tipo_mov" in include:
                codes, labels = _options("tipo_mov", "tipomovimentação")
                kw["tipos_mov"] = tuple(st.multiselect(
                    "Tipo de movimentação / desligamento", codes, format_func=labels.get,
                    key=f"{key}_tipo", placeholder="Todos"))
            if "salario" in include:
                c1, c2 = st.columns(2)
                smin = c1.number_input("Salário mínimo (R$)", min_value=0.0, value=None, step=100.0,
                                       key=f"{key}_smin", placeholder="sem limite")
                smax = c2.number_input("Salário máximo (R$)", min_value=0.0, value=None, step=100.0,
                                       key=f"{key}_smax", placeholder="sem limite")
                kw["salario_min"], kw["salario_max"] = smin, smax
                kw["excluir_salario_zero"] = st.checkbox("Excluir salários zerados", key=f"{key}_zero")
                kw["somente_unidade_mes"] = st.checkbox(
                    "Só salários com unidade 'Mês'", key=f"{key}_mes",
                    help="unidadesaláriocódigo = 5 (88,5% dos registros).")
            st.form_submit_button("Aplicar filtros", icon=":material/filter_alt:", type="primary",
                                  width="stretch")
    return Q.Filters(**kw)
