"""Tabelas com formatação brasileira e exportação de tabelas pequenas (agregadas)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard import formatting as fmt


def styled(df: pd.DataFrame, *, money=(), ints=(), pct=(), dec: dict | None = None, comp=(),
           corr=()):
    """Styler com números no padrão brasileiro. Os valores originais continuam numéricos,
    então a ordenação ao clicar no cabeçalho segue o número, não o texto."""
    formats = {}
    for c in money:
        formats[c] = fmt.brl
    for c in ints:
        formats[c] = fmt.integer
    for c in pct:
        formats[c] = fmt.pct
    for c, d in (dec or {}).items():
        formats[c] = lambda v, d=d: fmt.num(v, d)
    for c in comp:
        formats[c] = fmt.competencia
    for c in corr:
        formats[c] = fmt.corr
    formats = {k: v for k, v in formats.items() if k in df.columns}
    return df.style.format(formats, na_rep="—")


def show(df: pd.DataFrame, *, height: int | str = "auto", rename: dict | None = None,
         key: str | None = None, selectable: bool = False, **fmt_kwargs):
    """Mostra uma tabela formatada. Com `selectable=True`, devolve o evento de seleção de linha."""
    view = df.rename(columns=rename or {})
    mapped = {k: [(rename or {}).get(c, c) for c in v] if isinstance(v, (list, tuple)) else v
              for k, v in fmt_kwargs.items()}
    if "dec" in mapped and mapped["dec"]:
        mapped["dec"] = {(rename or {}).get(c, c): d for c, d in fmt_kwargs["dec"].items()}
    data = styled(view, **mapped) if len(view) * max(len(view.columns), 1) <= 200_000 else view
    kwargs = dict(width="stretch", hide_index=True, height=height, key=key)
    if selectable:
        return st.dataframe(data, on_select="rerun", selection_mode="single-row", **kwargs)
    st.dataframe(data, **kwargs)
    return None


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """CSV para Excel em português: separador ';', decimal ',', UTF-8 com BOM."""
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


def download(df: pd.DataFrame, filename: str, label: str = "Baixar tabela (CSV)", key: str | None = None):
    st.download_button(label, to_csv_bytes(df), file_name=filename, mime="text/csv",
                       icon=":material/download:", key=key)


def data_view(df: pd.DataFrame, filename: str, *, key: str, rename: dict | None = None,
              notes: list[str] | None = None, **fmt_kwargs) -> None:
    """Expansor "Ver dados" de um gráfico: as mesmas linhas e colunas usadas para desenhá-lo,
    com os nomes de coluna trazendo a unidade, e o CSV com exatamente essas linhas e valores.

    `notes`: linhas de metodologia (período, abrangência, fórmula, limites) mostradas acima da tabela.
    O CSV usa os valores numéricos sem arredondar, com separador ';' e decimal ','.
    """
    with st.expander("Ver dados e método", icon=":material/table_chart:"):
        for line in notes or []:
            st.caption(line)
        show(df, rename=rename, key=f"{key}_table", height=min(38 * len(df) + 40, 420), **fmt_kwargs)
        download(df.rename(columns=rename or {}), filename, key=f"{key}_csv")
