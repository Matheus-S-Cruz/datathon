"""Botão flutuante + janela de conversa do assistente (Etapa 4, interface — §3 do prompt).

Usa `st.popover` ancorado num contêiner fixo no canto inferior direito: é um painel flutuante nativo,
responsivo e acessível por teclado, sem JS frágil. A interface NÃO consulta dados: delega tudo ao
`Orchestrator`, que usa ferramentas controladas. O histórico vive só na sessão (`st.session_state`).

PRÉVIA: o "cérebro" é o provedor simulado determinístico; a janela exibe um selo "Prévia (simulação)".
"""

from __future__ import annotations

import streamlit as st

from dashboard.components import ui
from dashboard.services.assistant.orchestrator import SUGESTOES_INICIAIS, Orchestrator
from dashboard.services.assistant.response import Kind

_HIST = "assist_historico"      # lista de (papel, Resposta|str)
_PENDENTE = "assist_pendente"   # pergunta a processar no próximo rerun
_MAX_MSGS = 40                  # limite de mensagens mantidas na sessão (§11.2)
_NOME = "Assistente do Raio-X Industrial"


def _css() -> None:
    t = ui.TOKENS[ui.theme_type()]
    st.html(f"""<style>
    /* contêiner fixo do botão flutuante (canto inferior direito), acima do conteúdo */
    div.st-key-rx_assist_fab {{ position: fixed; right: 1.1rem; bottom: 1.1rem; z-index: 1000; width: auto; }}
    /* o botão que abre o popover vira um círculo com a identidade do projeto */
    div.st-key-rx_assist_fab [data-testid="stPopover"] > div > button {{
        border-radius: 999px; padding: .6rem 1rem; font-weight: 650; box-shadow: {t['shadow']};
        background: linear-gradient(120deg, {t['hero_a']}, {t['hero_b']}); color: #fff; border: none; }}
    div.st-key-rx_assist_fab [data-testid="stPopover"] > div > button:hover {{ filter: brightness(1.05); }}
    /* painel do popover: largura confortável no desktop, adapta no celular */
    div[data-testid="stPopoverBody"] {{ width: min(92vw, 420px); max-height: 70vh; }}
    .rx-assist-head {{ font-weight: 700; color: {t['ink']}; font-size: 1rem; line-height: 1.2; }}
    .rx-assist-sub {{ font-size: .76rem; color: {t['muted']}; margin-top: .1rem; }}
    .rx-assist-badge {{ display: inline-block; font-size: .66rem; font-weight: 650; padding: .06rem .45rem;
        border-radius: 999px; background: {t['chip_blue']}; color: {t['blue']}; margin-left: .4rem; vertical-align: 1px; }}
    .rx-assist-foot {{ font-size: .72rem; color: {t['muted']}; margin-top: .35rem; border-top: 1px solid {t['border']};
        padding-top: .3rem; }}
    </style>""")


def _render_resposta(r) -> None:
    """Desenha uma Resposta na bolha do assistente, com cores por tipo e rodapé de evidência."""
    icon = {Kind.DADO: ":material/insights:", Kind.CONCEITO: ":material/menu_book:",
            Kind.SEM_DADOS: ":material/help:", Kind.ESCLARECIMENTO: ":material/help:",
            Kind.ERRO: ":material/error:"}.get(r.kind, ":material/smart_toy:")
    st.markdown(r.texto)
    if r.tabela is not None and len(r.tabela):
        st.dataframe(r.tabela, hide_index=True, width="stretch")
    if r.tem_numero and r.evidencia:
        rodape = r.rodape_evidencia()
        if rodape:
            st.caption(rodape.replace("\n\n", "  ·  "))


def _processa_pendente(orch: Orchestrator, pagina_id: str) -> None:
    pergunta = st.session_state.pop(_PENDENTE, None)
    if not pergunta:
        return
    hist = st.session_state.setdefault(_HIST, [])
    hist.append(("user", pergunta))
    with st.spinner("Consultando os dados do dashboard…"):
        resposta = orch.responde(pergunta, pagina_id=pagina_id, state=st.session_state)
    hist.append(("assistant", resposta))
    del hist[: max(0, len(hist) - _MAX_MSGS)]   # mantém só as últimas mensagens


def _enviar(texto: str) -> None:
    if texto and texto.strip():
        st.session_state[_PENDENTE] = texto.strip()


def render(pagina_id: str = "") -> None:
    """Desenha o botão flutuante e a janela de conversa. Chamado uma vez por página (em app.py)."""
    _css()
    orch: Orchestrator = st.session_state.setdefault("assist_orch", Orchestrator())
    _processa_pendente(orch, pagina_id)
    hist = st.session_state.setdefault(_HIST, [])

    fab = st.container(key="rx_assist_fab")
    with fab.popover(":material/smart_toy: Assistente", use_container_width=False):
        c1, c2 = st.columns([0.74, 0.26])
        with c1:
            st.html(f'<div class="rx-assist-head">{_NOME}'
                    f'<span class="rx-assist-badge">Prévia (simulação)</span></div>'
                    '<div class="rx-assist-sub">Responde com base nos dados e na metodologia do dashboard.</div>')
        with c2:
            if st.button("Limpar", key="rx_assist_clear", use_container_width=True,
                         help="Apagar a conversa desta sessão"):
                st.session_state[_HIST] = []
                st.rerun()

        if not hist:
            st.caption("Experimente perguntar:")
            for i, s in enumerate(SUGESTOES_INICIAIS[:4]):
                st.button(s, key=f"rx_sug_{i}", use_container_width=True, on_click=_enviar, args=(s,))
        else:
            for papel, msg in hist:
                if papel == "user":
                    with st.chat_message("user"):
                        st.markdown(msg)
                else:
                    with st.chat_message("assistant"):
                        _render_resposta(msg)

        st.chat_input("Escreva sua pergunta…", key="rx_assist_input", on_submit=_enviar_do_input)
        st.html('<div class="rx-assist-foot">Prévia determinística: respostas vêm de consultas controladas '
                'aos dados reais; não há IA generativa nesta versão.</div>')


def _enviar_do_input() -> None:
    _enviar(st.session_state.get("rx_assist_input", ""))
