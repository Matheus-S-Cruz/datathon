"""Raio-X do Mercado de Trabalho Industrial — Santa Catarina (Datathon CDIA 2026).

Três seções:
1. Visão geral ............ indicadores-chave e os 6 gráficos que respondem à pergunta central;
2. Exploração e consulta .. CAGED Explorer (filtros, tabelas, dicionário, bases);
3. Análises complementares  demais gráficos do projeto, contexto IBGE e validação estatística.

Execute a partir da raiz do repositório:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from dashboard.components import ui  # noqa: E402
from dashboard.services.analytics import missing_outputs  # noqa: E402
from dashboard.services.database import missing_files  # noqa: E402

st.set_page_config(page_title="Raio-X do Trabalho Industrial — SC", page_icon=":material/factory:",
                   layout="wide", initial_sidebar_state="auto")  # auto: aberto no desktop, recolhido no celular

PAGES = Path(__file__).parent / "views"  # não usar "pages/": o Streamlit a listaria sozinho


def page(file: str, title: str, icon: str, url: str | None = None, default: bool = False) -> st.Page:
    return st.Page(PAGES / file, title=title, icon=f":material/{icon}:", url_path=url, default=default)


navigation = st.navigation({
    "Visão geral": [
        page("00_painel.py", "Painel executivo", "dashboard", default=True),
    ],
    "Exploração e consulta": [
        page("02_caged_explorer.py", "Explorador do Novo CAGED", "table_view", "explorador"),
        page("03_municipalities.py", "Municípios", "location_city", "municipios"),
        page("15_tabelas.py", "Tabelas analíticas", "table_chart", "tabelas"),
        page("04_dictionary.py", "Dicionário de dados", "menu_book", "dicionario"),
        page("01_overview.py", "Bases e validação", "database", "bases"),
    ],
    "Análises complementares": [
        page("10_territorio.py", "Território", "map", "territorio"),
        page("11_setores.py", "Setores", "factory", "setores"),
        page("12_renda_escolaridade.py", "Renda e escolaridade", "school", "renda-escolaridade"),
        page("13_macrofamilias.py", "Macrofamílias de ocupações", "badge", "macrofamilias"),
        page("14_contexto_ibge.py", "Contexto regional (IBGE)", "public", "contexto-ibge"),
        page("06_statistics.py", "Exploração estatística", "scatter_plot", "estatistica"),
        page("07_relations.py", "Relações territoriais e setoriais", "hub", "relacoes"),
        page("05_audit.py", "Resultados da auditoria", "fact_check", "auditoria"),
    ],
}, expanded=True)

ASSETS = Path(__file__).parent / "assets"
st.logo(str(ASSETS / f"logo_{ui.theme_type()}.svg"), size="large", icon_image=str(ASSETS / "icon.svg"))
ui.inject_css()

missing = missing_files() + [f"outputs/{n}.parquet" for n in missing_outputs()]
if missing:
    st.error("Arquivo(s) de dados não encontrado(s):\n\n" + "\n".join(f"- `{m}`" for m in missing)
             + "\n\nVeja a seção **Dados** do README para saber onde colocar cada base.",
             icon=":material/error:")
    st.stop()

navigation.run()

with st.sidebar:
    st.divider()
    st.caption("Datathon CDIA 2026 · UniSENAI. Dados: Novo CAGED (MTE) e IBGE. "
               "Os filtros desta barra valem para a página aberta.")
