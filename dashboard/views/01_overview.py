"""Página 1 — Visão geral: projeto, bases, volumes e situação da validação."""

import streamlit as st

from dashboard import formatting as fmt
from dashboard.components import charts, tables, ui
from dashboard.services import profiling as P
from dashboard.services import queries as Q


def main() -> None:
    ui.page_header("CAGED Explorer — Santa Catarina",
                   "Datathon CDIA 2026 · UniSENAI — Raio-X do Mercado de Trabalho e Vagas Industriais em SC")

    st.markdown(
        "> **Pergunta central de negócio**  \n"
        "> “Quais regiões e setores industriais de Santa Catarina estão enfrentando apagão de mão de obra "
        "ou expansão acelerada, e como os indicadores de renda e escolaridade explicam esses gargalos?”")
    st.markdown(
        "**Objetivo desta aplicação:** permitir que toda a equipe veja, consulte e confira as bases "
        "**antes** da modelagem. Aqui não há índice de escassez nem classificação de municípios — só "
        "dados, descrições e verificações reproduzíveis.")

    with st.spinner("Consultando as bases…"):
        k = Q.overview_kpis()

    st.subheader("Movimentações no período")
    c = st.columns(3)
    c[0].metric("Admissões", fmt.integer(k["admissoes"]), help="Registros com saldomovimentação = +1.")
    c[1].metric("Desligamentos", fmt.integer(k["desligamentos"]), help="Registros com saldomovimentação = −1.")
    c[2].metric("Saldo", fmt.signed(k["saldo"]), help="Admissões − desligamentos (soma do saldo).")
    c = st.columns(3)
    c[0].metric("Municípios com movimentação", fmt.integer(k["municipios"]),
                help=f"A base municipal tem {k['municipios_base']} municípios.")
    c[1].metric("Setores", fmt.integer(k["secoes"]) + " seções",
                help=f"{fmt.integer(k['subclasses'])} subclasses CNAE distintas.")
    c[2].metric("Ocupações (CBO)", fmt.integer(k["ocupacoes"]))

    ui.explain("O Novo CAGED registra **fluxos** (cada admissão e cada desligamento com carteira assinada). "
               "Ele não mede quantas pessoas estão empregadas (estoque) nem quantas vagas estão abertas.")

    st.subheader("Admissões e desligamentos por mês")
    col = st.segmented_control("Mês considerado", ["Declaração", "Movimentação"], default="Declaração",
                               key="ov_period") or "Declaração"
    dim = "competencia_mov" if col == "Movimentação" else "competencia_dec"
    flow = Q.flow_by(dim)
    flow["mes"] = flow[dim].map(fmt.competencia)
    charts.show(charts.flow_bars(flow, "mes", f"Por mês ({col.lower()})"))
    charts.show(charts.balance_bars(flow, "mes", "Saldo mensal (admissões − desligamentos)"))
    with st.expander("Ver tabela"):
        tables.show(flow[["mes", "admissoes", "desligamentos", "saldo", "movimentacoes"]],
                    rename={"mes": "Mês", "admissoes": "Admissões", "desligamentos": "Desligamentos",
                            "saldo": "Saldo", "movimentacoes": "Movimentações"},
                    ints=["admissoes", "desligamentos", "saldo", "movimentacoes"])
    if dim == "competencia_mov":
        st.caption("Meses anteriores a set/2025 aparecem porque há declarações fora do prazo "
                   "referentes a movimentações antigas.")

    st.subheader("Bases de dados")
    c = st.columns(4)
    c[0].metric("Registros do CAGED", fmt.integer(k["registros"]))
    c[1].metric("Colunas do CAGED", k["colunas_arquivo"])
    c[2].metric("Período (declaração)", f"{k['dec_meses']} meses",
                help=f"Por movimentação: {fmt.competencia(k['mov_min'])} a {fmt.competencia(k['mov_max'])}.")
    c[2].caption(f"{fmt.competencia(k['dec_min'])} a {fmt.competencia(k['dec_max'])}")
    c[3].metric("Municípios na base municipal", k["municipios_base"])

    info = P.file_info()
    info["modificado_em"] = info["modificado_em"].map(fmt.date_time)
    info["tamanho_mb"] = info["tamanho_mb"].map(fmt.megabytes)
    st.dataframe(info.rename(columns={"base": "Base", "arquivo": "Arquivo", "tamanho_mb": "Tamanho",
                                      "modificado_em": "Última atualização do arquivo"}),
                 hide_index=True, width="stretch")
    st.caption("Fontes: Novo CAGED (microdados de movimentações, MTE), fornecido pela organização do Datathon; "
               "indicadores municipais (IBGE, PNUD, DATASUS, Siconfi — ver rodapé do CSV); dicionário oficial "
               "do Novo CAGED.")

    st.subheader("Situação da validação das bases")
    checks = P.validation_checks()
    ok = int(checks["aprovada"].sum())
    if ok == len(checks):
        st.success(f"{ok} de {len(checks)} checagens aprovadas agora, a partir dos arquivos.",
                   icon=":material/verified:")
    else:
        st.warning(f"{ok} de {len(checks)} checagens aprovadas. Veja as reprovadas abaixo.",
                   icon=":material/warning:")
    checks["aprovada"] = checks["aprovada"].map({True: "✔ aprovada", False: "✖ reprovada"})
    st.dataframe(checks.rename(columns={"checagem": "Checagem", "aprovada": "Situação", "resultado": "Resultado"}),
                 hide_index=True, width="stretch")
    st.caption("Detalhes de cada constatação na página **Resultados da auditoria**.")


ui.guarded(main)
