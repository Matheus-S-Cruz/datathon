"""Conexão DuckDB e execução de consultas.

Arquitetura (por que assim):
- O Parquet do CAGED (3,4 milhões de linhas) NÃO é carregado em memória.
  A view `caged_raw` aponta para o arquivo; cada consulta lê só as colunas e
  as linhas de que precisa (projeção de colunas + filtros no SQL).
- A view `caged` acrescenta colunas convertidas (salário como DECIMAL, códigos
  com zero à esquerda etc.) sem materializar nada.
- `municipios` e `rotulos` (códigos do dicionário) são tabelas pequenas,
  materializadas uma vez.
- Uma única conexão por versão dos arquivos; cada consulta usa um cursor
  próprio, o que torna o uso seguro entre sessões simultâneas do Streamlit.
- `data_signature()` (data de modificação + tamanho dos arquivos) entra na
  chave de cache: se uma base for substituída, tudo é recalculado.
"""

from __future__ import annotations

import threading
from functools import lru_cache
from pathlib import Path

import duckdb
import pandas as pd

from dashboard.services.catalog import typed_view_sql
from dashboard.services.dictionary import code_labels, load_sheets
from dashboard.services.municipalities import load_municipalities
from src.config import CAGED_PARQUET, DICIONARIO_XLSX, MUNICIPIOS_CSV

DATA_FILES: dict[str, Path] = {
    "Novo CAGED (Parquet)": CAGED_PARQUET,
    "Municípios de SC (CSV)": MUNICIPIOS_CSV,
    "Dicionário de dados (Excel)": DICIONARIO_XLSX,
}

_lock = threading.Lock()


class DataSourceError(RuntimeError):
    """Erro de acesso a uma base, com mensagem pronta para a interface."""


def data_signature() -> tuple:
    sig = []
    for path in DATA_FILES.values():
        try:
            st = path.stat()
            sig.append((str(path), st.st_mtime_ns, st.st_size))
        except FileNotFoundError:
            sig.append((str(path), None, None))
    return tuple(sig)


def missing_files() -> list[str]:
    return [f"{name}: {path}" for name, path in DATA_FILES.items() if not path.exists()]


def _sql_path(path: Path) -> str:
    return path.as_posix().replace("'", "''")


@lru_cache(maxsize=1)
def _connection(signature: tuple) -> duckdb.DuckDBPyConnection:
    missing = missing_files()
    if missing:
        raise DataSourceError("Arquivo(s) de dados não encontrado(s):\n- " + "\n- ".join(missing))
    con = duckdb.connect(":memory:")
    con.execute(f"""
        CREATE VIEW caged_raw AS
        SELECT file_row_number + 1 AS linha, * EXCLUDE (file_row_number)
        FROM read_parquet('{_sql_path(CAGED_PARQUET)}', file_row_number = true)
    """)
    con.execute(typed_view_sql("caged_raw"))

    mun = load_municipalities().data
    con.execute("CREATE TABLE municipios AS SELECT * FROM mun")

    labels = code_labels(load_sheets())
    con.execute("CREATE TABLE rotulos AS SELECT * FROM labels")
    return con


def get_connection() -> duckdb.DuckDBPyConnection:
    with _lock:
        return _connection(data_signature())


def query(sql: str, params: list | tuple | None = None) -> pd.DataFrame:
    """Executa SQL parametrizado e devolve um DataFrame (use só para resultados pequenos)."""
    cur = get_connection().cursor()
    try:
        return cur.execute(sql, list(params or [])).df()
    except duckdb.Error as exc:
        raise DataSourceError(f"Falha na consulta ao DuckDB: {exc}") from exc
    finally:
        cur.close()


def scalar(sql: str, params: list | tuple | None = None):
    cur = get_connection().cursor()
    try:
        row = cur.execute(sql, list(params or [])).fetchone()
        return row[0] if row else None
    except duckdb.Error as exc:
        raise DataSourceError(f"Falha na consulta ao DuckDB: {exc}") from exc
    finally:
        cur.close()
