"""Seção 1 — Visão geral: indicadores-chave e os 6 gráficos que respondem à pergunta central.

Fontes: tabelas do pipeline (outputs/) e bases do IBGE (data/external/), via services/analytics.py.
"""

import pandas as pd
import streamlit as st

from dashboard import formatting as fmt
from dashboard.components import charts, filters, ui
from dashboard.services import analytics as A


def kpis(scope: A.Scope) -> None:
    k = A.kpis(scope)
    by_sector = not scope.all_sections
    na = "indisponível com recorte setorial (o estoque do CEMPRE não é aberto por setor)"
    ui.kpi_row([
        dict(label="Saldo de vagas formais", value=fmt.signed(k["saldo"]), icon="trending_up", accent="blue",
             note=f"{fmt.integer(k['admissoes'])} admissões · {fmt.integer(k['desligamentos'])} desligamentos",
             help="Admissões − desligamentos no Novo CAGED, set/2025 a ago/2026."),
        dict(label="Saldo por 10 mil habitantes", value=fmt.num(k["saldo_por_10k"], 1), icon="groups",
             accent="violet", note=f"{fmt.integer(k['municipios'])} municípios no recorte",
             help="Métrica do guia do Datathon: normaliza a comparação entre cidades de portes diferentes."),
        dict(label="Crescimento do emprego formal",
             value="—" if by_sector else fmt.num(k["cresc_emprego_pct"], 2) + "%", icon="show_chart",
             accent="green", note=na if by_sector else
             f"sobre {fmt.integer(k['assalariados'])} assalariados (IBGE/CEMPRE 2024)",
             help="Saldo do CAGED ÷ pessoal assalariado do CEMPRE 2024 × 100."),
        dict(label="Taxa de rotatividade", value="—" if by_sector else fmt.num(k["rotatividade_pct"], 1) + "%",
             icon="autorenew", accent="orange", note=na if by_sector else "reposição: mín(adm., desl.) ÷ estoque",
             help="Conceito DIEESE: parte do fluxo que é troca de trabalhadores, não vaga nova."),
        dict(label="Salário médio nas movimentações", value=fmt.brl(k["salario_medio"], 0), icon="payments",
             accent="amber", note=f"{fmt.pct(k['pct_superior'])} com superior completo ou mais",
             help="Média do salário declarado em admissões e desligamentos, ponderada pelo nº de movimentações."),
    ])


def map_card(scope: A.Scope, mun: pd.DataFrame) -> None:
    geo = A.geojson()
    with ui.card("Onde estão a expansão e a retração",
                 "Cada município colorido pelo saldo: azul = cria vagas, laranja = perde vagas, "
                 "cinza = estável. Passe o mouse para ver os números.", key="map", tag="Território"):
        options = ["Saldo por 10 mil hab."] + ([] if not scope.all_sections else ["Crescimento do emprego (%)"])
        metric = st.segmented_control("Métrica do mapa", options, default=options[0], key="pn_map_metric",
                                      label_visibility="collapsed") or options[0]
        col, title = (("saldo_por_10k", "Saldo / 10 mil hab.") if metric.startswith("Saldo")
                      else ("cresc_emprego_pct", "Crescimento (%)"))
        if geo is None or mun.empty:
            st.info("Sem municípios para exibir com o recorte atual.", icon=":material/info:")
            return
        hover = [("saldo", "Saldo", fmt.signed), ("populacao", "População", fmt.integer),
                 ("salario_medio", "Salário médio", lambda v: fmt.brl(v, 0)),
                 ("regiao_intermediaria", "Região", str)]
        if scope.all_sections:
            hover.insert(1, ("rotatividade_pct", "Rotatividade", lambda v: fmt.num(v, 1) + "%"))
        charts.show(charts.choropleth(mun, geo, col, title, hover, height=420), key="pn_map")


def regions_card() -> None:
    reg = A.regions()
    state = A.kpis(A.Scope())
    with ui.card("Expansão ou só reposição? As 7 regiões do estado",
                 "Direita = emprego formal cresce mais. Alto = mais rotatividade. Regiões no alto e à "
                 "esquerda trocam muitos trabalhadores sem crescer — sinal de dificuldade de reter mão de obra. "
                 "Linhas = média de SC; tamanho = estoque de assalariados.", key="regions", tag="IBGE + CAGED"):
        fig = charts.bubble(reg, "cresc_emprego_pct", "rotatividade_pct", None, "assalariados", "regiao",
                            "Crescimento do emprego (%)", "Rotatividade (%)", text_labels=True, height=470,
                            x_fmt=lambda v: fmt.num(v, 2) + "%", y_fmt=lambda v: fmt.num(v, 1) + "%",
                            hover=[("saldo", "Saldo", fmt.signed), ("assalariados", "Assalariados", fmt.integer),
                                   ("part_industria_vab_2021", "Indústria no VAB (2021)", fmt.pct)],
                            ref_x=state["cresc_emprego_pct"], ref_y=state["rotatividade_pct"])
        charts.show(fig, key="pn_regions")


def sectors_card(scope: A.Scope) -> None:
    sec = A.sectors_in_scope(scope).sort_values("saldo", ascending=False)
    with ui.card("Quais setores lideram a criação e a perda de vagas",
                 "Saldo por seção CNAE. Em azul, as seções industriais (B, C, D, F); demais em cinza.",
                 key="sectors", tag="Setores"):
        sec = sec.assign(rotulo=sec["secao"] + " · " + sec["setor"].str.slice(0, 42))
        charts.show(charts.emphasis_bars(sec, "rotulo", "saldo", sec["industrial"], "Saldo de vagas",
                                         "Industrial", "Demais setores"), key="pn_sectors")


def macro_card() -> None:
    with ui.card("O gargalo é operacional ou técnico?",
                 "Saldo por macrofamília ocupacional (CBOs agrupados pelo Grande Grupo da CBO-2002). "
                 "Laranja = mais desligamentos que admissões no período.", key="macro", tag="CBO"):
        scope_lbl = st.segmented_control("Setores", ["Indústria (B, C, D, F)", "Todos os setores"],
                                         default="Indústria (B, C, D, F)", key="pn_macro",
                                         label_visibility="collapsed") or "Indústria (B, C, D, F)"
        m = A.macro(industrial_only=scope_lbl.startswith("Indústria")).sort_values("saldo", ascending=False)
        charts.show(charts.signed_hbars(m, "cbo_grande_grupo", "saldo", "Saldo de vagas", extra=[
            ("salario_medio", "Salário médio", lambda v: fmt.brl(v, 0)),
            ("pct_superior", "Com superior completo", fmt.pct),
            ("admissoes", "Admissões", fmt.integer), ("desligamentos", "Desligamentos", fmt.integer)]),
            key="pn_macro_chart")
        st.caption("Recorte estadual: não acompanha os filtros de região e população.")


def salary_card() -> None:
    sg = A.table("salario_por_grau").sort_values("grau_ord")
    with ui.card("Quanto a escolaridade paga",
                 "Salário médio por grau de instrução (todas as movimentações de SC). O salário quase não muda "
                 "até o médio completo e salta a partir do superior.", key="salary", tag="Renda × escolaridade"):
        charts.show(charts.ordinal_bars(sg, "grau", "salario_medio", "Salário médio", n_col="n"),
                    key="pn_salary")


def scatter_card(mun: pd.DataFrame) -> None:
    with ui.card("Renda e escolaridade explicam o saldo dos municípios?",
                 "Cada bolha é um município: salário médio × % de movimentações com superior completo. "
                 "Cor = saldo por 10 mil hab.; tamanho = nº de movimentações.", key="scatter",
                 tag="Renda × escolaridade"):
        d = mun.assign(pct_sup=mun["pct_superior"] * 100)
        charts.show(charts.bubble(d, "salario_medio", "pct_sup", "saldo_por_10k", "movimentacoes", "municipio",
                                  "Salário médio (R$)", "Com superior completo (%)", "Saldo / 10 mil hab.",
                                  x_fmt=lambda v: fmt.brl(v, 0), y_fmt=lambda v: fmt.num(v, 1) + "%",
                                  hover=[("saldo", "Saldo", fmt.signed),
                                         ("saldo_por_10k", "Saldo / 10 mil hab.", lambda v: fmt.num(v, 1))],
                                  height=400), key="pn_scatter")


def findings(scope: A.Scope) -> None:
    """Leituras calculadas a partir dos dados (nada é texto fixo)."""
    reg = A.regions()
    top_g = reg.iloc[0]
    top_r = reg.sort_values("rotatividade_pct", ascending=False).iloc[0]
    sec = A.sectors()
    ind = sec[sec["industrial"]].sort_values("saldo", ascending=False)
    mi = A.macro(industrial_only=True)
    neg = mi[mi["saldo"] < 0].sort_values("saldo")
    sg = A.table("salario_por_grau").set_index("grau_cod")
    med, sup = sg.loc[7, "salario_medio"], sg.loc[9, "salario_medio"]
    items = [
        f"**Expansão:** a região de **{top_g['regiao']}** tem o maior crescimento do emprego formal "
        f"({fmt.num(top_g['cresc_emprego_pct'], 2)}% sobre o estoque; saldo {fmt.signed(top_g['saldo'])}).",
        f"**Reposição:** **{top_r['regiao']}** tem a maior rotatividade ({fmt.num(top_r['rotatividade_pct'], 1)}%)"
        + (" — muita troca de trabalhadores para um crescimento líquido abaixo da média do estado."
           if top_r["cresc_emprego_pct"] < A.kpis(A.Scope())["cresc_emprego_pct"] else "."),
        f"**Indústria:** {ind.iloc[0]['setor']} lidera o saldo industrial ({fmt.signed(ind.iloc[0]['saldo'])}); "
        f"{ind.iloc[-1]['setor']} fecha com {fmt.signed(ind.iloc[-1]['saldo'])}.",
    ]
    if not neg.empty:
        op = mi[mi["cbo_grande_grupo"].str.contains("Operacional")]["saldo"].sum()
        items.append("**Qualificação:** na indústria, o saldo é negativo em "
                     + ", ".join(f"{r.cbo_grande_grupo} ({fmt.signed(r.saldo)})" for r in neg.itertuples())
                     + (f", enquanto a base operacional cresce ({fmt.signed(op)})." if op > 0 else "."))
    items.append(f"**Renda:** superior completo paga {fmt.brl(sup, 0)} em média, contra {fmt.brl(med, 0)} "
                 f"no médio completo ({fmt.pct(sup / med - 1, 0)} a mais).")
    with ui.card("Principais leituras", "Calculadas a partir dos dados, para todo o estado.", key="findings",
                 tag="Resumo"):
        st.markdown("\n".join(f"- {i}" for i in items))


def main() -> None:
    ui.header("Raio-X do Mercado de Trabalho Industrial",
              "Santa Catarina · Novo CAGED de set/2025 a ago/2026 (3,4 milhões de movimentações) cruzado com "
              "dados municipais e bases públicas do IBGE.", eyebrow="Visão geral")
    ui.question_banner()
    scope = filters.analysis_scope()
    ui.active_filters(scope.describe())
    kpis(scope)
    mun = A.municipal(scope)

    ui.section("Território", "onde o emprego cresce e onde ele gira")
    c = st.columns([0.58, 0.42], gap="medium")
    with c[0]:
        map_card(scope, mun)
    with c[1]:
        regions_card()

    ui.section("Setores e qualificação", "quem cria vagas e em que tipo de função")
    c = st.columns([0.55, 0.45], gap="medium")
    with c[0]:
        sectors_card(scope)
    with c[1]:
        macro_card()

    ui.section("Renda e escolaridade", "a causa-raiz dos gargalos")
    c = st.columns([0.45, 0.55], gap="medium")
    with c[0]:
        salary_card()
    with c[1]:
        scatter_card(mun)

    findings(scope)
    st.caption("Fontes: Novo CAGED/MTE (organização do Datathon); indicadores municipais (IBGE, PNUD, DATASUS, "
               "Siconfi); IBGE — CEMPRE 2024, PIB dos Municípios, Divisão Regional e Malha Municipal. "
               "Limites: o CAGED mede fluxo, não estoque; taxas sobre o CEMPRE são aproximações; IDHM é de 2010; "
               "salários declarados podem conter valores extremos.")


ui.guarded(main)
