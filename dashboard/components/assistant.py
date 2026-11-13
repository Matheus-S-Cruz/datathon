"""Botão flutuante + janela de conversa do assistente (Etapa 4, interface — §3 do prompt).

Usa `st.popover` ancorado num contêiner fixo no canto inferior direito: é um painel flutuante nativo,
responsivo e acessível por teclado, sem JS frágil. A interface NÃO consulta dados: delega tudo ao
`Orchestrator`, que usa ferramentas controladas. O histórico vive só na sessão (`st.session_state`).

PRÉVIA: o "cérebro" é o provedor simulado determinístico; a janela exibe um selo "Prévia (simulação)".
"""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st

from dashboard.components import ui
from dashboard.services.assistant.orchestrator import SUGESTOES_INICIAIS, Orchestrator
from dashboard.services.assistant.response import Kind

_HIST = "assist_historico"      # lista de (papel, Resposta|str)
_PENDENTE = "assist_pendente"   # pergunta a processar no próximo rerun
_MAX_MSGS = 40                  # limite de mensagens mantidas na sessão (§11.2)
_NOME = "Assistente Pulso"
_MARCA = "Pulso Industry"
# Avatar circular do assistente: a marca Pulso Industry (coração + pulso + barras de dados) em disco escuro.
AVATAR = Path(__file__).resolve().parents[1] / "assets" / "assistant_avatar.svg"


@lru_cache(maxsize=1)
def _avatar_uri() -> str:
    """Avatar como data URI (base64): usado no cabeçalho, no botão flutuante e no indicador de carregamento."""
    return "data:image/svg+xml;base64," + base64.b64encode(AVATAR.read_bytes()).decode("ascii")


def _avatar_img(size: int, cls: str = "rx-assist-avatar") -> str:
    return f'<img class="{cls}" src="{_avatar_uri()}" width="{size}" height="{size}" alt="{_NOME}">'


def _css() -> None:
    t = ui.TOKENS[ui.theme_type()]
    st.html(f"""<style>
    /* contêiner fixo do botão flutuante (canto inferior direito), acima do conteúdo */
    div.st-key-rx_assist_fab {{ position: fixed; right: 1.1rem; bottom: 1.1rem; z-index: 1000; width: auto; }}
    /* o botão que abre o popover vira uma pílula com a identidade Pulso Industry e o avatar à esquerda */
    div.st-key-rx_assist_fab [data-testid="stPopover"] > div > button {{
        border-radius: 999px; padding: .45rem 1rem .45rem .45rem; font-weight: 650; box-shadow: {t['shadow']};
        background: linear-gradient(120deg, {t['hero_a']}, {t['hero_b']}); color: #fff; border: none; }}
    div.st-key-rx_assist_fab [data-testid="stPopover"] > div > button::before {{
        content: ""; flex: none; width: 28px; height: 28px; margin-right: .5rem; border-radius: 50%;
        background: url("{_avatar_uri()}") center / contain no-repeat;
        box-shadow: 0 0 0 2px rgba(255,255,255,.35); }}
    div.st-key-rx_assist_fab [data-testid="stPopover"] > div > button:hover {{ filter: brightness(1.05); }}
    /* avatar: sempre círculo perfeito, sem esticar */
    .rx-assist-avatar {{ width: 34px; height: 34px; border-radius: 50%; object-fit: contain; flex: none; }}
    .rx-assist-id {{ display: flex; align-items: center; gap: .6rem; }}
    [data-testid="stChatMessageAvatarCustom"] img, [data-testid="stChatMessage"] img[alt="assistant avatar"] {{
        border-radius: 50%; object-fit: contain; }}
    /* estado de processamento: o avatar "pulsa" de leve enquanto a resposta é calculada */
    .rx-assist-thinking {{ display: flex; align-items: center; gap: .55rem; font-size: .85rem; color: {t['muted']};
        padding: .35rem 0; }}
    .rx-assist-thinking img {{ width: 28px; height: 28px; border-radius: 50%; animation: rxpulse 1.2s ease-in-out infinite; }}
    @keyframes rxpulse {{ 0%, 100% {{ transform: scale(1); opacity: 1; }} 50% {{ transform: scale(1.08); opacity: .75; }} }}
    @media (prefers-reduced-motion: reduce) {{ .rx-assist-thinking img {{ animation: none; }} }}
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
    # Indicador de carregamento com a identidade do assistente (substitui o spinner genérico).
    aguarde = st.empty()
    aguarde.html(f'<div class="rx-assist-thinking">{_avatar_img(28, "")}'
                 '<span>Consultando os dados do dashboard…</span></div>')
    try:
        resposta = orch.responde(pergunta, pagina_id=pagina_id, state=st.session_state)
    finally:
        aguarde.empty()
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
    with fab.popover("Assistente Pulso", use_container_width=False):
        c1, c2 = st.columns([0.74, 0.26])
        with c1:
            st.html(f'<div class="rx-assist-id">{_avatar_img(34)}<div>'
                    f'<div class="rx-assist-head">{_NOME}'
                    f'<span class="rx-assist-badge">Prévia (simulação)</span></div>'
                    f'<div class="rx-assist-sub">{_MARCA} · responde com base nos dados e na metodologia '
                    'do dashboard.</div></div></div>')
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
                    with st.chat_message("assistant", avatar=str(AVATAR)):
                        _render_resposta(msg)

        st.chat_input("Escreva sua pergunta…", key="rx_assist_input", on_submit=_enviar_do_input)
        st.html('<div class="rx-assist-foot">Prévia determinística: respostas vêm de consultas controladas '
                'aos dados reais; não há IA generativa nesta versão.</div>')


def _enviar_do_input() -> None:
    _enviar(st.session_state.get("rx_assist_input", ""))
