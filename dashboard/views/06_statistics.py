"""Página 6 — Exploração estatística: descritivas, correlação e dispersão entre variáveis quantitativas."""

import pandas as pd
import streamlit as st

from dashboard import formatting as fmt
from dashboard.components import charts, filters, tables, ui
from dashboard.services import queries as Q

GROUP_DIMS = ["escolaridade", "movimento", "secao", "faixa_salarial", "categoria_cod", "sexo_cod",
              "tipo_mov", "competencia_dec", "grande_grupo_cbo"]
MONEY_VARS = {"salario", "salario_fixo", "receitas", "despesas", "pib_per_capita", "mediana_salario_adm"}
STAT_LABELS = {"n": "Observações usadas (n)", "media": "Média", "mediana": "Mediana", "moda": "Moda",
               "desvio_padrao": "Desvio-padrão", "minimo": "Mínimo", "q1": "1º quartil (Q1)",
               "q3": "3º quartil (Q3)", "maximo": "Máximo"}


def strength(r) -> str:
    if r is None or pd.isna(r):
        return "não calculável"
    a = abs(r)
    level = ("praticamente nula" if a < 0.1 else "fraca" if a < 0.3 else "moderada" if a < 0.5
             else "forte" if a < 0.7 else "muito forte")
    direction = "" if a < 0.1 else (" e positiva (quando uma cresce, a outra tende a crescer)" if r > 0
                                    else " e negativa (quando uma cresce, a outra tende a diminuir)")
    return level + direction


def stats_table(summaries: dict[str, dict], money: dict[str, bool]) -> pd.DataFrame:
    rows = []
    for key, label in STAT_LABELS.items():
        row = {"estatística": label}
        for var, s in summaries.items():
            v = s.get(key)
            row[var] = fmt.integer(v) if key == "n" else (fmt.brl(v) if money[var] else fmt.num(v, 2))
        rows.append(row)
    return pd.DataFrame(rows)


def explain_stats() -> None:
    with st.expander("O que significa cada estatística?", icon=":material/school:"):
        st.markdown("""
- **Média**: soma dividida pela quantidade. É puxada por valores extremos.
- **Mediana**: o valor do meio quando tudo é ordenado; metade fica abaixo, metade acima. Resiste a extremos.
- **Moda**: o valor mais frequente (em salários, costuma ser um piso ou o salário mínimo).
- **Desvio-padrão**: quanto os valores costumam se afastar da média.
- **Quartis**: Q1 deixa 25% abaixo, Q3 deixa 75% abaixo; entre eles estão os 50% centrais.
- **Pearson**: força da relação **linear** (de −1 a +1). Sensível a extremos.
- **Spearman**: se a **ordem** em uma variável acompanha a ordem na outra (−1 a +1). Mais robusto a extremos.
- **Correlação não é causalidade**: duas variáveis podem andar juntas porque ambas dependem de uma terceira
  (ex.: ocupação, porte da empresa, tamanho do município).
- Só aparecem variáveis **quantitativas**. Códigos (CBO, CNAE, escolaridade) são categorias: calcular correlação
  com eles como se fossem números não tem significado. Para categorias, use a tabela agregada por grupo.
""")


def record_level() -> None:
    f = filters.filter_panel("stat", include=("municipio", "periodo", "secao", "divisao", "escolaridade",
                                              "movimento", "tipo_mov", "salario"))
    ui.active_filters(f.active())
    variables = Q.RECORD_VARIABLES
    c = st.columns(2)
    x = c[0].selectbox("Variável X", list(variables), format_func=variables.get, key="stat_x")
    y = c[1].selectbox("Variável Y", list(variables), index=2, format_func=variables.get, key="stat_y")
    if "salario" in (x, y) and not f.excluir_salario_zero:
        st.caption("Dica: marque *Excluir salários zerados* nos filtros: 1% dos registros têm salário 0.")

    with st.spinner("Calculando sobre todos os registros filtrados…"):
        sx = Q.numeric_summary(x, f)
        sy = Q.numeric_summary(y, f) if y != x else sx
    st.subheader("Estatísticas descritivas")
    tables.show(stats_table({variables[x]: sx, variables[y]: sy} if y != x else {variables[x]: sx},
                            {variables[x]: x in MONEY_VARS, variables[y]: y in MONEY_VARS}))
    missing = {variables[v]: int(s["total"] - s["n"]) for v, s in [(x, sx), (y, sy)] if s["total"] > s["n"]}
    st.caption(f"Calculado no DuckDB sobre {fmt.integer(sx['total'])} registros filtrados. "
               + ("Sem valor (excluídos do cálculo): " + "; ".join(f"{k}: {fmt.integer(v)}" for k, v in missing.items())
                  if missing else "Nenhum valor ausente nessas variáveis."))
    explain_stats()

    if x == y:
        st.info("Escolha variáveis X e Y diferentes para ver correlação e dispersão.")
    else:
        st.subheader("Relação entre X e Y")
        with st.spinner("Calculando correlações…"):
            r = Q.correlation(x, y, f)
        c = st.columns(3)
        c[0].metric("Observações (pares completos)", fmt.integer(r["n"]))
        c[1].metric("Pearson", fmt.corr(r["pearson"]))
        c[2].metric("Spearman", fmt.corr(r["spearman"]))
        st.markdown(f"Relação linear (Pearson) **{strength(r['pearson'])}**; relação de ordem (Spearman) "
                    f"**{strength(r['spearman'])}**. Faixas usadas: |r| < 0,1 praticamente nula; < 0,3 fraca; "
                    "< 0,5 moderada; < 0,7 forte; acima, muito forte (convenção, não regra).")
        if pd.notna(r["pearson"]) and pd.notna(r["spearman"]) and abs(r["spearman"] - r["pearson"]) > 0.15:
            st.caption("Pearson e Spearman bem diferentes costumam indicar valores extremos ou relação não linear.")

        c = st.columns(3)
        n = c[0].select_slider("Pontos no gráfico", [1000, 2000, 5000, 10000], value=5000, key="stat_n")
        color = c[1].selectbox("Colorir por", [None, "movimento", "sexo_cod"], key="stat_color",
                               format_func=lambda d: "nada" if d is None else Q.DIMENSIONS[d].label)
        cut = c[2].toggle("Cortar no percentil 99 de cada eixo", value=True, key="stat_cut",
                          help="Só para visualização: os cálculos acima usam todos os registros.")
        pts = Q.scatter_sample(x, y, f, n=n, color_dim=color)
        if color:
            pts = Q.add_labels(pts.rename(columns={"grupo": color}), color)
            pts["grupo"] = pts[f"{color}_descricao"] if f"{color}_descricao" in pts else pts[color]
        if cut and len(pts):
            pts = pts[(pts["x"] <= pts["x"].quantile(0.99)) & (pts["y"] <= pts["y"].quantile(0.99))]
        pts["registro"] = "linha " + pts["linha"].map(fmt.integer)
        charts.show(charts.scatter(pts, "x", "y", f"{variables[y]} × {variables[x]}", variables[x], variables[y],
                                   hover="registro", group="grupo" if color else None), key="stat_scatter")
        st.badge(f"Amostra aleatória de {fmt.integer(len(pts))} pontos para o gráfico "
                 f"(de {fmt.integer(r['n'])} pares). Os números acima usam todos os pares.",
                 icon=":material/shuffle:", color="violet")

    st.subheader("Tabela agregada por categoria")
    c = st.columns(2)
    var = c[0].selectbox("Variável", list(variables), format_func=variables.get, key="stat_gvar")
    dim = c[1].selectbox("Agrupar por", GROUP_DIMS, format_func=lambda d: Q.DIMENSIONS[d].label, key="stat_gdim")
    g = Q.grouped_summary(var, dim, f)
    label = f"{dim}_descricao"
    cols = [dim] + ([label] if label in g else []) + ["n", "media", "mediana", "q1", "q3", "desvio_padrao"]
    money = ["media", "mediana", "q1", "q3", "desvio_padrao"] if var in MONEY_VARS else []
    tables.show(g[cols], rename={dim: Q.DIMENSIONS[dim].label, label: "descrição", "n": "n", "media": "média",
                                 "q1": "Q1", "q3": "Q3", "desvio_padrao": "desvio-padrão"},
                ints=["n"], money=money, dec={} if money else {c: 2 for c in ["media", "mediana", "q1", "q3",
                                                                              "desvio_padrao"]})
    st.caption("Até 50 grupos com mais observações. Diferenças entre grupos podem refletir composição "
               "(ocupações, setores, meses diferentes): são descrições, não efeitos.")
    tables.download(g[cols], f"estatistica_{var}_por_{dim}.csv", key="stat_dl")


def municipal_level() -> None:
    f = filters.filter_panel("statm", include=("periodo", "secao", "divisao", "movimento", "tipo_mov"),
                             title="Filtros do CAGED (antes de agregar)")
    ui.active_filters(f.active())
    st.caption("Uma observação por município: indicadores da base municipal + agregados do CAGED com os filtros.")
    df = Q.municipal_metrics(f)
    variables = Q.MUNICIPAL_VARIABLES
    c = st.columns(3)
    x = c[0].selectbox("Variável X", list(variables), index=list(variables).index("pib_per_capita"),
                       format_func=variables.get, key="statm_x")
    y = c[1].selectbox("Variável Y", list(variables), index=list(variables).index("saldo_10mil"),
                       format_func=variables.get, key="statm_y")
    minmov = c[2].number_input("Mínimo de movimentações no município", 0, 100000, 0, step=100, key="statm_min",
                               help="Municípios pequenos geram taxas instáveis; use para excluí-los.")
    data = df[df["movimentacoes"] >= minmov]

    summ = {}
    for v in dict.fromkeys([x, y]):
        s = data[v].dropna().astype(float)
        summ[variables[v]] = {"n": len(s), "media": s.mean(), "mediana": s.median(),
                              "moda": s.mode().iloc[0] if len(s.mode()) else None, "desvio_padrao": s.std(),
                              "minimo": s.min(), "q1": s.quantile(0.25), "q3": s.quantile(0.75), "maximo": s.max()}
    tables.show(stats_table(summ, {variables[v]: v in MONEY_VARS for v in [x, y]}))
    explain_stats()
    if x != y:
        pair = data[[x, y]].dropna().astype(float)
        c = st.columns(3)
        c[0].metric("Municípios (pares completos)", fmt.integer(len(pair)))
        pearson = pair[x].corr(pair[y]) if len(pair) > 2 else None
        spearman = pair.corr(method="spearman").iloc[0, 1] if len(pair) > 2 else None
        c[1].metric("Pearson", fmt.corr(pearson))
        c[2].metric("Spearman", fmt.corr(spearman))
        st.markdown(f"Relação linear **{strength(pearson)}**; relação de ordem **{strength(spearman)}**.")
        log = st.toggle("Escala logarítmica no eixo X", value=x in ("pop_estimada", "pop_censo", "densidade",
                                                                    "receitas", "despesas", "admissoes",
                                                                    "desligamentos"), key=f"statm_log_{x}")
        charts.show(charts.scatter(data.dropna(subset=[x, y]), x, y, f"{variables[y]} × {variables[x]}",
                                   variables[x], variables[y], hover="nome",
                                   log_x=log and (data[x] > 0).all()), key="statm_scatter")
    out = data[["nome", "cod6", x, y]].rename(columns={"nome": "Município", "cod6": "Código", x: variables[x],
                                                      y: variables[y]})
    tables.download(out, "estatistica_municipios.csv", key="statm_dl")


def main() -> None:
    ui.page_header("Exploração estatística",
                   "Relações entre variáveis quantitativas. Resultados exploratórios: associação, não causa.")
    level = st.segmented_control("Nível de análise", ["Registros do CAGED", "Municípios"],
                                 default="Registros do CAGED", key="stat_level") or "Registros do CAGED"
    if level == "Municípios":
        municipal_level()
    else:
        record_level()


ui.guarded(main)
