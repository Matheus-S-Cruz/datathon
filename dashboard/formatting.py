"""Formatação no padrão brasileiro (milhar com ponto, decimal com vírgula, R$, dd/mm/aaaa).

Funções puras, usadas tanto pelos serviços (textos das constatações) quanto pela interface.
"""

from __future__ import annotations

import math
from datetime import datetime

import pandas as pd

MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _missing(value) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _swap(text: str) -> str:
    return text.replace(",", "\0").replace(".", ",").replace("\0", ".")


def num(value, decimals: int = 0) -> str:
    if _missing(value):
        return "-"
    return _swap(f"{float(value):,.{decimals}f}")


def integer(value) -> str:
    if _missing(value):
        return "-"
    return _swap(f"{int(round(float(value))):,}")


def signed(value) -> str:
    if _missing(value):
        return "-"
    return _swap(f"{int(round(float(value))):+,}").replace("-", "−")


def brl(value, decimals: int = 2) -> str:
    if _missing(value):
        return "-"
    return "R$ " + num(value, decimals)


def pct(fraction, decimals: int = 1) -> str:
    """Recebe fração (0,25) e devolve '25,0%'."""
    if _missing(fraction) or (isinstance(fraction, float) and math.isinf(fraction)):
        return "-"
    return num(float(fraction) * 100, decimals) + "%"


def corr(value) -> str:
    return "-" if _missing(value) else num(value, 3)


def competencia(value) -> str:
    """'202509' -> 'set/2025'."""
    text = str(value or "")
    if len(text) == 6 and text.isdigit() and 1 <= int(text[4:]) <= 12:
        return f"{MONTHS[int(text[4:]) - 1]}/{text[:4]}"
    return text


def date_time(value) -> str:
    if _missing(value):
        return "-"
    if not isinstance(value, datetime):
        value = pd.Timestamp(value)
    return value.strftime("%d/%m/%Y %H:%M")


def megabytes(value) -> str:
    """Tamanho em MB; abaixo de 1 MB, mostra em KB."""
    if _missing(value):
        return "-"
    return num(value * 1024, 0) + " KB" if value < 1 else num(value, 1) + " MB"
