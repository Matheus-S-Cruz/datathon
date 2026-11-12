"""Visualizações Essenciais — painel principal.

Capa: mapa 3D das mesorregiões (clique numa região para filtrar o painel inteiro).
Abaixo: abas de storytelling (Território, Setores, Renda × Escolaridade, Macrofamílias/IA),
todas recalculadas para a região selecionada (ou Santa Catarina inteira).
"""
import plotly.express as px
import streamlit as st

from dashboard import dados as D
from dashboard.mapa3d import mapa_sc, valor_selecionado

D.checar_tabelas()

# ------------------------------------------------------------------ estado / filtros
if "regiao_sel" not in st.session_state:
    st.session_state.regiao_sel = None


def ao_clicar():
    st.session_state.regiao_sel = valor_selecionado(st.session_state["mapa"].selecionada)


def ver_sc():
    st.session_state.regiao_sel = None


with st.sidebar:
    st.header("Filtros")
    apenas_ind = st.toggle(
        "Apenas setores industriais", value=False,
        help="Seções CNAE B (Extrativas), C (Transformação), D (Eletricidade e gás) e F (Construção).",
    )

regiao = st.session_state.regiao_sel
nome_recorte = regiao or "Santa Catarina"
cubo = D.recorte(D.cubo(), regiao, apenas_ind)
ind = D.indicadores(cubo)
pop = D.populacao(regiao)

# ------------------------------------------------------------------------ cabeçalho
# Título, subtítulo colado ao título e a chamada da pergunta central em texto simples.
st.html("""
<style>
  .cab-titulo { font-size: 2.6rem; font-weight: 700; line-height: 1.15; margin: 0; padding: 0; }
  .cab-sub    { font-size: .875rem; opacity: .65; margin: .15rem 0 0 0; }
  .cab-chamada{ font-size: .95rem; margin: .9rem 0 .2rem 0; opacity: .9; }
  .observacao { font-size: .9rem; line-height: 1.45; margin-top: .4rem; }
  .observacao .rotulo { font-weight: 600; opacity: .7; }
</style>
<div class="cab-titulo">Raio-X do Mercado de Trabalho em Santa Catarina</div>
<p class="cab-sub">Novo CAGED · declarações de set/2025 a ago/2026 · 3,4 milhões de admissões e desligamentos</p>
<p class="cab-chamada">Descubra quais regiões e setores industriais de SC enfrentam <b>apagão de mão de obra</b>
ou <b>expansão acelerada</b>, e como <b>renda e escolaridade</b> explicam esses gargalos.</p>
""")

# --------------------------------------------------------------------- mapa (capa)
reg = D.carregar("agg_mesorregiao").rename(columns={"mesorregiao": "regiao"}).copy()
reg["dica_html"] = [
    f"<b>{r.regiao}</b><br>Saldo: {D.fmt_int(r.saldo, True)} vagas"
    f"<br>Saldo/10 mil hab.: {D.fmt_dec(r.saldo_por_10k, 1, True)}"
    for r in reg.itertuples()
]

col_mapa, col_kpi = st.columns([3, 2], gap="large")
with col_mapa:
    mapa_sc(reg, selecionada=regiao, key="mapa", on_click=ao_clicar)
    st.caption("Clique numa região para filtrar o painel · clique de novo para voltar ao estado")

with col_kpi:
    st.subheader(nome_recorte + (" · indústria" if apenas_ind else ""))
    k1, k2 = st.columns(2)
    k1.metric("Saldo de vagas", D.fmt_int(ind.saldo, True), border=True)
    k2.metric("Saldo por 10 mil hab.", D.fmt_dec(ind.saldo / pop * 10_000, 1, True),
              help="Saldo ÷ população × 10.000. Compara regiões de tamanhos diferentes.", border=True)
    k1.metric("Admissões", D.fmt_int(ind.admissoes), border=True)
    k2.metric("Desligamentos", D.fmt_int(ind.desligamentos), border=True)
    k1.metric("Desligamentos a pedido", D.fmt_pct(ind.pct_a_pedido),
              help="Parcela dos desligamentos feitos pelo próprio trabalhador. Alta = mercado "
                   "aquecido / dificuldade de reter pessoas (indício de apagão).", border=True)
    dif = ind.salario_adm - ind.salario_desl
    k2.metric("Salário de admissão", D.fmt_reais(ind.salario_adm),
              delta=f"{'+' if dif >= 0 else '-'}R$ {D.fmt_int(abs(dif))} vs. desligados",
              delta_color="off",
              help="Média dos salários de admissão (faixa válida de R$ 500 a R$ 50.000).", border=True)

    # alerta: macrofamília industrial com mais reposição (desliga ≥ contrata) e volume relevante
    macro_r = D.por_grupo(cubo, ["macrofamilia"])
    alerta = macro_r[macro_r["macrofamilia"].isin(D.MACRO_INDUSTRIAIS) & (macro_r["movimentacoes"] > 3000)]
    if not alerta.empty:
        a = alerta.sort_values("reposicao", ascending=False).iloc[0]
        st.html(
            f'<div class="observacao"><span class="rotulo">Observação:</span> '
            f'<b>{D.NOMES_MACRO[a.macrofamilia]}</b> tem {D.fmt_dec(a.reposicao, 2)} desligamentos por '
            f'admissão (saldo {D.fmt_int(a.saldo, True)}) e {D.fmt_pct(a.pct_a_pedido)} das saídas são '
            f'a pedido do trabalhador.</div>')
    if regiao:
        st.button("Ver Santa Catarina inteira", on_click=ver_sc, icon=":material/zoom_out_map:")

st.divider()

# ------------------------------------------------------------------------------ abas
aba_terr, aba_setor, aba_socio, aba_cbo = st.tabs(
    [":material/map: Território", ":material/factory: Setores",
     ":material/school: Renda × Escolaridade", ":material/smart_toy: Macrofamílias (IA)"]
)

mun = D.carregar("agg_municipio").merge(
    D.carregar("municipios")[["mun_cod", "mesorregiao"]], on="mun_cod", how="left")
if regiao:
    mun = mun[mun["mesorregiao"] == regiao]

# ----------------------------------------------------------------------- Território
with aba_terr:
    st.subheader(f"Onde estão os polos de expansão e de retração ({nome_recorte})")
    st.caption("Saldo por 10 mil habitantes normaliza cidades de portes diferentes. "
               "Giro alto com saldo baixo/negativo = reposição constante (rotatividade).")
    min_pop = st.slider("População mínima do município", 0, 50_000, 5_000, step=1_000,
                        help="Evita que municípios muito pequenos dominem os rankings por 10 mil hab.")
    mun_f = mun[mun["populacao"] >= min_pop].copy()

    coords = D.coordenadas()
    if coords is not None and not mun_f.empty:
        mapa_df = mun_f.merge(coords, on="mun_cod", how="inner")
        lim = float(mapa_df["saldo_por_10k"].abs().quantile(0.95)) or 1.0
        mapa_df["tam"] = mapa_df["giro_por_10k"].clip(lower=1)
        centro = {"lat": mapa_df["lat"].mean(), "lon": mapa_df["lon"].mean()} if regiao \
            else {"lat": -27.5, "lon": -50.6}
        fig = px.scatter_map(
            mapa_df, lat="lat", lon="lon", color="saldo_por_10k", size="tam", size_max=26,
            zoom=7.2 if regiao else 6.1, center=centro, color_continuous_scale="RdYlGn",
            range_color=[-lim, lim], hover_name="municipio", height=480,
            custom_data=["saldo", "saldo_por_10k", "giro_por_10k", "salario_medio", "populacao"],
            labels={"saldo_por_10k": "Saldo / 10 mil hab."},
        )
        fig.update_traces(hovertemplate=(
            "<b>%{hovertext}</b><br>Saldo: %{customdata[0]:+,.0f} vagas<br>"
            "Saldo por 10 mil hab.: %{customdata[1]:.1f}<br>Giro por 10 mil hab.: %{customdata[2]:,.0f}<br>"
            "Salário médio: R$ %{customdata[3]:,.0f}<br>População: %{customdata[4]:,.0f}<extra></extra>"))
        fig.update_layout(map_style="carto-positron", margin=dict(r=0, t=0, l=0, b=0))
        st.plotly_chart(fig, width="stretch")
        st.caption("Bolha = município · tamanho = giro (admissões + desligamentos) por 10 mil hab. · "
                   "cor = saldo por 10 mil hab.")

    col_a, col_b = st.columns(2)
    with col_a:
        top = mun_f.sort_values("saldo_por_10k", ascending=False).head(15)
        fig = px.bar(top, x="saldo_por_10k", y="municipio", orientation="h",
                     color="saldo_por_10k", color_continuous_scale="Greens",
                     title="Top 15 em expansão (saldo / 10 mil hab.)",
                     labels={"saldo_por_10k": "Saldo por 10 mil hab.", "municipio": ""})
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=480, coloraxis_showscale=False)
        st.plotly_chart(fig, width="stretch")
    with col_b:
        bot = mun_f.sort_values("saldo_por_10k").head(15)
        fig = px.bar(bot, x="saldo_por_10k", y="municipio", orientation="h",
                     color="saldo_por_10k", color_continuous_scale="Reds_r",
                     title="Top 15 em retração (saldo / 10 mil hab.)",
                     labels={"saldo_por_10k": "Saldo por 10 mil hab.", "municipio": ""})
        fig.update_layout(yaxis={"categoryorder": "total descending"}, height=480, coloraxis_showscale=False)
        st.plotly_chart(fig, width="stretch")

# -------------------------------------------------------------------------- Setores
with aba_setor:
    st.subheader(f"Setores que lideram a criação e a perda de vagas ({nome_recorte})")
    setores = D.carregar("agg_setor")[["seção", "setor"]]
    s = D.por_grupo(D.recorte(D.cubo(), regiao), ["seção"]).merge(setores, on="seção", how="left")
    s["tipo"] = s["seção"].map(lambda x: "Industrial" if x in D.SETORES_INDUSTRIAIS else "Demais")
    s = s[s["movimentacoes"] > 0].sort_values("saldo")
    fig = px.bar(s, x="saldo", y="setor", orientation="h", color="tipo",
                 color_discrete_map={"Industrial": "#1f6feb", "Demais": "#a9c4eb"},
                 custom_data=["admissoes", "desligamentos", "pct_a_pedido", "salario_adm"],
                 labels={"saldo": "Saldo de vagas", "setor": "", "tipo": ""}, height=620,
                 title="Saldo de vagas por setor (CNAE): azul-escuro = industrial")
    fig.update_traces(hovertemplate=(
        "<b>%{y}</b><br>Saldo: %{x:+,.0f}<br>Admissões: %{customdata[0]:,.0f}<br>"
        "Desligamentos: %{customdata[1]:,.0f}<br>A pedido: %{customdata[2]:.0%}<br>"
        "Salário de admissão: R$ %{customdata[3]:,.0f}<extra></extra>"))
    fig.update_layout(yaxis={"categoryorder": "total ascending"})  # ordena pelo saldo, não pela cor
    st.plotly_chart(fig, width="stretch")

    st.markdown("**Maiores polos industriais (município × setor)**")
    ms = D.carregar("agg_municipio_setor").merge(
        D.carregar("municipios")[["mun_cod", "mesorregiao"]], on="mun_cod", how="left")
    if regiao:
        ms = ms[ms["mesorregiao"] == regiao]
    ind_ms = ms[ms["seção"].isin(D.SETORES_INDUSTRIAIS)].sort_values("saldo", ascending=False).head(20)
    st.dataframe(
        ind_ms[["municipio", "setor", "saldo", "admissoes", "desligamentos", "salario_medio", "anos_estudo"]],
        column_config={
            "municipio": "Município", "setor": "Setor", "saldo": "Saldo",
            "admissoes": "Admissões", "desligamentos": "Desligamentos",
            "salario_medio": st.column_config.NumberColumn("Salário médio", format="R$ %.0f"),
            "anos_estudo": st.column_config.NumberColumn("Anos de estudo", format="%.1f"),
        }, hide_index=True, width="stretch")

# ----------------------------------------------------------- Renda × Escolaridade
with aba_socio:
    st.subheader(f"A causa-raiz: renda e escolaridade ({nome_recorte})")
    esc = D.carregar("escolaridade_regiao")
    if regiao:
        esc = esc[esc["mesorregiao"] == regiao]
    esc = esc[esc["grau_cod"] != 99]
    ORDEM = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6, 8: 7, 9: 8, 80: 9, 10: 10, 11: 11}
    g = (esc.groupby(["grau_cod", "grau_instr", "tipo"], as_index=False)[["n", "sal_soma", "sal_n"]].sum())
    g["ordem"] = g["grau_cod"].map(ORDEM)
    g["salario"] = g["sal_soma"] / g["sal_n"]
    g["movimento"] = g["tipo"].map({"ADM": "Admitidos", "DESL": "Desligados"})
    g = g.sort_values("ordem")
    ordem_graus = g.drop_duplicates("grau_instr")["grau_instr"].tolist()

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Salário médio por escolaridade: quem entra × quem sai**")
        fig = px.line(g, x="grau_instr", y="salario", color="movimento", markers=True,
                      category_orders={"grau_instr": ordem_graus},
                      color_discrete_map={"Admitidos": "#2ca02c", "Desligados": "#d62728"},
                      labels={"grau_instr": "", "salario": "Salário médio (R$)", "movimento": ""})
        fig.update_layout(xaxis_tickangle=-40, height=430)
        st.plotly_chart(fig, width="stretch")
        st.caption("Se quem é admitido ganha menos que quem sai no mesmo nível, há compressão salarial.")
    with col_b:
        st.markdown("**Admitidos × desligados por escolaridade**")
        fig = px.bar(g, x="grau_instr", y="n", color="movimento", barmode="group",
                     category_orders={"grau_instr": ordem_graus},
                     color_discrete_map={"Admitidos": "#2ca02c", "Desligados": "#d62728"},
                     labels={"grau_instr": "", "n": "Movimentações", "movimento": ""})
        fig.update_layout(xaxis_tickangle=-40, height=430)
        st.plotly_chart(fig, width="stretch")

    st.markdown("**Municípios: salário × escolaridade** (tamanho = movimentações, cor = saldo por 10 mil hab.)")
    d = mun.dropna(subset=["salario_medio", "anos_estudo"])
    d = d[d["populacao"] >= 5_000]
    lim = float(d["saldo_por_10k"].abs().quantile(0.95)) or 1.0
    fig = px.scatter(d, x="anos_estudo", y="salario_medio", size="movimentacoes", color="saldo_por_10k",
                     hover_name="municipio", color_continuous_scale="RdYlGn", range_color=[-lim, lim],
                     labels={"anos_estudo": "Anos de estudo (média dos movimentados)",
                             "salario_medio": "Salário médio (R$)", "saldo_por_10k": "Saldo / 10 mil hab."},
                     height=500)
    st.plotly_chart(fig, width="stretch")
    st.caption("Municípios com 5 mil habitantes ou mais. Escolaridade convertida em anos de estudo "
               "aproximados (o código do CAGED não é ordinal: 80 = pós-graduação).")

# ------------------------------------------------------------- Macrofamílias (IA)
with aba_cbo:
    st.subheader(f"Macrofamílias ocupacionais, CBOs agrupados por IA ({nome_recorte})")
    st.caption("Os 2.207 CBOs do CAGED foram classificados por um LLM em 14 macrofamílias "
               "(prompt e validação em `ia/`). Mostra se o gargalo é operacional (e de qual cadeia) "
               "ou técnico/engenharia.")
    m = macro_r.copy()
    m["nome"] = m["macrofamilia"].map(D.NOMES_MACRO)
    m = m[m["macrofamilia"] != "NAO_CLASSIFICADO"]
    m["foco"] = m["macrofamilia"].map(lambda x: "Indústria" if x in D.MACRO_INDUSTRIAIS else "Demais")

    col_a, col_b = st.columns(2)
    with col_a:
        fig = px.bar(m.sort_values("saldo"), x="saldo", y="nome", orientation="h", color="foco",
                     color_discrete_map={"Indústria": "#1f6feb", "Demais": "#a9c4eb"},
                     title="Saldo de vagas por macrofamília",
                     labels={"saldo": "Saldo de vagas", "nome": "", "foco": ""}, height=520)
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, legend_orientation="h", legend_y=-0.15)
        st.plotly_chart(fig, width="stretch")
    with col_b:
        fig = px.bar(m.sort_values("reposicao"), x="reposicao", y="nome", orientation="h",
                     color="reposicao", color_continuous_scale="RdYlGn_r", range_color=[0.85, 1.15],
                     title="Desligamentos por admissão (≥ 1 = não repõe quem sai)",
                     labels={"reposicao": "Desligamentos por admissão", "nome": ""}, height=520)
        fig.add_vline(x=1, line_dash="dash", line_color="gray")
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, width="stretch")

    st.markdown("**Salário × escolaridade por macrofamília** (tamanho = movimentações, cor = saldo)")
    fig = px.scatter(m, x="anos_estudo", y="salario_medio", size="movimentacoes", color="saldo",
                     hover_name="nome", color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
                     labels={"anos_estudo": "Anos de estudo", "salario_medio": "Salário médio (R$)",
                             "saldo": "Saldo"}, height=460)
    st.plotly_chart(fig, width="stretch")

    st.dataframe(
        m.sort_values("saldo")[["nome", "admissoes", "desligamentos", "saldo", "reposicao",
                                "pct_a_pedido", "salario_adm", "salario_desl", "anos_estudo"]],
        column_config={
            "nome": "Macrofamília", "admissoes": "Admissões", "desligamentos": "Desligamentos",
            "saldo": "Saldo",
            "reposicao": st.column_config.NumberColumn("Desl./adm.", format="%.2f"),
            "pct_a_pedido": st.column_config.NumberColumn("A pedido", format="percent"),
            "salario_adm": st.column_config.NumberColumn("Salário admissão", format="R$ %.0f"),
            "salario_desl": st.column_config.NumberColumn("Salário desligamento", format="R$ %.0f"),
            "anos_estudo": st.column_config.NumberColumn("Anos de estudo", format="%.1f"),
        }, hide_index=True, width="stretch")

st.divider()
st.caption(
    "Fonte: Novo CAGED-SC (declarações de set/2025 a ago/2026) + dados municipais (IBGE). "
    "Limites: o CAGED mede fluxo, não estoque nem vagas abertas: saldo e rotatividade são "
    "**indícios** de apagão/expansão, não prova; exclusões (EXC) não foram fornecidas; "
    "promoções internas não aparecem; classificação de CBOs por LLM validada por amostra. "
    "Detalhes em *Consulta e Exploração dos Dados*."
)
