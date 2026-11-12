"""Página 5 — Resultados da auditoria, recalculados a partir dos arquivos."""

import pandas as pd
import streamlit as st

from dashboard import formatting as fmt
from dashboard.components import charts, tables, ui
from dashboard.services import profiling as P
from dashboard.services import queries as Q
from dashboard.services.database import data_signature


@st.cache_data(show_spinner=False)
def _findings(signature) -> list[P.Finding]:
    return P.all_findings()


# ----------------------------------------------------------------- detalhes por constatação


def _table(f: P.Finding, **kw):
    if f.detalhe is not None:
        tables.show(f.detalhe, **kw)


def _flow_detail(f: P.Finding, dim: str, top: int = 20):
    df = f.detalhe.head(top).copy()
    label = f"{dim}_descricao"
    df["rotulo"] = df[dim].astype(str) + " · " + df[label].astype(str) if label in df else df[dim]
    charts.show(charts.ranked_bars(df, "rotulo", "movimentacoes", f"{top} maiores por movimentações",
                                   "Movimentações (admissões + desligamentos)"), key=f"aud_{f.id}")
    full = f.detalhe
    cols = [c for c in [dim, label, "admissoes", "desligamentos", "saldo", "movimentacoes"] if c in full]
    tables.show(full[cols], ints=["admissoes", "desligamentos", "saldo", "movimentacoes"], height=360)
    tables.download(full[cols], f"auditoria_{f.id}.csv", key=f"aud_dl_{f.id}")


def _competencia_detail(f: P.Finding):
    for df, dim, name in [(f.detalhe, "competencia_dec", "declaração"), (f.extras["mov"], "competencia_mov", "movimentação")]:
        d = df.copy()
        d["mes"] = d[dim].map(fmt.competencia)
        charts.show(charts.flow_bars(d, "mes", f"Por competência da {name}"), key=f"aud_B2_{dim}")


def _education_detail(f: P.Finding):
    df = f.detalhe.copy()
    df["rotulo"] = df["escolaridade"] + " · " + df["escolaridade_descricao"]
    charts.show(charts.flow_bars(df, "rotulo", "Admissões e desligamentos por grau de instrução (ordem ordinal)"),
                key="aud_B6")
    tables.show(df[["escolaridade", "escolaridade_descricao", "admissoes", "desligamentos", "saldo", "movimentacoes"]],
                ints=["admissoes", "desligamentos", "saldo", "movimentacoes"])


def _salary_hist(f: P.Finding):
    st.caption("Histograma calculado no DuckDB sobre todos os registros (sem amostragem).")
    c = st.columns(3)
    hi = c[0].number_input("Mostrar até (R$)", 1000, 100000, 10000, step=1000, key="aud_hist_hi")
    zero = c[1].toggle("Excluir salários zerados", value=True, key="aud_hist_zero")
    split = c[2].toggle("Separar admissões e desligamentos", value=False, key="aud_hist_split")
    groups = [("Admissão", "Admissões"), ("Desligamento", "Desligamentos")] if split else [(None, "Todos")]
    for mov, name in groups:
        fl = Q.Filters(excluir_salario_zero=zero, movimento=mov)
        bins, inside, outside = Q.histogram("salario", fl, 0, float(hi), 50)
        charts.show(charts.histogram(bins, f"Distribuição salarial: {name}", "Salário (R$)", money=True),
                    key=f"aud_hist_{name}")
        st.caption(f"{fmt.integer(inside)} registros no intervalo; {fmt.integer(outside)} acima de {fmt.brl(hi, 0)} "
                   "não aparecem no gráfico.")


DETAILS = {
    "A1": lambda f: _table(f, ints=["nulos", "vazios"], pct=["% do total"], height=360),
    "A2": lambda f: _table(f, ints=["valores que não converteram"]),
    "A5": lambda f: _table(f, ints=["n"]),
    "A8": lambda f: _table(f, ints=["n", "ignorado"], comp=["competencia_dec"]),
    "B2": _competencia_detail,
    "B3": lambda f: _flow_detail(f, "municipio"),
    "B4": lambda f: _flow_detail(f, "secao", 22),
    "B5": lambda f: _flow_detail(f, "cbo"),
    "B6": _education_detail,
    "C2": _salary_hist,
    "C4": lambda f: _table(f, ints=["n", "zeros"], money=["mediana"]),
    "C5": lambda f: _table(f, ints=["n"], money=["mediana", "q1", "q3", "media"]),
    "D3": lambda f: _table(f, ints=["códigos fora do dicionário", "registros afetados"]),
}
EXPANDED = {"B2", "B3", "B6", "C2"}


def main() -> None:
    ui.page_header("Resultados da auditoria",
                   "Cada constatação é recalculada agora a partir dos arquivos e comparada com o valor publicado em "
                   "docs/diagnostico_inicial.md.")
    with st.spinner("Recalculando as constatações (a primeira vez leva cerca de 30 segundos)…"):
        findings = _findings(data_signature())

    ok = sum(1 for f in findings if f.confere is True)
    bad = [f.id for f in findings if f.confere is False]
    ref = sum(1 for f in findings if f.confere is not None)
    c = st.columns(4)
    c[0].metric("Constatações", len(findings))
    c[1].metric("Reproduzem a auditoria inicial", f"{ok} de {ref}")
    c[2].metric("Divergem", len(bad), help=", ".join(bad) or "nenhuma")
    c[3].metric("Pendentes ou com validação externa",
                sum(1 for f in findings if f.situacao in (P.PENDING, P.EXTERNAL)))
    if bad:
        st.warning("Divergências em relação à auditoria inicial: " + ", ".join(bad), icon=":material/warning:")

    ui.legend()
    ui.explain("**Constatação ≠ hipótese.** Exemplo: existirem linhas idênticas é um fato medido; dizer que são "
               "duplicidades indevidas seria uma hipótese, e o CAGED não tem identificador para comprová-la.")

    c = st.columns(2)
    natures = c[0].multiselect("Natureza", list(ui.NATURE_STYLE), key="aud_nat", placeholder="Todas")
    statuses = c[1].multiselect("Situação", list(ui.STATUS_STYLE), key="aud_sit", placeholder="Todas")
    selected = [f for f in findings if (not natures or f.natureza in natures)
                and (not statuses or f.situacao in statuses)]

    with st.expander("Resumo em tabela", icon=":material/table:"):
        summary = pd.DataFrame([{"id": f.id, "categoria": f.categoria, "constatação": f.titulo,
                                 "natureza": f.natureza, "situação": f.situacao, "registros": f.registros,
                                 "reproduz a auditoria": {True: "sim", False: "NÃO", None: "-"}[f.confere]}
                                for f in selected])
        tables.show(summary, ints=["registros"])
        tables.download(summary, "auditoria_resumo.csv", key="aud_dl_summary")

    tabs = st.tabs(P.CATEGORIES)
    for tab, category in zip(tabs, P.CATEGORIES):
        with tab:
            items = [f for f in selected if f.categoria == category]
            if not items:
                st.caption("Nenhuma constatação com os filtros escolhidos.")
            for f in items:
                ui.finding_card(f, DETAILS.get(f.id), expand_detail=f.id in EXPANDED)


ui.guarded(main)
