"""Leitura e limpeza da base de municípios de SC (`Municipios_SC_limpo.csv`).

Problemas conhecidos tratados aqui (todos contados e devolvidos no relatório,
nunca descartados em silêncio):
- cabeçalhos com HTML (`<span>`);
- última linha é um rodapé em HTML (notas e fontes), não um município;
- vírgula sobrando no fim das linhas gera uma coluna vazia;
- ausência representada por `-`.

A coluna "Prefeito" é descartada: dado pessoal sem uso analítico
(decisão registrada em `docs/dicionario_analitico.md`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from src.config import MUNICIPIOS_CSV

# chave interna -> início do cabeçalho original (sem HTML)
COLUMN_PREFIXES: dict[str, str] = {
    "nome": "Município",
    "codigo_ibge": "Código",
    "gentilico": "Gentílico",
    "prefeito": "Prefeito",
    "area_km2": "Área Territorial",
    "pop_censo": "População no último censo",
    "densidade": "Densidade demográfica",
    "pop_estimada": "População estimada",
    "escolarizacao": "Escolarização",
    "idhm": "IDHM",
    "mortalidade_infantil": "Mortalidade infantil",
    "receitas": "Total de receitas",
    "despesas": "Total de despesas",
    "pib_per_capita": "PIB per capita",
}

NUMERIC_KEYS = ["area_km2", "pop_censo", "densidade", "pop_estimada", "escolarizacao", "idhm",
                "mortalidade_infantil", "receitas", "despesas", "pib_per_capita"]
TEXT_KEYS = ["nome", "codigo_ibge", "gentilico"]
DROPPED_KEYS = ["prefeito"]


@dataclass
class MunicipalitiesResult:
    data: pd.DataFrame                      # 1 linha por município, numéricos convertidos
    raw: pd.DataFrame                       # texto original (somente municípios, sem prefeito)
    labels: dict[str, str]                  # chave -> cabeçalho original limpo
    footer_rows: int = 0
    empty_columns: list[str] = field(default_factory=list)
    missing_dash: dict[str, int] = field(default_factory=dict)   # valores '-'
    invalid: dict[str, int] = field(default_factory=dict)        # não numéricos (exceto '-')
    total_rows_in_file: int = 0


def clean_header(name: str) -> str:
    text = re.sub(r"<[^>]+>", " ", name)
    return re.sub(r"\s+", " ", text).strip()


def ibge_check_digit(code6: str) -> str:
    """Dígito verificador do código IBGE de município (7º dígito)."""
    total = 0
    for digit, weight in zip(code6, [1, 2, 1, 2, 1, 2]):
        product = int(digit) * weight
        total += product // 10 + product % 10
    return str((10 - total % 10) % 10)


def load_municipalities(path=MUNICIPIOS_CSV) -> MunicipalitiesResult:
    raw = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[], encoding="utf-8")
    total_rows = len(raw)
    headers = {col: clean_header(col) for col in raw.columns}

    empty_cols = [c for c in raw.columns
                  if c.startswith("Unnamed") and (raw[c].str.strip() == "").all()]

    mapping: dict[str, str] = {}
    labels: dict[str, str] = {}
    for key, prefix in COLUMN_PREFIXES.items():
        match = [c for c, h in headers.items() if h.startswith(prefix)]
        if not match:
            raise ValueError(f"Coluna esperada não encontrada no CSV de municípios: '{prefix}…'")
        mapping[match[0]] = key
        labels[key] = headers[match[0]]

    df = raw[list(mapping)].rename(columns=mapping)
    is_municipality = df["codigo_ibge"].str.strip().str.fullmatch(r"\d{7}")
    footer_rows = int((~is_municipality).sum())
    df = df[is_municipality].copy()
    for key in df.columns:
        df[key] = df[key].str.strip()

    out = df[TEXT_KEYS].copy()
    out["cod6"] = out["codigo_ibge"].str[:6]
    out["dv_valido"] = [ibge_check_digit(c[:6]) == c[6] for c in out["codigo_ibge"]]
    missing, invalid = {}, {}
    for key in NUMERIC_KEYS:
        text = df[key]
        values = pd.to_numeric(text.where(text != "-"), errors="coerce")
        missing[key] = int((text == "-").sum())
        invalid[key] = int((values.isna() & (text != "-")).sum())
        out[key] = values
    raw_view = df.drop(columns=DROPPED_KEYS)
    return MunicipalitiesResult(
        data=out.reset_index(drop=True), raw=raw_view.reset_index(drop=True), labels=labels,
        footer_rows=footer_rows, empty_columns=empty_cols, missing_dash=missing,
        invalid=invalid, total_rows_in_file=total_rows,
    )
