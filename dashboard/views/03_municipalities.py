"""Página 3 — Explorador de municípios (base municipal de SC)."""

import pandas as pd
import streamlit as st

from dashboard import formatting as fmt
from dashboard.components import charts, tables, ui
from dashboard.services import queries as Q
from dashboard.services.municipalities import NUMERIC_KEYS, load_municipalities

MONEY = ["receitas", "despesas", "pib_per_capita"]
INTS = ["pop_censo", "pop_estimada", "movimentacoes", "admissoes", "desligamentos", "saldo"]
DECS = {"area_km2": 2, "densidade": 2, "escolarizacao": 2, "idhm": 3, "mortalidade_infantil": 2}
SORTS = {"Nome": "nome", "População estimada": "pop_estimada", "PIB per capita": "pib_per_capita",
         "IDHM": "idhm", "Código IBGE": "codigo_ibge", "Movimentações no CAGED": "movimentacoes"}


@st.cache_data(show_spinner=False)
def _load(signature):
    return load_municipalities()


def main() -> None:
    ui.section_header("Exploração e consulta", "Municípios de Santa Catarina",
                   "Base `Municipios_SC_limpo.csv` já limpa: sem a linha de rodapé, sem a coluna vazia, '-' como ausente.")
    from dashboard.services.database import data_signature
    res = _load(data_signature())
    labels = res.labels
    flows = Q.flow_by("municipio")[["municipio", "movimentacoes", "admissoes", "desligamentos", "saldo"]]
    df = res.data.merge(flows, left_on="cod6", right_on="municipio", how="left").drop(columns="municipio")

    c = st.columns(4)
    c[0].metric("Municípios", fmt.integer(len(df)))
    c[1].metric("Com movimentação no CAGED", fmt.integer(df["movimentacoes"].notna().sum()))
    c[2].metric("Indicadores numéricos", len(NUMERIC_KEYS))
    c[3].metric("Valores ausentes ('-')", fmt.integer(sum(res.missing_dash.values())))

    tab_table, tab_missing, tab_record, tab_charts = st.tabs(
        ["Tabela", "Valores ausentes", "Registro completo", "Gráficos exploratórios"])

    with tab_table:
        c = st.columns([0.4, 0.3, 0.3])
        term = c[0].text_input("Pesquisar por nome ou código IBGE", key="mun_term",
                               placeholder="ex.: Joinville, 4209102 ou 420910")
        sort = c[1].selectbox("Ordenar por", list(SORTS), key="mun_sort")
        desc = c[2].toggle("Decrescente", value=sort not in ("Nome", "Código IBGE"), key=f"mun_desc_{sort}")
        view = df
        if term.strip():
            t = term.strip().lower()
            view = df[df["nome"].str.lower().str.contains(t, regex=False)
                      | df["codigo_ibge"].str.startswith(t) | df["cod6"].str.startswith(t)]
        view = view.sort_values(SORTS[sort], ascending=not desc, na_position="last")
        st.caption(f"{fmt.integer(len(view))} município(s). Clique no cabeçalho para reordenar. "
                   "‘—’ = valor ausente no arquivo. Movimentações = total do CAGED no período.")
        cols = ["nome", "codigo_ibge", "cod6", *NUMERIC_KEYS, "movimentacoes", "saldo"]
        rename = {k: labels.get(k, k) for k in cols}
        rename.update({"nome": "Município", "codigo_ibge": "Código IBGE (7 dígitos)", "cod6": "Código CAGED (6)",
                       "movimentacoes": "Movimentações (CAGED)", "saldo": "Saldo (CAGED)"})
        event = tables.show(view[cols], rename=rename, money=MONEY, ints=INTS, dec=DECS,
                            height=560, key="mun_grid", selectable=True)
        if event and event.selection.rows:
            st.session_state["mun_selected"] = view.iloc[event.selection.rows[0]]["codigo_ibge"]
            st.caption("Município selecionado — veja a aba *Registro completo*.")
        tables.download(view[cols].rename(columns=rename), "municipios_sc.csv", key="mun_dl")

    with tab_missing:
        miss = pd.DataFrame([{"indicador": labels[k], "ausentes ('-')": res.missing_dash[k],
                              "não numéricos": res.invalid[k],
                              "% ausente": res.missing_dash[k] / len(df)} for k in NUMERIC_KEYS])
        tables.show(miss, ints=["ausentes ('-')", "não numéricos"], pct=["% ausente"])
        key = st.selectbox("Ver municípios com ausência em", [k for k in NUMERIC_KEYS if res.missing_dash[k]],
                           format_func=labels.get, key="mun_misskey")
        if key:
            st.dataframe(df[df[key].isna()][["nome", "codigo_ibge"]].rename(
                columns={"nome": "Município", "codigo_ibge": "Código IBGE"}), hide_index=True, width="stretch")
        st.caption(f"Limpeza aplicada: {res.footer_rows} linha(s) de rodapé removida(s) de {res.total_rows_in_file} "
                   f"linhas do arquivo; a coluna 'Prefeito' não é exibida (dado pessoal sem uso analítico).")

    with tab_record:
        names = dict(zip(df["codigo_ibge"], df["nome"]))
        codes = sorted(names, key=names.get)
        default = st.session_state.get("mun_selected", codes[0])
        code = st.selectbox("Município", codes, index=codes.index(default),
                            format_func=lambda c: f"{names[c]} ({c})", key=f"mun_rec_{default}")
        row = df[df["codigo_ibge"] == code].iloc[0]
        raw = res.raw[res.raw["codigo_ibge"] == code].iloc[0]
        rec = []
        for k in ["nome", "codigo_ibge", "gentilico", *NUMERIC_KEYS]:
            value = row[k]
            if k in MONEY:
                shown = fmt.brl(value)
            elif k in INTS:
                shown = fmt.integer(value)
            elif k in DECS:
                shown = fmt.num(value, DECS[k])
            else:
                shown = value
            rec.append({"campo": labels.get(k, k), "valor no arquivo": raw[k], "valor interpretado": shown})
        rec += [{"campo": "Código usado no CAGED (6 dígitos)", "valor no arquivo": "", "valor interpretado": row["cod6"]},
                {"campo": "Dígito verificador IBGE válido", "valor no arquivo": "",
                 "valor interpretado": "sim" if row["dv_valido"] else "não"},
                {"campo": "Admissões no CAGED", "valor no arquivo": "", "valor interpretado": fmt.integer(row["admissoes"])},
                {"campo": "Desligamentos no CAGED", "valor no arquivo": "", "valor interpretado": fmt.integer(row["desligamentos"])},
                {"campo": "Saldo no CAGED", "valor no arquivo": "", "valor interpretado": fmt.signed(row["saldo"])}]
        st.dataframe(pd.DataFrame(rec), hide_index=True, width="stretch", height=640)

    with tab_charts:
        ui.explain("Os gráficos mostram como os indicadores se distribuem e se variam juntos. "
                   "**Variar junto não significa que um causa o outro** — municípios maiores, por exemplo, "
                   "diferem em muitos aspectos ao mesmo tempo.")
        log = st.toggle("Escala logarítmica para população", value=True, key="mun_log",
                        help="A população vai de ~1 mil a ~650 mil habitantes; em escala linear quase todos os "
                             "municípios ficam espremidos à esquerda.")
        c = st.columns(3)
        with c[0]:
            charts.show(charts.value_histogram(df["pop_estimada"], "Distribuição da população estimada",
                                               "Habitantes", log_x=log), key="mun_h1")
        with c[1]:
            charts.show(charts.value_histogram(df["pib_per_capita"], "Distribuição do PIB per capita",
                                               "PIB per capita (R$)"), key="mun_h2")
        with c[2]:
            charts.show(charts.value_histogram(df["idhm"], "Distribuição do IDHM (2010)", "IDHM"), key="mun_h3")
            st.caption(f"{res.missing_dash['idhm']} município(s) sem IDHM ficam de fora.")
        c = st.columns(2)
        with c[0]:
            charts.show(charts.scatter(df, "pop_estimada", "pib_per_capita", "População × PIB per capita",
                                       "População estimada", "PIB per capita (R$)", hover="nome", log_x=log),
                        key="mun_s1")
        with c[1]:
            charts.show(charts.scatter(df.dropna(subset=["idhm"]), "pib_per_capita", "idhm",
                                       "PIB per capita × IDHM", "PIB per capita (R$)", "IDHM (2010)", hover="nome"),
                        key="mun_s2")
        corr = []
        for a, b in [("pop_estimada", "pib_per_capita"), ("pib_per_capita", "idhm")]:
            pair = df[[a, b]].dropna()
            corr.append({"par": f"{labels[a]} × {labels[b]}", "n": len(pair),
                         "Pearson": pair[a].corr(pair[b]),
                         # DataFrame.corr tem Spearman próprio (Series.corr exigiria SciPy)
                         "Spearman": pair.corr(method="spearman").iloc[0, 1]})
        tables.show(pd.DataFrame(corr), ints=["n"], corr=["Pearson", "Spearman"])
        st.caption("Pearson mede relação linear (sensível a extremos); Spearman mede se a ordem dos municípios "
                   "num indicador acompanha a ordem no outro. Ambos variam de −1 a +1. O IDHM é de 2010 e o PIB "
                   "per capita de 2023: anos diferentes.")


ui.guarded(main)
