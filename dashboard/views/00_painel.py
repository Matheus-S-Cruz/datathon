"""Seção 1 — Visão geral: indicadores-chave e os 6 gráficos que respondem à pergunta central.

Ordem de leitura: pergunta → recorte aplicado → KPIs → resposta em 3 leituras → evidências (6 gráficos,
cada um com selo de escopo e "Ver dados e método") → limites e próximos passos.

Fontes: tabelas do pipeline (outputs/) e bases do IBGE (data/external/), via services/analytics.py.
Nenhum cálculo é feito aqui além de selecionar colunas para exibir: cada gráfico e sua tabela em
"Ver dados" saem do mesmo DataFrame.
"""

import pandas as pd
import streamlit as st

from dashboard import formatting as fmt
from dashboard.components import charts, filters, tables, ui
from dashboard.services import analytics as A
from src import glossario as G

PERIODO = G.PERIODO


def kpis(scope: A.Scope) -> None:
    k = A.kpis(scope)
    sal_sc = A.salario_estado()   # mediana sem zeros de SC inteira (manchete do salário)
    by_sector = not scope.all_sections
    na = "indisponível com recorte setorial (o estoque do CEMPRE não é aberto por setor)"
    ui.kpi_row([
        dict(label="Saldo de vagas formais", value=fmt.signed(k["saldo"]), icon="trending_up", accent="blue",
             note=f"{fmt.integer(k['admissoes'])} admissões · {fmt.integer(k['desligamentos'])} desligamentos",
             help=G.texto("saldo", "kpi_ajuda")),
        dict(label="Saldo por 10 mil habitantes", value=fmt.num(k["saldo_por_10k"], 1), icon="groups",
             accent="violet", note=f"{fmt.integer(k['municipios'])} municípios no recorte",
             help=G.texto("saldo_por_10k_censo", "kpi_ajuda")),
        dict(label="Crescimento do emprego formal",
             value="—" if by_sector else fmt.num(k["cresc_emprego_pct"], 2) + "%", icon="show_chart",
             accent="green", note=na if by_sector else
             f"sobre {fmt.integer(k['assalariados'])} assalariados (IBGE/CEMPRE 2024)",
             help=G.texto("cresc_emprego_pct", "kpi_ajuda")),
        dict(label="Taxa de rotatividade", value="—" if by_sector else fmt.num(k["rotatividade_pct"], 1) + "%",
             icon="autorenew", accent="orange", note=na if by_sector else G.texto("rotatividade_pct", "kpi_nota"),
             help=G.texto("rotatividade_pct", "kpi_ajuda")),
        dict(label="Salário mediano (SC)", value=fmt.brl(sal_sc["salario_mediano_s0"], 0), icon="payments",
             accent="amber",
             note=f"média do recorte {fmt.brl(k['salario_medio'], 0)} · {G.texto('salario_mediano', 'kpi_nota')}",
             help=G.texto("salario_mediano", "kpi_ajuda")),
    ])


# --------------------------------------------------------------------------- leituras


def findings() -> dict[str, list[str]]:
    """Leituras calculadas a partir dos dados (nada é texto fixo), sempre para o estado inteiro.
    Mesmas frases da versão anterior, agrupadas pelos três eixos da pergunta central."""
    reg = A.regions()
    top_g = reg.iloc[0]
    top_r = reg.sort_values("rotatividade_pct", ascending=False).iloc[0]
    sec = A.sectors()
    ind = sec[sec["industrial"]].sort_values("saldo", ascending=False)
    mi = A.macro(industrial_only=True)
    neg = mi[mi["saldo"] < 0].sort_values("saldo")
    sg = A.table("salario_por_grau").set_index("grau_cod")
    med, sup = sg.loc[7, "salario_mediano_s0"], sg.loc[9, "salario_mediano_s0"]
    onde = [
        f"**Expansão:** a região de **{top_g['regiao']}** tem o maior crescimento do emprego formal "
        f"({fmt.num(top_g['cresc_emprego_pct'], 2)}% sobre o estoque; saldo {fmt.signed(top_g['saldo'])}).",
        f"**Reposição:** **{top_r['regiao']}** tem a maior rotatividade ({fmt.num(top_r['rotatividade_pct'], 1)}%)"
        + (" — muita troca de trabalhadores para um crescimento líquido abaixo da média do estado."
           if top_r["cresc_emprego_pct"] < A.kpis(A.Scope())["cresc_emprego_pct"] else "."),
    ]
    setores = [
        f"**Indústria:** {ind.iloc[0]['setor']} lidera o saldo industrial ({fmt.signed(ind.iloc[0]['saldo'])}); "
        f"{ind.iloc[-1]['setor']} fecha com {fmt.signed(ind.iloc[-1]['saldo'])}.",
    ]
    if not neg.empty:
        op = mi[mi["cbo_grande_grupo"].str.contains("Operacional")]["saldo"].sum()
        setores.append("**Qualificação:** na indústria, o saldo é negativo em "
                       + ", ".join(f"{r.cbo_grande_grupo} ({fmt.signed(r.saldo)})" for r in neg.itertuples())
                       + (f", enquanto a base operacional cresce ({fmt.signed(op)})." if op > 0 else "."))
    renda = [f"**Renda:** Nos registros de movimentações com superior completo, o salário mediano (sem zeros) "
             f"é de {fmt.brl(sup, 0)}, contra {fmt.brl(med, 0)} para o médio completo — uma diferença "
             f"de aproximadamente {fmt.pct(sup / med - 1, 0)}."]
    return {"onde": onde, "setores": setores, "renda": renda}


def readings() -> None:
    f = findings()
    ui.section("A resposta em 3 leituras", "calculadas a partir dos dados, para Santa Catarina inteira")
    c = st.columns(3, gap="medium")
    with c[0]:
        ui.reading_card("Onde", f["onde"], "ev-onde", "Ver a evidência no mapa e nas regiões", key="read_onde")
    with c[1]:
        ui.reading_card("Quais setores e funções", f["setores"], "ev-setores",
                        "Ver a evidência por setor e ocupação", key="read_setores")
    with c[2]:
        ui.reading_card("Renda e escolaridade", f["renda"], "ev-renda",
                        "Ver a relação entre renda e escolaridade", key="read_renda",
                        note=G.nota("renda_ressalva"))


# ---------------------------------------------------------------- evidência 1 · onde


def map_card(scope: A.Scope, mun: pd.DataFrame) -> None:
    geo = A.geojson()
    with ui.card("Onde estão a expansão e a retração",
                 "Saldo de cada município: azul = cria vagas, laranja = perde, cinza = estável. "
                 f"Período {PERIODO.split(' (')[0]}.", key="map", scope="recorte"):
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
        used = ["mun_cod", "municipio", col] + [c for c, _, _ in hover]
        tables.data_view(
            mun[used], f"mapa_{col}.csv", key="pn_map_data",
            notes=[f"Período: {PERIODO}. Abrangência: municípios de SC no recorte atual "
                   f"({fmt.integer(len(mun))}).",
                   G.nota("mapa_formulas"),
                   G.nota("limite_fluxo")],
            rename={"mun_cod": "Código do município (6 dígitos)", "municipio": "Município",
                    "saldo_por_10k": "Saldo por 10 mil hab.", "cresc_emprego_pct": "Crescimento do emprego (%)",
                    "saldo": "Saldo (vagas)", "rotatividade_pct": "Rotatividade (%)", "populacao": "População",
                    "salario_medio": "Salário médio (R$)", "regiao_intermediaria": "Região intermediária (IBGE)"},
            ints=["saldo", "populacao"], money=["salario_medio"],
            dec={"saldo_por_10k": 1, "cresc_emprego_pct": 2, "rotatividade_pct": 1})


def regions_card() -> None:
    reg = A.regions()
    state = A.kpis(A.Scope())
    with ui.card("Expansão ou só reposição? As 7 regiões do estado",
                 "Direita = o emprego formal cresce mais; alto = troca mais trabalhadores. "
                 "Linhas = média de SC; bolha = estoque de assalariados.", key="regions", scope="estado"):
        fig = charts.bubble(reg, "cresc_emprego_pct", "rotatividade_pct", None, "assalariados", "regiao",
                            "Crescimento do emprego (%)", "Rotatividade (%)", text_labels=True, height=470,
                            x_fmt=lambda v: fmt.num(v, 2) + "%", y_fmt=lambda v: fmt.num(v, 1) + "%",
                            hover=[("saldo", "Saldo", fmt.signed), ("assalariados", "Assalariados", fmt.integer),
                                   ("part_industria_vab_2021", "Indústria no VAB (2021)", fmt.pct)],
                            ref_x=state["cresc_emprego_pct"], ref_y=state["rotatividade_pct"])
        charts.show(fig, key="pn_regions")
        used = ["regiao", "cresc_emprego_pct", "rotatividade_pct", "assalariados", "saldo",
                "part_industria_vab_2021"]
        tables.data_view(
            reg[used], "regioes_intermediarias.csv", key="pn_regions_data",
            notes=[f"Período: {PERIODO}. Abrangência: as 7 regiões geográficas intermediárias do IBGE "
                   "(Santa Catarina inteira; não muda com os filtros).",
                   G.nota("regioes_formulas"),
                   f"Linhas de referência (média de SC): crescimento {fmt.num(state['cresc_emprego_pct'], 2)}%, "
                   f"rotatividade {fmt.num(state['rotatividade_pct'], 1)}%.",
                   G.nota("regioes_leitura")],
            rename={"regiao": "Região intermediária", "cresc_emprego_pct": "Crescimento do emprego (%)",
                    "rotatividade_pct": "Rotatividade (%)", "assalariados": "Assalariados (CEMPRE 2024)",
                    "saldo": "Saldo (vagas)", "part_industria_vab_2021": "Indústria no VAB (2021)"},
            ints=["assalariados", "saldo"], dec={"cresc_emprego_pct": 2, "rotatividade_pct": 1},
            pct=["part_industria_vab_2021"])


# -------------------------------------------------------- evidência 2 · setores e funções


def sectors_card(scope: A.Scope) -> None:
    sec = A.sectors_in_scope(scope).sort_values("saldo", ascending=False)
    with ui.card("Quais setores lideram a criação e a perda de vagas",
                 "Saldo (admissões − desligamentos) por seção CNAE. Azul = seções industriais (B, C, D, F); "
                 "cinza = demais.", key="sectors", scope="recorte"):
        sec = sec.assign(rotulo=sec["secao"] + " · " + sec["setor"].str.slice(0, 42))
        charts.show(charts.emphasis_bars(sec, "rotulo", "saldo", sec["industrial"], "Saldo de vagas",
                                         "Industrial", "Demais setores"), key="pn_sectors")
        view = sec[["secao", "setor", "saldo", "industrial"]].assign(
            industrial=sec["industrial"].map({True: "Industrial", False: "Demais setores"}))
        tables.data_view(
            view, "saldo_por_setor.csv", key="pn_sectors_data",
            notes=[f"Período: {PERIODO}. Abrangência: seções CNAE no recorte atual ({len(sec)}).",
                   "No gráfico, o nome do setor aparece cortado em 42 caracteres; aqui está completo."],
            rename={"secao": "Seção CNAE", "setor": "Setor", "saldo": "Saldo (vagas)", "industrial": "Grupo"},
            ints=["saldo"])


def macro_card() -> None:
    with ui.card("O gargalo é operacional ou técnico?",
                 "Saldo por macrofamília de ocupações (Grande Grupo da CBO-2002). Laranja = mais desligamentos "
                 "que admissões.", key="macro", scope="estado"):
        scope_lbl = st.segmented_control("Setores", ["Indústria (B, C, D, F)", "Todos os setores"],
                                         default="Indústria (B, C, D, F)", key="pn_macro",
                                         label_visibility="collapsed") or "Indústria (B, C, D, F)"
        m = A.macro(industrial_only=scope_lbl.startswith("Indústria")).sort_values("saldo", ascending=False)
        charts.show(charts.signed_hbars(m, "cbo_grande_grupo", "saldo", "Saldo de vagas", extra=[
            ("salario_mediano_s0", "Salário mediano", lambda v: fmt.brl(v, 0)),
            ("pct_superior", "Com superior completo", fmt.pct),
            ("admissoes", "Admissões", fmt.integer), ("desligamentos", "Desligamentos", fmt.integer)]),
            key="pn_macro_chart")
        used = ["cbo_grande_grupo", "saldo", "salario_mediano_s0", "salario_medio", "pct_superior",
                "admissoes", "desligamentos"]
        tables.data_view(
            m[used], "macrofamilias.csv", key="pn_macro_data",
            notes=[f"Período: {PERIODO}. Abrangência: {scope_lbl[0].lower() + scope_lbl[1:]} de Santa Catarina inteira — não "
                   "acompanha os filtros de região e população da barra lateral. Salário em R$ por mês.",
                   G.nota("macro_agrupamento"),
                   G.nota("macro_salario")],
            rename={"cbo_grande_grupo": "Macrofamília", "saldo": "Saldo (vagas)",
                    "salario_mediano_s0": "Salário mediano (R$, sem zeros)", "salario_medio": "Salário médio (R$)",
                    "pct_superior": "Com superior completo", "admissoes": "Admissões", "desligamentos": "Desligamentos"},
            ints=["saldo", "admissoes", "desligamentos"], money=["salario_mediano_s0", "salario_medio"],
            pct=["pct_superior"])


# ------------------------------------------------- evidência 3 · renda e escolaridade


def salary_card() -> None:
    sg = A.table("salario_por_grau").sort_values("grau_ord")
    with ui.card("Salário mediano por escolaridade",
                 "Mediana do salário declarado (exclui zeros), em R$ por mês. Quase não muda até o médio "
                 "completo e sobe a partir do superior.", key="salary", scope="estado"):
        charts.show(charts.ordinal_bars(sg, "grau", "salario_mediano_s0", "Salário mediano", n_col="n_salario_s0"),
                    key="pn_salary")
        tables.data_view(
            sg[["grau", "salario_mediano_s0", "salario_medio", "n_salario_s0", "n"]],
            "salario_por_escolaridade.csv", key="pn_salary_data",
            notes=[f"Período: {PERIODO}. Abrangência: todas as admissões e desligamentos de Santa Catarina "
                   "(não muda com os filtros). Unidade: R$ por mês.",
                   G.nota("salario_relacao")],
            rename={"grau": "Grau de instrução", "salario_mediano_s0": "Salário mediano (R$, sem zeros)",
                    "salario_medio": "Salário médio (R$)", "n_salario_s0": "Registros com salário > 0",
                    "n": "Movimentações"},
            money=["salario_mediano_s0", "salario_medio"], ints=["n_salario_s0", "n"])


def scatter_card(mun: pd.DataFrame) -> None:
    with ui.card("Renda, escolaridade e saldo nos municípios",
                 "Cada bolha é um município: salário médio × % de movimentações com superior completo. "
                 "Cor = saldo por 10 mil hab.; tamanho = nº de movimentações.", key="scatter", scope="recorte"):
        d = mun.assign(pct_sup=mun["pct_superior"] * 100)
        charts.show(charts.bubble(d, "salario_medio", "pct_sup", "saldo_por_10k", "movimentacoes", "municipio",
                                  "Salário médio (R$)", "Com superior completo (%)", "Saldo / 10 mil hab.",
                                  x_fmt=lambda v: fmt.brl(v, 0), y_fmt=lambda v: fmt.num(v, 1) + "%",
                                  hover=[("saldo", "Saldo", fmt.signed),
                                         ("saldo_por_10k", "Saldo / 10 mil hab.", lambda v: fmt.num(v, 1))],
                                  height=400), key="pn_scatter")
        plotted = d.dropna(subset=["salario_medio", "pct_sup"])  # o gráfico de bolhas descarta linhas sem x/y
        used = ["municipio", "salario_medio", "pct_sup", "saldo_por_10k", "movimentacoes", "saldo"]
        tables.data_view(
            plotted[used], "renda_escolaridade_municipios.csv", key="pn_scatter_data",
            notes=[f"Período: {PERIODO}. Abrangência: municípios no recorte atual com salário e escolaridade "
                   f"disponíveis ({fmt.integer(len(plotted))} de {fmt.integer(len(d))}).",
                   G.nota("dispersao_relacao")],
            rename={"municipio": "Município", "salario_medio": "Salário médio (R$)",
                    "pct_sup": "Com superior completo (%)", "saldo_por_10k": "Saldo por 10 mil hab.",
                    "movimentacoes": "Movimentações", "saldo": "Saldo (vagas)"},
            money=["salario_medio"], ints=["movimentacoes", "saldo"], dec={"pct_sup": 1, "saldo_por_10k": 1})


# ----------------------------------------------------------------------- fecho


def closing() -> None:
    c = st.columns([0.62, 0.38], gap="medium")
    with c[0], ui.card("Fontes e limites da análise", key="limits"):
        st.markdown(
            "- **Fontes:** Novo CAGED/MTE (organização do Datathon); indicadores municipais (IBGE, PNUD, DATASUS, "
            "Siconfi); IBGE — CEMPRE 2024, PIB dos Municípios, Divisão Regional e Malha Municipal.\n"
            "- **Limites:** o CAGED mede fluxo, não estoque; taxas sobre o CEMPRE são aproximações; IDHM é de "
            "2010; o salário usa a **mediana sem zeros** como medida principal (a média, exibida como "
            "complemento, é puxada por valores extremos). Ver `docs/metodologia_salarial.md`.")
    with c[1], ui.card("Explore mais", key="more"):
        st.page_link("views/02_caged_explorer.py", label="Consultar os microdados no Explorador",
                     icon=":material/table_view:")
        st.page_link("views/10_territorio.py", label="Rankings de municípios e rotatividade", icon=":material/map:")
        st.page_link("views/11_setores.py", label="Polos industriais por região", icon=":material/factory:")
        st.page_link("views/14_contexto_ibge.py", label="Contexto regional do IBGE", icon=":material/public:")


def main() -> None:
    ui.header("Mercado de Trabalho Industrial de Santa Catarina",
              "Santa Catarina · Novo CAGED de set/2025 a ago/2026 (3,4 milhões de movimentações) cruzado com "
              "dados municipais e bases públicas do IBGE.", eyebrow="Pulso Industry · Visão geral")
    ui.question_banner()
    scope = filters.analysis_scope()
    ui.scope_bar(scope.describe())
    kpis(scope)
    readings()
    mun = A.municipal(scope)

    ui.section("Onde o emprego cresce e onde ele gira", anchor="ev-onde", step="Evidência 1")
    c = st.columns([0.58, 0.42], gap="medium")
    with c[0]:
        map_card(scope, mun)
    with c[1]:
        regions_card()

    ui.section("Setores e funções", "quem cria vagas e em que tipo de ocupação", anchor="ev-setores",
               step="Evidência 2")
    c = st.columns([0.55, 0.45], gap="medium")
    with c[0]:
        sectors_card(scope)
    with c[1]:
        macro_card()

    ui.section("Como a renda se relaciona com a escolaridade", anchor="ev-renda", step="Evidência 3")
    c = st.columns([0.45, 0.55], gap="medium")
    with c[0]:
        salary_card()
    with c[1]:
        scatter_card(mun)

    closing()


ui.guarded(main)
