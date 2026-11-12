"""Raio-X do Mercado de Trabalho — Santa Catarina (Datathon CDIA 2026).

Execute a partir da raiz do repositório:
    streamlit run dashboard/app.py

Navegação em três seções:
- Visualizações Essenciais ........ painel principal (mapa 3D + KPIs + abas de storytelling)
- Consulta e Exploração dos Dados . CAGED Explorer: bases, dicionário, auditoria e estatística
- Visualizações Complementares .... gráficos de apoio ao diagnóstico
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from dashboard.services.database import missing_files  # noqa: E402

st.set_page_config(page_title="Raio-X do Trabalho | SC", page_icon=":material/insights:",
                   layout="wide", initial_sidebar_state="auto")

AQUI = Path(__file__).resolve().parent
PAGINAS = AQUI / "paginas"
VIEWS = AQUI / "views"  # páginas do CAGED Explorer (não usar "pages/": o Streamlit a listaria sozinho)

navegacao = st.navigation({
    "Visualizações Essenciais": [
        st.Page(PAGINAS / "painel_principal.py", title="Painel principal",
                icon=":material/dashboard:", default=True),
    ],
    "Consulta e Exploração dos Dados": [
        st.Page(VIEWS / "01_overview.py", url_path="visao-geral", title="Visão geral das bases", icon=":material/home:"),
        st.Page(VIEWS / "02_caged_explorer.py", url_path="explorador", title="Explorador do Novo CAGED", icon=":material/table_view:"),
        st.Page(VIEWS / "03_municipalities.py", url_path="municipios", title="Municípios", icon=":material/location_city:"),
        st.Page(VIEWS / "04_dictionary.py", url_path="dicionario", title="Dicionário de dados", icon=":material/menu_book:"),
        st.Page(VIEWS / "05_audit.py", url_path="auditoria", title="Resultados da auditoria", icon=":material/fact_check:"),
        st.Page(VIEWS / "06_statistics.py", url_path="estatistica", title="Exploração estatística", icon=":material/scatter_plot:"),
        st.Page(VIEWS / "07_relations.py", url_path="relacoes", title="Relações territoriais e setoriais", icon=":material/hub:"),
    ],
    "Visualizações Complementares": [
        st.Page(PAGINAS / "complementares.py", url_path="complementares", title="Gráficos complementares",
                icon=":material/bar_chart:"),
    ],
})

faltando = missing_files()
if faltando:
    st.error("Arquivo(s) de dados não encontrado(s):\n\n" + "\n".join(f"- `{m}`" for m in faltando)
             + "\n\nVeja a seção **Dados** do README.", icon=":material/error:")
    st.stop()

navegacao.run()
