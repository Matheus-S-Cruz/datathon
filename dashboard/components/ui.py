"""Elementos visuais comuns: cabeçalhos, selos de status, cartões de constatação, erros."""

from __future__ import annotations

import traceback
from collections.abc import Callable

import streamlit as st

from dashboard import formatting as fmt
from dashboard.services import profiling as P
from dashboard.services.database import DataSourceError

# natureza da informação -> (cor do selo, ícone). Cores identificam o TIPO de
# afirmação, nunca um juízo sobre o dado.
NATURE_STYLE = {
    P.VERIFIED: ("blue", ":material/verified:"),
    P.HYPOTHESIS: ("violet", ":material/help:"),
    P.LIMITATION: ("orange", ":material/block:"),
    P.EXPLORATORY: ("gray", ":material/query_stats:"),
}
STATUS_STYLE = {
    P.RESOLVED: ("green", ":material/check_circle:"),
    P.NO_ACTION: ("gray", ":material/check:"),
    P.HANDLED: ("blue", ":material/build:"),
    P.PENDING: ("orange", ":material/pending:"),
    P.EXTERNAL: ("violet", ":material/contact_support:"),
}


def page_header(title: str, subtitle: str | None = None) -> None:
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def nature_badge(nature: str) -> None:
    color, icon = NATURE_STYLE.get(nature, ("gray", ":material/info:"))
    st.badge(nature, color=color, icon=icon)


def status_badge(status: str) -> None:
    color, icon = STATUS_STYLE.get(status, ("gray", ":material/info:"))
    st.badge(f"Situação: {status}", color=color, icon=icon)


def legend() -> None:
    """Legenda dos selos usados nas páginas."""
    with st.expander("Como ler os selos", icon=":material/info:"):
        cols = st.columns(2)
        with cols[0]:
            st.markdown("**Natureza da informação**")
            for nature, text in [
                (P.VERIFIED, "número medido agora nos arquivos"),
                (P.HYPOTHESIS, "interpretação plausível, ainda não comprovada"),
                (P.LIMITATION, "característica da base que restringe a análise"),
                (P.EXPLORATORY, "descrição de distribuição, sem juízo de qualidade"),
            ]:
                nature_badge(nature)
                st.caption(text)
        with cols[1]:
            st.markdown("**Situação do problema**")
            for status in STATUS_STYLE:
                status_badge(status)


def finding_card(f: P.Finding, render_detail: Callable | None = None, expand_detail: bool = False) -> None:
    with st.container(border=True):
        head = st.columns([0.62, 0.38])
        head[0].markdown(f"#### {f.id} · {f.titulo}")
        with head[1]:
            nature_badge(f.natureza)
            status_badge(f.situacao)
        st.markdown(f"**O que foi encontrado.** {f.o_que}")
        cols = st.columns(2)
        cols[0].markdown(f"**Por que importa.** {f.porque}")
        cols[1].markdown(f"**Tratamento ou investigação recomendada.** {f.recomendacao}")
        meta = st.columns(2)
        meta[0].metric("Registros envolvidos", fmt.integer(f.registros) if f.registros is not None else "não se aplica")
        with meta[1]:
            if f.documentado:
                st.caption(f"Valor na auditoria inicial: {f.documentado}")
            if f.confere is True:
                st.badge("Reproduz a auditoria inicial", color="blue", icon=":material/done_all:")
            elif f.confere is False:
                st.badge("Diverge da auditoria inicial: investigar", color="orange", icon=":material/warning:")
            else:
                st.caption("Sem valor de referência para comparar.")
        if f.extras.get("hipotese"):
            with st.container():
                nature_badge(P.HYPOTHESIS)
                st.caption(f.extras["hipotese"])
        if render_detail:
            with st.expander("Ver dados e gráficos", icon=":material/bar_chart:", expanded=expand_detail):
                render_detail(f)
        with st.expander("Como foi calculado", icon=":material/code:"):
            st.markdown(f.como)
            if f.sql:
                st.code(_dedent(f.sql), language="sql")
            else:
                st.caption("Calculado em Python a partir dos arquivos (sem SQL).")


def _dedent(sql: str) -> str:
    lines = [l for l in sql.strip("\n").splitlines()]
    indent = min((len(l) - len(l.lstrip()) for l in lines[1:] if l.strip()), default=0)
    return "\n".join([lines[0].strip()] + [l[indent:] for l in lines[1:]])


def explain(text: str) -> None:
    """Caixa explicativa para quem não domina SQL ou estatística."""
    st.info(text, icon=":material/lightbulb:")


def active_filters(items: list[str]) -> None:
    if items:
        st.caption("Filtros ativos: " + " · ".join(items))
    else:
        st.caption("Sem filtros: todos os registros.")


def guarded(main: Callable[[], None]) -> None:
    """Executa a página mostrando erros de forma legível em vez de quebrar a aplicação."""
    try:
        main()
    except DataSourceError as exc:
        st.error(f"Não foi possível acessar os dados.\n\n{exc}", icon=":material/error:")
        st.caption("Verifique se os arquivos estão em `dataset/` (ver README).")
    except Exception as exc:  # noqa: BLE001 — erro inesperado: mostra e mantém o app vivo
        st.error(f"Erro inesperado: {exc}", icon=":material/error:")
        with st.expander("Detalhes técnicos"):
            st.code(traceback.format_exc())
