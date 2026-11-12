"""Visualizações Complementares — gráficos extras que não estão no painel principal.

Aprofundam os sinais de apagão/expansão: sazonalidade, motivo dos desligamentos,
diferença salarial entre quem entra e quem sai, mapa de calor macrofamília × região
e contexto socioeconômico dos municípios.
"""
import plotly.express as px
import streamlit as st

from dashboard import dados as D

D.checar_tabelas()

st.title("Visualizações complementares")
st.caption("Gráficos de apoio ao diagnóstico. Use o filtro de região na barra lateral.")

regioes = sorted(D.carregar("municipios")["mesorregiao"].unique())
with st.sidebar:
    st.header("Filtros")
    padrao = st.session_state.get("regiao_sel")
    opcoes = ["Santa Catarina (todas)"] + regioes
    escolha = st.selectbox("Região", opcoes,
                           index=opcoes.index(padrao) if padrao in opcoes else 0,
                           help="Começa com a região escolhida no mapa do painel principal.")
regiao = None if escolha.startswith("Santa Catarina") else escolha
nome = regiao or "Santa Catarina"
cubo = D.recorte(D.cubo(), regiao)

# ---------------------------------------------------------------- 1. série mensal
st.subheader(f"1. Sazonalidade: saldo mensal ({nome})")
serie = D.carregar("serie_mensal")
if regiao:
    serie = serie[serie["mesorregiao"] == regiao]
fam = st.multiselect(
    "Macrofamílias", options=list(D.NOMES_MACRO), format_func=D.NOMES_MACRO.get,
    default=[], placeholder="Todas", key="comp_fam")
if fam:
    serie = serie[serie["macrofamilia"].isin(fam)]
mes = serie.groupby("competênciamov", as_index=False)[["admissoes", "desligamentos", "saldo"]].sum()
mes["mês"] = mes["competênciamov"].str[4:] + "/" + mes["competênciamov"].str[:4]
mes["sinal"] = mes["saldo"].map(lambda v: "Positivo" if v >= 0 else "Negativo")
mes = mes.sort_values("competênciamov")
fig = px.bar(mes, x="mês", y="saldo", color="sinal",
             category_orders={"mês": mes["mês"].tolist()},  # ordem cronológica (não por cor)
             color_discrete_map={"Positivo": "#2ca02c", "Negativo": "#d62728"},
             labels={"saldo": "Saldo de vagas", "mês": "", "sinal": ""}, height=380)
st.plotly_chart(fig, width="stretch")
st.caption("Dezembro concentra desligamentos (fim de contratos e safras): comparar sempre janelas de "
           "12 meses, nunca meses isolados.")

# ------------------------------------------------- 2. motivo dos desligamentos
st.subheader(f"2. Por que as pessoas saem? ({nome})")
st.caption("**A pedido** = o trabalhador saiu (mercado aquecido, busca de salário melhor → dificuldade de "
           "reter). **Demissão** = iniciativa da empresa (retração).")
m = D.por_grupo(cubo, ["macrofamilia"])
m = m[m["macrofamilia"] != "NAO_CLASSIFICADO"]
m["nome"] = m["macrofamilia"].map(D.NOMES_MACRO)
desl = cubo[cubo["tipo"] == "DESL"].groupby("macrofamilia", as_index=False)[["n", "a_pedido", "demissao"]].sum()
desl["Outros (fim de contrato, acordo…)"] = desl["n"] - desl["a_pedido"] - desl["demissao"]
desl = desl.rename(columns={"a_pedido": "A pedido", "demissao": "Demissão"})
desl["nome"] = desl["macrofamilia"].map(D.NOMES_MACRO)
desl = desl[desl["macrofamilia"] != "NAO_CLASSIFICADO"]
longo = desl.melt(id_vars=["nome", "n"], value_vars=["A pedido", "Demissão", "Outros (fim de contrato, acordo…)"],
                  var_name="motivo", value_name="qtd")
longo["pct"] = longo["qtd"] / longo["n"]
ordem = desl.assign(p=desl["A pedido"] / desl["n"]).sort_values("p")["nome"].tolist()
fig = px.bar(longo, x="pct", y="nome", color="motivo", orientation="h",
             category_orders={"nome": ordem},
             color_discrete_map={"A pedido": "#e67e22", "Demissão": "#7f8c8d",
                                 "Outros (fim de contrato, acordo…)": "#d5dbdb"},
             labels={"pct": "Parcela dos desligamentos", "nome": "", "motivo": ""}, height=520)
fig.update_layout(xaxis_tickformat=".0%", legend_orientation="h", legend_y=-0.15)
st.plotly_chart(fig, width="stretch")

# ------------------------------------------------- 3. gap salarial adm × desl
st.subheader(f"3. Quem entra ganha mais ou menos de quem sai? ({nome})")
m["gap"] = m["salario_adm"] - m["salario_desl"]
m["gap_pct"] = m["gap"] / m["salario_desl"]
fig = px.bar(m.sort_values("gap_pct"), x="gap_pct", y="nome", orientation="h",
             color="gap_pct", color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
             custom_data=["salario_adm", "salario_desl"],
             labels={"gap_pct": "Salário de admissão vs. desligamento", "nome": ""}, height=520)
fig.update_traces(hovertemplate="<b>%{y}</b><br>Admissão: R$ %{customdata[0]:,.0f}<br>"
                                "Desligamento: R$ %{customdata[1]:,.0f}<br>Diferença: %{x:+.1%}<extra></extra>")
fig.update_layout(xaxis_tickformat="+.0%", coloraxis_showscale=False)
st.plotly_chart(fig, width="stretch")
st.caption("Quem entra costuma ganhar menos que quem sai (tem menos tempo de casa), então o normal é ficar "
           "negativo. O que importa é a **comparação entre famílias**: diferença muito negativa indica "
           "substituição por profissionais mais baratos / compressão salarial; perto de zero ou positiva indica "
           "que a empresa precisa pagar o mesmo ou mais para atrair (sinal de escassez).")

# ------------------------------------------- 4. mapa de calor macrofamília × região
st.subheader("4. Mapa de calor: macrofamília × mesorregião")
metrica = st.segmented_control(
    "Indicador", ["Desligamentos por admissão", "Saldo por 10 mil hab.", "% a pedido"],
    default="Desligamentos por admissão", key="comp_heat")
todas = D.por_grupo(D.cubo(), ["mesorregiao", "macrofamilia"])
todas = todas[todas["macrofamilia"] != "NAO_CLASSIFICADO"]
pop = D.carregar("municipios").groupby("mesorregiao")["populacao"].sum()
todas["saldo_10k"] = todas["saldo"] / todas["mesorregiao"].map(pop) * 10_000
col, escala, meio = {
    "Desligamentos por admissão": ("reposicao", "RdYlGn_r", 1.0),
    "Saldo por 10 mil hab.": ("saldo_10k", "RdYlGn", 0.0),
    "% a pedido": ("pct_a_pedido", "Oranges", None),
}[metrica or "Desligamentos por admissão"]
piv = todas.pivot(index="macrofamilia", columns="mesorregiao", values=col)
piv.index = piv.index.map(D.NOMES_MACRO)
fig = px.imshow(piv, color_continuous_scale=escala, color_continuous_midpoint=meio, aspect="auto",
                text_auto=".2f" if col != "saldo_10k" else ".1f", labels={"color": metrica}, height=560)
fig.update_xaxes(side="top", title="")
fig.update_yaxes(title="")
st.plotly_chart(fig, width="stretch")

# ---------------------------------------------- 5. contexto socioeconômico
st.subheader(f"5. Contexto dos municípios: desenvolvimento × emprego ({nome})")
mun = D.carregar("agg_municipio").merge(D.carregar("municipios")[["mun_cod", "mesorregiao"]], on="mun_cod")
if regiao:
    mun = mun[mun["mesorregiao"] == regiao]
mun = mun[mun["populacao"] >= 5_000]
eixo = st.segmented_control("Comparar saldo por 10 mil hab. com", ["PIB per capita", "IDHM (2010)"],
                            default="PIB per capita", key="comp_eixo")
x = "pib_per_capita" if (eixo or "PIB per capita") == "PIB per capita" else "idhm"
fig = px.scatter(mun, x=x, y="saldo_por_10k", size="populacao", color="mesorregiao",
                 hover_name="municipio", log_x=(x == "pib_per_capita"),
                 labels={"pib_per_capita": "PIB per capita (R$, escala log)", "idhm": "IDHM (2010)",
                         "saldo_por_10k": "Saldo por 10 mil hab.", "mesorregiao": "Mesorregião"},
                 height=500)
st.plotly_chart(fig, width="stretch")
st.caption("Municípios com 5 mil habitantes ou mais. Associação, não causalidade.")
