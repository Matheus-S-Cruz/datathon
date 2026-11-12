"""Página 7 — Relações territoriais e setoriais: agregações por combinações de dimensões."""

import pandas as pd
import streamlit as st

from dashboard import formatting as fmt
from dashboard.components import charts, filters, tables, ui
from dashboard.services import queries as Q
from dashboard.services.catalog import EDUCATION_ORDER

PRESETS = {
    "Município × Divisão CNAE": ["municipio", "divisao_cnae"],
    "Município × CBO": ["municipio", "cbo"],
    "Divisão CNAE × Escolaridade": ["divisao_cnae", "escolaridade"],
    "CBO × Escolaridade": ["cbo", "escolaridade"],
    "Município × Divisão CNAE × CBO": ["municipio", "divisao_cnae", "cbo"],
    "Personalizado": [],
}
CHOICES = ["municipio", "secao", "divisao_cnae", "subclasse7", "cbo", "grande_grupo_cbo", "escolaridade",
           "faixa_salarial", "competencia_dec", "competencia_mov", "tipo_mov", "categoria_cod", "sexo_cod"]
METRICS = {"movimentacoes": "Movimentações", "admissoes": "Admissões", "desligamentos": "Desligamentos",
           "saldo": "Saldo", "deslig_a_pedido": "Desligamentos a pedido", "mediana_salarial": "Mediana salarial",
           "mediana_adm": "Mediana salarial (admissões)", "mediana_desl": "Mediana salarial (desligamentos)",
           "ocupacoes": "Ocupações distintas (CBO)", "pct_medio_completo": "% com médio completo",
           "pct_superior_ou_mais": "% com superior completo ou mais"}
MONEY = ["mediana_salarial", "mediana_adm", "mediana_desl"]
INTS = ["movimentacoes", "admissoes", "desligamentos", "saldo", "deslig_a_pedido", "ocupacoes"]
PCTS = ["pct_medio_completo", "pct_superior_ou_mais"]


def group_label(df: pd.DataFrame, dims: list[str]) -> pd.Series:
    parts = []
    for d in dims:
        label = f"{d}_descricao"
        if label in df and d.startswith("competencia"):
            parts.append(df[label].astype(str))
        elif label in df:
            parts.append(df[d].astype(str) + " · " + df[label].astype(str).str.slice(0, 40))
        else:
            parts.append(Q.DIMENSIONS[d].label.split(" (")[0] + " " + df[d].astype(str))
    out = parts[0]
    for p in parts[1:]:
        out = out + " | " + p
    return out


def main() -> None:
    ui.page_header("Relações territoriais e setoriais",
                   "Combine município, setor, ocupação, escolaridade, salário e competência. "
                   "Medidas descritivas: ainda não há índice de escassez nem classificação de municípios.")
    f = filters.filter_panel("rel")
    ui.active_filters(f.active())

    c = st.columns([0.45, 0.55])
    preset = c[0].selectbox("Nível de agrupamento", list(PRESETS), key="rel_preset")
    if preset == "Personalizado":
        dims = c[1].multiselect("Dimensões (até 3, na ordem escolhida)", CHOICES, default=["municipio", "secao"],
                                max_selections=3, format_func=lambda d: Q.DIMENSIONS[d].label, key="rel_dims")
    else:
        dims = PRESETS[preset]
        c[1].markdown("**Dimensões:** " + " × ".join(Q.DIMENSIONS[d].label for d in dims))
    if not dims:
        st.info("Escolha ao menos uma dimensão.")
        return

    c = st.columns(3)
    minmov = c[0].number_input("Mínimo de movimentações por grupo", 0, 1_000_000, 30, step=10, key="rel_min",
                               help="Grupos muito pequenos geram medianas e percentuais instáveis.")
    sort = c[1].selectbox("Ordenar por", list(METRICS), format_func=METRICS.get, key="rel_sort")
    desc = c[2].toggle("Decrescente", value=True, key="rel_desc")

    with st.spinner("Agregando no DuckDB…"):
        df = Q.aggregate(dims, f, int(minmov))
    if df.empty:
        st.warning("Nenhum grupo atende aos filtros e ao mínimo de movimentações.")
        return
    df = df.sort_values(sort, ascending=not desc, na_position="last").reset_index(drop=True)
    df["grupo"] = group_label(df, dims)
    st.caption(f"{fmt.integer(len(df))} grupos com pelo menos {fmt.integer(minmov)} movimentações. "
               "Medianas salariais excluem salários zerados.")

    tab_table, tab_charts, tab_edu = st.tabs(["Tabela agregada", "Gráficos", "Distribuição educacional"])

    with tab_table:
        key_cols = []
        for d in dims:
            key_cols.append(d)
            if f"{d}_descricao" in df:
                key_cols.append(f"{d}_descricao")
        cols = key_cols + list(METRICS)
        rename = {d: Q.DIMENSIONS[d].label for d in dims}
        rename.update({f"{d}_descricao": f"{Q.DIMENSIONS[d].label} (descrição)" for d in dims})
        rename.update(METRICS)
        tables.show(df[cols].head(2000), rename=rename, ints=INTS, money=MONEY, pct=PCTS, height=600)
        if len(df) > 2000:
            st.caption(f"Exibindo os 2.000 primeiros de {fmt.integer(len(df))} grupos; o CSV contém todos.")
        tables.download(df[cols].rename(columns=rename), "relacoes_agregadas.csv", key="rel_dl")
        with st.expander("Como cada coluna é calculada"):
            st.markdown("""
- **Admissões / Desligamentos**: contagem de registros com saldo +1 / −1. **Saldo** = admissões − desligamentos.
- **Desligamentos a pedido**: `tipomovimentação = 40`.
- **Medianas salariais**: mediana de `salário` > 0 (todas as unidades de pagamento).
- **Ocupações distintas**: quantidade de CBOs diferentes no grupo.
- **% com médio completo**: `graudeinstrução = 7` sobre todas as movimentações do grupo.
- **% com superior completo ou mais**: códigos 9, 80, 10 e 11.
""")

    with tab_charts:
        top = st.slider("Grupos exibidos", 5, 50, 20, key="rel_top")
        view = df.head(top)
        charts.show(charts.flow_bars(view, "grupo", f"Admissões e desligamentos: {top} grupos (ordenados por "
                                                    f"{METRICS[sort].lower()})"), key="rel_flow")
        charts.show(charts.balance_bars(view, "grupo", "Saldo por grupo", horizontal=True), key="rel_bal")
        sc = df.dropna(subset=["mediana_adm"])
        charts.show(charts.scatter(sc, "mediana_adm", "saldo", "Saldo × mediana salarial das admissões (cada ponto é "
                                                               "um grupo)", "Mediana salarial das admissões (R$)",
                                   "Saldo", hover="grupo"), key="rel_sc")
        st.caption("Exploratório: um grupo no alto à direita tem saldo positivo e salário de admissão alto. Isso "
                   "não indica, sozinho, escassez nem expansão; depende de sazonalidade e composição.")
        if len(dims) == 2:
            metric = st.selectbox("Métrica do mapa de calor", ["saldo", "movimentacoes", "mediana_salarial",
                                                               "pct_superior_ou_mais"], format_func=METRICS.get,
                                  key="rel_hm")
            n_rows = st.slider("Linhas e colunas do mapa (maiores por volume)", 5, 30, 15, key="rel_hmn")
            a, b = dims
            la = df.groupby(a)["movimentacoes"].sum().nlargest(n_rows).index
            lb = df.groupby(b)["movimentacoes"].sum().nlargest(n_rows).index
            sub = df[df[a].isin(la) & df[b].isin(lb)].copy()
            sub["_a"] = group_label(sub, [a])
            sub["_b"] = group_label(sub, [b])
            pivot = sub.pivot_table(index="_a", columns="_b", values=metric, aggfunc="first")
            charts.show(charts.heatmap(pivot, f"{METRICS[metric]}: {Q.DIMENSIONS[a].label} × {Q.DIMENSIONS[b].label}",
                                       METRICS[metric], diverging=metric == "saldo", money=metric in MONEY),
                        key="rel_heat")
            st.caption("Células vazias: combinação sem movimentações suficientes (abaixo do mínimo).")

    with tab_edu:
        first = dims[0]
        if first == "escolaridade":
            st.info("A primeira dimensão já é a escolaridade; escolha outra ordem para ver a distribuição.")
        else:
            n = st.slider("Grupos exibidos", 5, 30, 12, key="rel_edu_n")
            groups = (df.groupby(first)["movimentacoes"].sum().nlargest(n).index.astype(str).tolist())
            edu = Q.education_distribution(first, f, groups)
            names = df.drop_duplicates(first).set_index(df.drop_duplicates(first)[first].astype(str))
            lab = group_label(names, [first])
            edu["grupo_rotulo"] = edu["grupo"].map(lab)
            charts.show(charts.education_share(edu, "grupo_rotulo",
                                               f"Escolaridade das movimentações por {Q.DIMENSIONS[first].label.lower()}"),
                        key="rel_edu")
            st.caption("Faixas agregam os códigos do dicionário: até fundamental incompleto = 1 a 4; fundamental "
                       "completo/médio incompleto = 5 a 6; médio completo = 7; superior incompleto = 8; superior "
                       "completo = 9; pós/mestrado/doutorado = 80, 10, 11. Tabela com os 12 níveis abaixo.")
            pivot = edu.pivot_table(index="grupo_rotulo", columns="escolaridade_descricao", values="n",
                                    aggfunc="sum", fill_value=0)
            code_of = dict(zip(edu["escolaridade_descricao"], edu["escolaridade"]))
            order = {c: i for i, c in enumerate(EDUCATION_ORDER)}
            pivot = pivot[sorted(pivot.columns, key=lambda d: order.get(code_of.get(d), 99))]
            st.dataframe(pivot, width="stretch")


ui.guarded(main)
