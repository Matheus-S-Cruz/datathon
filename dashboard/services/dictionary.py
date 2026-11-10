"""Leitura do dicionário de dados oficial (`Dicionario_de_dados.xlsx`).

- Aba `Layout`: variáveis do Novo CAGED (nome, descrição, formato).
- Demais abas: tabelas de códigos (Código, Descrição).

Os códigos são normalizados como texto com zeros à esquerda quando a coluna
correspondente do CAGED exige (subclasse 7, CBO 6, município 6 dígitos), para
que a comparação com a base seja feita no mesmo formato.
"""

from __future__ import annotations

import openpyxl
import pandas as pd

from dashboard.services.catalog import CAGED_COLUMNS
from src.config import DICIONARIO_XLSX

NO_DESCRIPTION = "(sem descrição no dicionário)"


def _cell_to_text(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    return text or None


def load_sheets(path=DICIONARIO_XLSX) -> dict[str, pd.DataFrame]:
    """Todas as abas como DataFrames de texto, com cabeçalho detectado e linhas vazias removidas."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheets: dict[str, pd.DataFrame] = {}
    try:
        for ws in wb.worksheets:
            rows = [[_cell_to_text(v) for v in r] for r in ws.iter_rows(values_only=True)]
            rows = [r for r in rows if any(v is not None for v in r)]
            if not rows:
                sheets[ws.title] = pd.DataFrame()
                continue
            header_idx = next((i for i, r in enumerate(rows)
                               if r and r[0] in ("Código", "Variável")), 0)
            header = [h if h else f"coluna_{i + 1}" for i, h in enumerate(rows[header_idx])]
            body = [r[: len(header)] + [None] * (len(header) - len(r)) for r in rows[header_idx + 1:]]
            df = pd.DataFrame(body, columns=header)
            df = df.dropna(axis=1, how="all")
            sheets[ws.title] = df
    finally:
        wb.close()
    return sheets


def layout_table(sheets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = sheets["Layout"].copy()
    df.columns = ["variavel", "descricao", "formato"][: len(df.columns)]
    return df


def code_labels(sheets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Tabela longa (variavel, codigo, descricao) com códigos normalizados."""
    pads = {c.sheet: c.pad for c in CAGED_COLUMNS if c.sheet}
    frames = []
    for name, df in sheets.items():
        if name == "Layout" or df.empty or "Código" not in df.columns:
            continue
        part = pd.DataFrame({"variavel": name, "codigo": df["Código"],
                             "descricao": df.get("Descrição")}).dropna(subset=["codigo"])
        pad = pads.get(name)
        if pad:
            part["codigo"] = part["codigo"].str.zfill(pad)
        frames.append(part)
    return pd.concat(frames, ignore_index=True)


def search(sheets: dict[str, pd.DataFrame], term: str) -> pd.DataFrame:
    """Procura um termo (código ou texto) em todas as abas."""
    term = term.strip().lower()
    hits = []
    for name, df in sheets.items():
        if df.empty:
            continue
        mask = df.apply(lambda col: col.fillna("").str.lower().str.contains(term, regex=False))
        found = df[mask.any(axis=1)]
        for _, row in found.iterrows():
            values = [v for v in row.tolist() if v is not None]
            hits.append({"aba": name, "código/variável": values[0] if values else "",
                         "descrição": values[1] if len(values) > 1 else NO_DESCRIPTION})
    return pd.DataFrame(hits, columns=["aba", "código/variável", "descrição"])
