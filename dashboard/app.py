"""CAGED Explorer — Santa Catarina.

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

from dashboard.services.database import missing_files  # noqa: E402

st.set_page_config(page_title="CAGED Explorer — Santa Catarina", page_icon=":material/travel_explore:",
                   layout="wide", initial_sidebar_state="auto")

PAGES = Path(__file__).parent / "views"  # não usar "pages/": o Streamlit a listaria sozinho

navigation = st.navigation({
    "Bases": [
        st.Page(PAGES / "01_overview.py", title="Visão geral", icon=":material/home:", default=True),
        st.Page(PAGES / "02_caged_explorer.py", url_path="explorador", title="Explorador do Novo CAGED", icon=":material/table_view:"),
        st.Page(PAGES / "03_municipalities.py", url_path="municipios", title="Municípios", icon=":material/location_city:"),
        st.Page(PAGES / "04_dictionary.py", url_path="dicionario", title="Dicionário de dados", icon=":material/menu_book:"),
    ],
    "Validação e exploração": [
        st.Page(PAGES / "05_audit.py", url_path="auditoria", title="Resultados da auditoria", icon=":material/fact_check:"),
        st.Page(PAGES / "06_statistics.py", url_path="estatistica", title="Exploração estatística", icon=":material/scatter_plot:"),
        st.Page(PAGES / "07_relations.py", url_path="relacoes", title="Relações territoriais e setoriais", icon=":material/hub:"),
    ],
})

with st.sidebar:
    st.caption("**CAGED Explorer — Santa Catarina** · ferramenta de compreensão e validação dos dados. "
               "Não é o dashboard executivo final.")

missing = missing_files()
if missing:
    st.error("Arquivo(s) de dados não encontrado(s):\n\n" + "\n".join(f"- `{m}`" for m in missing)
             + "\n\nVeja a seção **Dados** do README para saber onde colocar cada base.",
             icon=":material/error:")
    st.stop()

navigation.run()
