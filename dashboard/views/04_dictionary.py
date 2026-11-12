"""Página 4 — Dicionário de dados: abas do Excel, pesquisa e correspondência com as colunas."""

import pandas as pd
import streamlit as st

from dashboard.components import tables, ui
from dashboard.services import queries as Q
from dashboard.services.catalog import CAGED_COLUMNS
from dashboard.services.database import data_signature
from dashboard.services.dictionary import NO_DESCRIPTION, layout_table, load_sheets, search
from dashboard.services.municipalities import NUMERIC_KEYS, TEXT_KEYS, load_municipalities


@st.cache_data(show_spinner=False)
def _sheets(signature) -> dict[str, pd.DataFrame]:
    return load_sheets()


def field_table(sheets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Campo | Tipo identificado | Descrição | Base | Utilização — uma linha por campo das duas bases
    e por variável do dicionário que não existe no CAGED."""
    lay = layout_table(sheets)
    desc = dict(zip(lay["variavel"], lay["descricao"]))
    fmt_code = dict(zip(lay["variavel"], lay["formato"]))
    stored = Q.run("SELECT column_name, column_type FROM (DESCRIBE caged_raw)")
    stored = dict(zip(stored["column_name"], stored["column_type"]))
    rows = []
    for c in CAGED_COLUMNS:
        rows.append({
            "Campo": c.name,
            "Tipo identificado": f"{c.kind} (armazenado como {stored.get(c.name, '?')})",
            "Descrição": desc.get(c.name, NO_DESCRIPTION),
            "Formato no dicionário": fmt_code.get(c.name, "-"),
            "Aba de códigos": c.sheet or "-",
            "Base": "Novo CAGED",
            "Utilização": c.usage,
        })
    caged_names = {c.name for c in CAGED_COLUMNS}
    for var in lay["variavel"]:
        if var not in caged_names:
            rows.append({"Campo": var, "Tipo identificado": "- (campo ausente na base)",
                         "Descrição": desc.get(var, NO_DESCRIPTION), "Formato no dicionário": fmt_code.get(var, "-"),
                         "Aba de códigos": var if var in sheets else "-",
                         "Base": "Somente no dicionário",
                         "Utilização": "Não utilizável: a coluna não existe no Parquet (ver auditoria, A9)."})
    mun = load_municipalities()
    for k in TEXT_KEYS + NUMERIC_KEYS:
        rows.append({"Campo": mun.labels[k],
                     "Tipo identificado": "numérico (decimal com ponto; '-' = ausente)" if k in NUMERIC_KEYS else "texto",
                     "Descrição": "Não disponível no dicionário (o dicionário cobre só o CAGED). "
                                  "O rótulo e o rodapé do CSV indicam a fonte.",
                     "Formato no dicionário": "-", "Aba de códigos": "-", "Base": "Municípios de SC",
                     "Utilização": {"codigo_ibge": "Chave: 6 primeiros dígitos = município do CAGED.",
                                    "pop_estimada": "Denominador candidato para taxas por 10 mil habitantes.",
                                    "pib_per_capita": "Contexto econômico.",
                                    "idhm": "Contexto de desenvolvimento (dado de 2010).",
                                    "mortalidade_infantil": "Evitar: muitos ausentes.",
                                    "nome": "Rótulo do município."}.get(k, "Contexto (uso opcional).")})
    return pd.DataFrame(rows)


def main() -> None:
    ui.page_header("Dicionário de dados", "Arquivo oficial `Dicionario_de_dados.xlsx` (layout do Novo CAGED).")
    sheets = _sheets(data_signature())
    st.caption(f"{len(sheets)} abas: `Layout` (variáveis) + {len(sheets) - 1} tabelas de códigos.")

    tab_fields, tab_sheet, tab_search, tab_cov = st.tabs(
        ["Campos e utilização", "Consultar uma aba", "Pesquisar códigos e descrições", "Cobertura dos códigos"])

    with tab_fields:
        ui.explain("Descrições copiadas da aba `Layout` do dicionário. “Utilização” resume as decisões da equipe "
                   "registradas em `docs/dicionario_analitico.md`. Quando o dicionário não descreve o campo, "
                   "isso é dito explicitamente: nenhum significado foi inventado.")
        ft = field_table(sheets)
        base = st.multiselect("Base", sorted(ft["Base"].unique()), key="dic_base", placeholder="Todas")
        term = st.text_input("Filtrar campos por nome ou descrição", key="dic_fterm")
        view = ft[ft["Base"].isin(base)] if base else ft
        if term.strip():
            t = term.strip().lower()
            view = view[view["Campo"].str.lower().str.contains(t, regex=False)
                        | view["Descrição"].str.lower().str.contains(t, regex=False)]
        st.dataframe(view, hide_index=True, width="stretch", height=640,
                     column_config={"Descrição": st.column_config.TextColumn(width="large"),
                                    "Utilização": st.column_config.TextColumn(width="large")})
        tables.download(view, "dicionario_campos.csv", key="dic_dl_fields")

    with tab_sheet:
        names = list(sheets)
        sheet = st.selectbox("Aba", names, key="dic_sheet",
                             format_func=lambda n: f"{n} ({len(sheets[n])} linhas)")
        df = sheets[sheet]
        col = next((c for c in CAGED_COLUMNS if c.sheet == sheet), None)
        if sheet == "Layout":
            st.caption("Lista das variáveis do Novo CAGED: nome, descrição e formato.")
        elif col:
            used = Q.distinct_values(col.typed)
            df = df.copy()
            codes = df["Código"].str.zfill(col.pad) if col.pad else df["Código"]
            counts = dict(zip(used["valor"], used["n"]))
            df["registros no CAGED"] = codes.map(counts).fillna(0).astype(int)
            st.caption(f"Corresponde à coluna `{col.name}` do CAGED. {int((df['registros no CAGED'] > 0).sum())} de "
                       f"{len(df)} códigos aparecem na base.")
        else:
            st.caption("Esta aba não corresponde a nenhuma coluna existente no CAGED.")
        t = st.text_input("Filtrar esta aba", key=f"dic_t_{sheet}")
        if t.strip():
            mask = df.astype(str).apply(lambda s: s.str.lower().str.contains(t.strip().lower(), regex=False))
            df = df[mask.any(axis=1)]
        st.dataframe(df, hide_index=True, width="stretch", height=560)

    with tab_search:
        term = st.text_input("Código ou palavra (procura em todas as abas)", key="dic_term",
                             placeholder="ex.: 715505, soldador, 40, aprendiz")
        if term.strip():
            hits = search(sheets, term)
            st.caption(f"{len(hits)} resultado(s).")
            st.dataframe(hits, hide_index=True, width="stretch", height=520)
        else:
            st.caption("Digite um termo para pesquisar.")

    with tab_cov:
        st.markdown("Códigos que aparecem no CAGED mas **não** constam da aba correspondente do dicionário. "
                    "Esses registros são exibidos como *(sem descrição no dicionário)*.")
        tables.show(Q.dictionary_coverage(), ints=["códigos fora do dicionário", "registros afetados"])
        st.caption("Comparação feita com os códigos normalizados (zeros à esquerda restaurados: subclasse 7, CBO 6, "
                   "município 6 dígitos).")


ui.guarded(main)
