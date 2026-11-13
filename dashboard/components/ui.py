"""Elementos visuais comuns: cabeçalhos, selos de status, cartões de constatação, erros."""

from __future__ import annotations

import traceback
from collections.abc import Callable

import streamlit as st

from dashboard import formatting as fmt
from dashboard.services import profiling as P
from dashboard.services.analytics import MissingOutputs
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


def page_header(title: str, subtitle: str | None = None, eyebrow: str | None = None) -> None:
    header(title, subtitle, eyebrow)


def section_header(eyebrow: str, title: str, subtitle: str | None = None) -> None:
    """Cabeçalho com o nome da seção do site acima do título."""
    header(title, subtitle, eyebrow)


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
                st.badge("Diverge da auditoria inicial — investigar", color="orange", icon=":material/warning:")
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
        st.caption("Verifique se os arquivos estão em `data/raw/` e `data/reference/` (ver README).")
    except MissingOutputs as exc:
        st.error(str(exc), icon=":material/error:")
    except Exception as exc:  # noqa: BLE001 — erro inesperado: mostra e mantém o app vivo
        st.error(f"Erro inesperado: {exc}", icon=":material/error:")
        with st.expander("Detalhes técnicos"):
            st.code(traceback.format_exc())


# --------------------------------------------------------------------------- #
# Identidade visual do painel (cards, KPIs, cabeçalhos). Os tokens seguem o tema
# ativo e repetem os valores de .streamlit/config.toml.
# --------------------------------------------------------------------------- #

TOKENS = {
    "light": dict(surface="#ffffff", border="#e3e7ee", ink="#1b2433", ink2="#4a5568", muted="#6b7585",
                  shadow="0 1px 2px rgba(16,24,40,.04), 0 4px 14px rgba(16,24,40,.05)",
                  chip_blue="#e8f1fc", chip_orange="#fdeee7", chip_green="#e5f6ef", chip_violet="#eeecfb",
                  chip_amber="#fdf3dc", blue="#2a78d6", orange="#c24d1c", green="#0f7a55", violet="#5143b8",
                  amber="#8a5d00", hero_a="#5b21b6", hero_b="#a21caf"),   # marca Pulso: roxo → magenta
    "dark": dict(surface="#191d23", border="#2a3039", ink="#e6e9ef", ink2="#b4bccb", muted="#8c95a5",
                 shadow="0 1px 2px rgba(0,0,0,.35), 0 6px 16px rgba(0,0,0,.25)",
                 chip_blue="#16304f", chip_orange="#3d2216", chip_green="#123a2c", chip_violet="#28244a",
                 chip_amber="#3a2e10", blue="#6da7ec", orange="#f2a07c", green="#5fd3a5", violet="#aaa1f5",
                 amber="#f1c35e", hero_a="#3b1673", hero_b="#701a75"),
}
ACCENTS = ("blue", "orange", "green", "violet", "amber")
ICON_FONT = "'Material Symbols Rounded'"


def theme_type() -> str:
    try:
        return "dark" if st.context.theme.type == "dark" else "light"
    except Exception:  # noqa: BLE001 — fora do Streamlit
        return "light"


def inject_css() -> None:
    """CSS global: cards, KPIs, cabeçalhos e marca. Chamado uma vez em app.py."""
    t = TOKENS[theme_type()]
    st.html(f"""<style>
    /* A área principal é um "container" de CSS: as quebras abaixo dependem da largura útil
       (com ou sem menu lateral aberto), não da largura da janela. */
    /* padding-top acima da barra superior do Streamlit (60 px), para o rótulo da seção não ficar escondido */
    .block-container {{ padding-top: 4rem; padding-bottom: 3rem; max-width: 1480px;
                        container-type: inline-size; container-name: rxmain; }}
    /* Linhas de cards lado a lado empilham quando a área útil fica estreita (tablet, janela
       menor, menu aberto). Vale só para linhas que contêm cards: filtros e formulários em
       colunas continuam como estão. */
    @container rxmain (max-width: 900px) {{
        [data-testid="stHorizontalBlock"]:has(div[class*="st-key-card_"]) {{ flex-direction: column; }}
        [data-testid="stHorizontalBlock"]:has(div[class*="st-key-card_"]) > [data-testid="stColumn"] {{
            width: 100% !important; flex: 1 1 auto !important; min-width: 0; }}
    }}
    @container rxmain (max-width: 520px) {{
        div[class*="st-key-card_"] {{ padding: .85rem .8rem .45rem .8rem; }}
    }}
    /* Mapa do painel em tela estreita: o contêiner encolhe e o Plotly redesenha o mapa no espaço
       disponível (mesmos dados, escala e interação). Acima de 560 px a altura segue a da figura (420). */
    @container rxmain (max-width: 560px) {{
        div.st-key-card_map [data-testid="stPlotlyChart"] {{ height: 300px !important; }}
    }}
    /* cards: ui.card() e st.container(border=True) */
    div[class*="st-key-card_"], div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: {t['surface']}; border: 1px solid {t['border']} !important;
        border-radius: 14px !important; box-shadow: {t['shadow']};
    }}
    div[class*="st-key-card_"] {{ padding: 1.05rem 1.15rem .55rem 1.15rem; }}
    .rx-card-title {{ font-size: 1.02rem; font-weight: 650; color: {t['ink']}; line-height: 1.35; }}
    .rx-card-sub {{ font-size: .84rem; color: {t['muted']}; margin-top: .15rem; line-height: 1.45; }}
    .rx-tag {{ display: inline-block; font-size: .68rem; font-weight: 650; padding: .08rem .5rem;
               border-radius: 999px; background: {t['chip_blue']}; color: {t['blue']}; margin-left: .45rem;
               vertical-align: 2px; letter-spacing: .02em; }}
    /* cabeçalho */
    .rx-eyebrow {{ font-size: .72rem; font-weight: 650; letter-spacing: .08em; text-transform: uppercase;
                   color: {t['blue']}; }}
    .rx-subtitle {{ color: {t['ink2']}; font-size: .95rem; max-width: 980px; line-height: 1.5; }}
    h1 {{ font-size: 1.9rem !important; letter-spacing: -.01em; }}
    /* faixa da pergunta central */
    .rx-question {{ background: linear-gradient(120deg, {t['hero_a']}, {t['hero_b']}); color: #fff;
                    border-radius: 14px; padding: 1rem 1.3rem; box-shadow: {t['shadow']}; }}
    .rx-question small {{ text-transform: uppercase; letter-spacing: .08em; font-weight: 650; opacity: .85;
                          font-size: .7rem; }}
    .rx-question div {{ font-size: 1.02rem; line-height: 1.5; margin-top: .25rem; }}
    /* KPIs */
    .rx-kpis {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 14px; }}
    @container rxmain (max-width: 900px) {{ .rx-kpis {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }} }}
    @container rxmain (max-width: 560px) {{ .rx-kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
                                            .rx-kpis .rx-kpi-value {{ font-size: 1.45rem; }}
                                            .rx-kpis .rx-kpi:last-child:nth-child(odd) {{ grid-column: 1 / -1; }} }}
    /* logo maior no topo do menu */
    [data-testid="stSidebarHeader"] img, [data-testid="stLogo"] {{ height: 2.6rem !important; max-width: 100%; }}
    .rx-kpi {{ background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 14px;
               box-shadow: {t['shadow']}; padding: .9rem 1rem .85rem 1.15rem; position: relative;
               overflow: hidden; }}
    .rx-kpi::before {{ content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
                       background: var(--accent); }}
    .rx-kpi-top {{ display: flex; align-items: center; gap: .55rem; }}
    .rx-kpi-icon {{ width: 30px; height: 30px; border-radius: 8px; display: grid; place-items: center;
                    background: var(--chip); color: var(--accent); font-family: {ICON_FONT};
                    font-size: 18px; line-height: 1; flex: none; }}
    .rx-kpi-label {{ font-size: .8rem; color: {t['ink2']}; font-weight: 550; line-height: 1.25; }}
    .rx-kpi-value {{ font-size: 1.75rem; font-weight: 700; color: {t['ink']}; margin-top: .5rem;
                     line-height: 1.1; letter-spacing: -.01em; white-space: nowrap; }}
    .rx-kpi-note {{ font-size: .76rem; color: {t['muted']}; margin-top: .35rem; line-height: 1.4; }}
    /* título de seção dentro da página */
    .rx-section {{ display: flex; align-items: baseline; gap: .7rem; flex-wrap: wrap;
                   margin-top: .9rem; border-bottom: 1px solid {t['border']}; padding-bottom: .35rem; }}
    .rx-section b {{ font-size: 1.08rem; font-weight: 650; color: {t['ink']}; }}
    .rx-section span {{ font-size: .84rem; color: {t['muted']}; }}
    .rx-section .rx-step {{ font-size: .72rem; font-weight: 650; letter-spacing: .08em; text-transform: uppercase;
                            color: {t['blue']}; }}
    /* selo de escopo dos cards: diz se o card segue o recorte ou mostra o estado inteiro */
    .rx-scope {{ display: inline-flex; align-items: center; gap: .25rem; font-size: .68rem; font-weight: 600;
                 padding: .08rem .5rem .08rem .4rem; border-radius: 999px; margin-left: .45rem; vertical-align: 2px;
                 border: 1px solid {t['border']}; color: {t['ink2']}; white-space: nowrap; }}
    .rx-scope i {{ font-family: {ICON_FONT}; font-style: normal; font-size: 13px; line-height: 1; }}
    .rx-scope.recorte {{ background: {t['chip_blue']}; border-color: transparent; color: {t['blue']}; }}
    /* barra de recorte (filtros ativos) */
    .rx-scopebar {{ display: flex; flex-wrap: wrap; align-items: center; gap: .4rem; font-size: .82rem;
                    color: {t['muted']}; }}
    .rx-chip {{ display: inline-flex; align-items: center; gap: .3rem; padding: .18rem .65rem; border-radius: 999px;
                background: {t['chip_blue']}; color: {t['blue']}; font-weight: 600; font-size: .78rem; }}
    .rx-chip.neutral {{ background: {t['surface']}; color: {t['ink2']}; border: 1px solid {t['border']}; }}
    .rx-chip i {{ font-family: {ICON_FONT}; font-style: normal; font-size: 14px; line-height: 1; }}
    /* ajuda dos KPIs: elemento details nativo, funciona com toque e teclado.
       Atenção: não escrever tags HTML (sinal de menor) dentro deste CSS; o sanitizador do
       st.html descarta o bloco de estilo inteiro. */
    .rx-kpi {{ display: flex; flex-direction: column; }}
    .rx-kpi-help {{ margin-top: auto; padding-top: .45rem; font-size: .76rem; color: {t['ink2']}; }}
    .rx-kpi-help summary {{ cursor: pointer; list-style: none; display: inline-flex; align-items: center; gap: .25rem;
                            color: {t['muted']}; font-weight: 550; border-radius: 6px; }}
    .rx-kpi-help summary::-webkit-details-marker {{ display: none; }}
    .rx-kpi-help summary i {{ font-family: {ICON_FONT}; font-style: normal; font-size: 15px; line-height: 1; }}
    .rx-kpi-help summary:hover, .rx-kpi-help summary:focus-visible {{ color: {t['blue']}; outline: none; }}
    .rx-kpi-help[open] summary {{ color: {t['blue']}; }}
    .rx-kpi-help div {{ margin-top: .3rem; line-height: 1.45; }}
    /* leituras (resposta em 3 cards) */
    .rx-read {{ display: flex; flex-direction: column; gap: .5rem; }}
    .rx-read ul {{ margin: 0; padding-left: 1.05rem; display: flex; flex-direction: column; gap: .35rem;
                   font-size: .9rem; line-height: 1.5; color: {t['ink']}; }}
    .rx-read a {{ font-size: .8rem; font-weight: 600; color: {t['blue']}; text-decoration: none; }}
    .rx-read a:hover, .rx-read a:focus-visible {{ text-decoration: underline; }}
    </style>""")


def header(title: str, subtitle: str | None = None, eyebrow: str | None = None) -> None:
    """Cabeçalho de página: rótulo da seção, título (st.title) e subtítulo."""
    if eyebrow:
        st.html(f'<div class="rx-eyebrow">{eyebrow}</div>')
    st.title(title, anchor=False)
    if subtitle:
        st.html(f'<div class="rx-subtitle">{subtitle}</div>')


def question_banner() -> None:
    st.html('<div class="rx-question"><small>Pergunta central de negócio</small><div>'
            'Quais regiões e setores industriais de Santa Catarina estão enfrentando <b>apagão de mão de '
            'obra</b> ou <b>expansão acelerada</b>, e como os indicadores de <b>renda e escolaridade</b> '
            'explicam esses gargalos?</div></div>')


def kpi_row(items: list[dict]) -> None:
    """Indicadores-chave. Cada item: label, value, note, icon (Material Symbol), accent, help.
    O acento identifica o indicador (não é juízo de bom/ruim)."""
    t = TOKENS[theme_type()]
    cards = []
    for i, it in enumerate(items):
        acc = it.get("accent") or ACCENTS[i % len(ACCENTS)]
        note = f'<div class="rx-kpi-note">{it["note"]}</div>' if it.get("note") else ""
        tip = (it.get("help") or "").replace('"', "&quot;")
        # Ajuda visível com clique, toque ou teclado (o title continua para quem usa o mouse).
        helper = (f'<details class="rx-kpi-help"><summary><i>info</i>O que é</summary><div>{it["help"]}</div>'
                  '</details>') if it.get("help") else ""
        cards.append(
            f'<div class="rx-kpi" style="--accent:{t[acc]};--chip:{t["chip_" + acc]}" title="{tip}">'
            f'<div class="rx-kpi-top"><div class="rx-kpi-icon">{it.get("icon", "monitoring")}</div>'
            f'<div class="rx-kpi-label">{it["label"]}</div></div>'
            f'<div class="rx-kpi-value">{it["value"]}</div>{note}{helper}</div>')
    st.html(f'<div class="rx-kpis">{"".join(cards)}</div>')


def section(title: str, hint: str | None = None, *, anchor: str | None = None, step: str | None = None) -> None:
    """Título de seção. `anchor` cria um destino para links internos (#anchor); `step` é o rótulo
    curto acima do título (ex.: "Evidência 1")."""
    span = f"<span>{hint}</span>" if hint else ""
    ident = f' id="{anchor}"' if anchor else ""
    lead = f'<span class="rx-step">{step}</span>' if step else ""
    st.html(f'<div class="rx-section"{ident}>{lead}<b>{title}</b>{span}</div>')


SCOPES = {
    "recorte": ("filter_alt", "Segue o recorte", "Este card usa os filtros da barra lateral."),
    "estado": ("public", "Estado inteiro", "Este card mostra Santa Catarina inteira e não muda com os filtros."),
}


def card(title: str | None = None, subtitle: str | None = None, *, key: str, tag: str | None = None,
         scope: str | None = None):
    """Card com título descritivo e leitura. Uso: `with ui.card("Título", "Como ler", key="x"): ...`.
    `scope`: "recorte" (segue os filtros) ou "estado" (Santa Catarina inteira) — exibido como selo."""
    box = st.container(key=f"card_{key}")
    if title:
        tg = f'<span class="rx-tag">{tag}</span>' if tag else ""
        sc = ""
        if scope:
            icon, label, tip = SCOPES[scope]
            sc = f'<span class="rx-scope {scope}" title="{tip}"><i>{icon}</i>{label}</span>'
        sub = f'<div class="rx-card-sub">{subtitle}</div>' if subtitle else ""
        box.html(f'<div class="rx-card-title">{title}{sc}{tg}</div>{sub}')
    return box


def scope_bar(items: list[str]) -> None:
    """Filtros ativos como chips. Sem filtros, diz explicitamente que o recorte é o estado inteiro."""
    if items:
        chips = "".join(f'<span class="rx-chip"><i>filter_alt</i>{x}</span>' for x in items)
        st.html(f'<div class="rx-scopebar">Recorte aplicado: {chips}'
                '<span>· mude na barra lateral</span></div>')
    else:
        st.html('<div class="rx-scopebar">Recorte: <span class="rx-chip neutral"><i>public</i>Santa Catarina '
                'inteira, todos os setores</span><span>· filtre na barra lateral</span></div>')


def reading_card(title: str, items: list[str], link: str, link_label: str, *, key: str, scope: str = "estado",
                 note: str | None = None):
    """Card de leitura: frases calculadas (markdown), ressalva opcional e link para o gráfico que as sustenta."""
    with card(title, key=key, scope=scope):
        st.markdown("\n".join(f"- {i}" for i in items))
        if note:
            st.caption(note)
        st.html(f'<div class="rx-read"><a href="#{link}">{link_label} ↓</a></div>')
