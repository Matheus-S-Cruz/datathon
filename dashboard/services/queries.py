"""Consultas SQL reutilizadas pelas páginas.

Regras seguidas em todo o módulo:
- valores do usuário entram sempre como parâmetros (`?`), nunca concatenados;
- nomes de colunas só entram no SQL se estiverem no catálogo (lista branca);
- resultados recorrentes ficam em cache (`run`), com chave que inclui a versão
  dos arquivos de dados;
- estatísticas de salário usam o valor DECIMAL e excluem NULLs explicitamente.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import streamlit as st

from dashboard import formatting as fmt
from dashboard.services import database
from dashboard.services.catalog import BY_NAME, CAGED_COLUMNS, EDUCATION_ORDER, MONEY, q
from dashboard.services.dictionary import NO_DESCRIPTION

# --------------------------------------------------------------------------- cache


@st.cache_data(show_spinner=False, max_entries=1024)
def _cached(sql: str, params: tuple, signature: tuple) -> pd.DataFrame:
    return database.query(sql, list(params))


def run(sql: str, params: list | tuple = ()) -> pd.DataFrame:
    """Consulta com cache. Use para tudo que não seja exportação."""
    return _cached(sql, tuple(params), database.data_signature())


# ------------------------------------------------------------------------- filtros


@dataclass(frozen=True)
class Filters:
    municipios: tuple[str, ...] = ()
    periodo_coluna: str = "competencia_dec"        # ou "competencia_mov"
    competencia_inicio: str | None = None
    competencia_fim: str | None = None
    secoes: tuple[str, ...] = ()
    divisoes: tuple[str, ...] = ()
    subclasses: tuple[str, ...] = ()
    cbos: tuple[str, ...] = ()
    escolaridades: tuple[str, ...] = ()
    movimento: str | None = None                   # "Admissão" | "Desligamento" | None
    tipos_mov: tuple[str, ...] = ()
    salario_min: float | None = None
    salario_max: float | None = None
    excluir_salario_zero: bool = False
    somente_unidade_mes: bool = False
    valores_coluna: tuple[tuple[str, tuple[str, ...]], ...] = ()   # (coluna original, valores)
    texto: str | None = None
    texto_coluna: str | None = None               # coluna original ou None = todas
    texto_modo: str = "contém"                    # contém | igual | começa com

    def active(self) -> list[str]:
        """Descrição curta dos filtros ativos (para mostrar à usuária)."""
        out = []
        if self.municipios:
            out.append(f"{len(self.municipios)} município(s)")
        if self.competencia_inicio or self.competencia_fim:
            out.append(f"período {self.competencia_inicio or '…'}–{self.competencia_fim or '…'}")
        for label, values in [("seção", self.secoes), ("divisão", self.divisoes),
                              ("subclasse", self.subclasses), ("CBO", self.cbos),
                              ("escolaridade", self.escolaridades), ("tipo mov.", self.tipos_mov)]:
            if values:
                out.append(f"{label}: {len(values)}")
        if self.movimento:
            out.append(self.movimento)
        if self.salario_min is not None or self.salario_max is not None:
            out.append("faixa salarial")
        if self.excluir_salario_zero:
            out.append("sem salário zero")
        if self.somente_unidade_mes:
            out.append("unidade Mês")
        for col, vals in self.valores_coluna:
            out.append(f"{col}: {len(vals)} valor(es)")
        if self.texto:
            out.append(f"texto “{self.texto}”")
        return out


PERIOD_COLUMNS = ("competencia_dec", "competencia_mov")
TEXT_MODES = ("contém", "igual", "começa com")


def _in(column: str, values, clauses: list, params: list) -> None:
    values = list(values)
    if values:
        clauses.append(f"{column} IN ({', '.join('?' for _ in values)})")
        params.extend(values)


def build_where(f: Filters) -> tuple[str, list]:
    """Converte os filtros em uma cláusula WHERE parametrizada sobre a view `caged`."""
    clauses: list[str] = []
    params: list = []
    _in("municipio", f.municipios, clauses, params)
    period = f.periodo_coluna if f.periodo_coluna in PERIOD_COLUMNS else "competencia_dec"
    if f.competencia_inicio:
        clauses.append(f"{period} >= ?")
        params.append(f.competencia_inicio)
    if f.competencia_fim:
        clauses.append(f"{period} <= ?")
        params.append(f.competencia_fim)
    _in("secao", f.secoes, clauses, params)
    _in("divisao_cnae", f.divisoes, clauses, params)
    _in("subclasse7", f.subclasses, clauses, params)
    _in("cbo", f.cbos, clauses, params)
    _in("escolaridade", f.escolaridades, clauses, params)
    _in("tipo_mov", f.tipos_mov, clauses, params)
    if f.movimento in ("Admissão", "Desligamento"):
        clauses.append("movimento = ?")
        params.append(f.movimento)
    if f.salario_min is not None:
        clauses.append("salario >= ?")
        params.append(f.salario_min)
    if f.salario_max is not None:
        clauses.append("salario <= ?")
        params.append(f.salario_max)
    if f.excluir_salario_zero:
        clauses.append("salario > 0")
    if f.somente_unidade_mes:
        clauses.append("unidade_salario = '5'")
    for col, values in f.valores_coluna:
        if col in BY_NAME:
            _in(q(col), values, clauses, params)
    if f.texto:
        term = f.texto.strip().lower()
        if f.texto_coluna in BY_NAME:
            target = f"lower(CAST({q(f.texto_coluna)} AS VARCHAR))"
        else:
            target = "lower(concat_ws(' | ', " + ", ".join(q(c.name) for c in CAGED_COLUMNS) + "))"
        if f.texto_modo == "igual":
            clauses.append(f"{target} = ?")
        elif f.texto_modo == "começa com":
            clauses.append(f"starts_with({target}, ?)")
        else:
            clauses.append(f"contains({target}, ?)")
        params.append(term)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def and_where(where: str, condition: str) -> str:
    return f"{where} AND {condition}" if where else f"WHERE {condition}"


# ------------------------------------------------------------------------- rótulos


@st.cache_data(show_spinner=False)
def _labels(signature: tuple) -> dict[str, dict[str, str]]:
    df = database.query("SELECT variavel, codigo, descricao FROM rotulos")
    out: dict[str, dict[str, str]] = {}
    for var, code, desc in df.itertuples(index=False):
        out.setdefault(var, {})[code] = desc if isinstance(desc, str) else NO_DESCRIPTION
    mun = database.query("SELECT cod6, nome FROM municipios")
    out["__municipio_nome"] = dict(zip(mun["cod6"], mun["nome"]))
    return out


def labels_for(sheet: str) -> dict[str, str]:
    return _labels(database.data_signature()).get(sheet, {})


def municipality_names() -> dict[str, str]:
    return _labels(database.data_signature())["__municipio_nome"]


def describe(sheet: str | None, code) -> str:
    if sheet is None or code is None or (isinstance(code, float) and pd.isna(code)):
        return ""
    return labels_for(sheet).get(str(code), NO_DESCRIPTION)


competencia_label = fmt.competencia   # '202509' -> 'set/2025'


# ----------------------------------------------------------------- dimensões (pág. 6/7)

SALARY_BANDS = [
    ("0 (zerado)", "salario = 0"),
    ("até R$ 1.500", "salario > 0 AND salario <= 1500"),
    ("R$ 1.500 a 2.000", "salario > 1500 AND salario <= 2000"),
    ("R$ 2.000 a 3.000", "salario > 2000 AND salario <= 3000"),
    ("R$ 3.000 a 5.000", "salario > 3000 AND salario <= 5000"),
    ("R$ 5.000 a 10.000", "salario > 5000 AND salario <= 10000"),
    ("acima de R$ 10.000", "salario > 10000"),
]
SALARY_BAND_SQL = ("CASE " + " ".join(f"WHEN {cond} THEN '{label}'" for label, cond in SALARY_BANDS)
                   + " ELSE 'sem valor válido' END")


@dataclass(frozen=True)
class Dimension:
    key: str
    label: str
    expr: str
    sheet: str | None = None   # aba do dicionário para descrever o código


DIMENSIONS: dict[str, Dimension] = {d.key: d for d in [
    Dimension("municipio", "Município", "municipio", "município"),
    Dimension("secao", "Seção CNAE", "secao", "seção"),
    Dimension("divisao_cnae", "Divisão CNAE (2 dígitos)", "divisao_cnae"),
    Dimension("subclasse7", "Subclasse CNAE", "subclasse7", "subclasse"),
    Dimension("cbo", "Ocupação (CBO 2002)", "cbo", "cbo2002ocupação"),
    Dimension("grande_grupo_cbo", "Grande grupo CBO (1º dígito)", "grande_grupo_cbo"),
    Dimension("escolaridade", "Grau de instrução", "escolaridade", "graudeinstrução"),
    Dimension("faixa_salarial", "Faixa salarial", SALARY_BAND_SQL),
    Dimension("competencia_dec", "Competência da declaração", "competencia_dec"),
    Dimension("competencia_mov", "Competência da movimentação", "competencia_mov"),
    Dimension("movimento", "Admissão/desligamento", "movimento"),
    Dimension("tipo_mov", "Tipo de movimentação", "tipo_mov", "tipomovimentação"),
    Dimension("categoria_cod", "Categoria do trabalhador", "categoria_cod", "categoria"),
    Dimension("sexo_cod", "Sexo", "sexo_cod", "sexo"),
]}


def add_labels(df: pd.DataFrame, dim_key: str, column: str | None = None) -> pd.DataFrame:
    """Acrescenta a coluna '<dim> (descrição)' a partir do dicionário/base municipal."""
    column = column or dim_key
    dim = DIMENSIONS[dim_key]
    if dim_key == "municipio":
        names = municipality_names()
        df[f"{column}_descricao"] = df[column].map(lambda c: names.get(c, NO_DESCRIPTION))
    elif dim_key.startswith("competencia"):
        df[f"{column}_descricao"] = df[column].map(competencia_label)
    elif dim.sheet:
        df[f"{column}_descricao"] = df[column].map(lambda c: describe(dim.sheet, c))
    return df


def sort_dimension(df: pd.DataFrame, dim_key: str, column: str | None = None) -> pd.DataFrame:
    column = column or dim_key
    if dim_key == "escolaridade":
        order = {c: i for i, c in enumerate(EDUCATION_ORDER)}
        return df.sort_values(column, key=lambda s: s.map(lambda v: order.get(v, 99)))
    if dim_key == "faixa_salarial":
        order = {label: i for i, (label, _) in enumerate(SALARY_BANDS)}
        return df.sort_values(column, key=lambda s: s.map(lambda v: order.get(v, 99)))
    return df.sort_values(column)


# ------------------------------------------------------------------ visão geral


def overview_kpis() -> dict:
    df = run("""
        SELECT count(*) AS registros,
               count(*) FILTER (WHERE saldo = 1) AS admissoes,
               count(*) FILTER (WHERE saldo = -1) AS desligamentos,
               count(*) FILTER (WHERE saldo IS NULL OR saldo NOT IN (1, -1)) AS saldo_invalido,
               sum(saldo) AS saldo,
               count(DISTINCT municipio) AS municipios,
               count(DISTINCT secao) AS secoes,
               count(DISTINCT subclasse7) AS subclasses,
               count(DISTINCT cbo) AS ocupacoes,
               min(competencia_dec) AS dec_min, max(competencia_dec) AS dec_max,
               count(DISTINCT competencia_dec) AS dec_meses,
               min(competencia_mov) AS mov_min, max(competencia_mov) AS mov_max
        FROM caged
    """)
    out = df.iloc[0].to_dict()
    out["colunas"] = len(CAGED_COLUMNS)
    out["colunas_arquivo"] = int(run("SELECT count(*) AS n FROM (DESCRIBE caged_raw)")["n"].iloc[0]) - 1
    out["municipios_base"] = int(run("SELECT count(*) AS n FROM municipios")["n"].iloc[0])
    return out


def flow_by(dim_key: str, f: Filters | None = None) -> pd.DataFrame:
    """Admissões, desligamentos e saldo por uma dimensão."""
    dim = DIMENSIONS[dim_key]
    where, params = build_where(f or Filters())
    df = run(f"""
        SELECT {dim.expr} AS {dim_key},
               count(*) FILTER (WHERE saldo = 1) AS admissoes,
               count(*) FILTER (WHERE saldo = -1) AS desligamentos,
               sum(saldo) AS saldo, count(*) AS movimentacoes
        FROM caged {where} GROUP BY 1
    """, params)
    return add_labels(sort_dimension(df, dim_key), dim_key)


def distinct_values(column_expr: str, limit: int = 5000) -> pd.DataFrame:
    """Valores distintos e frequência de uma coluna (para montar filtros)."""
    return run(f"SELECT {column_expr} AS valor, count(*) AS n FROM caged GROUP BY 1 "
               f"ORDER BY n DESC LIMIT {int(limit)}")


def count_distinct(column_expr: str) -> int:
    return int(run(f"SELECT count(DISTINCT {column_expr}) AS n FROM caged")["n"].iloc[0])


# ------------------------------------------------------------------- explorador

# Ordenação numérica para colunas armazenadas como texto
NUMERIC_SORT = {c.name: c.typed for c in CAGED_COLUMNS if c.quantitative or c.kind == "índice técnico"}


def explorer_count(f: Filters) -> int:
    where, params = build_where(f)
    return int(run(f"SELECT count(*) AS n FROM caged {where}", params)["n"].iloc[0])


def _raw_select(columns: list[str]) -> str:
    cols = [c for c in columns if c in BY_NAME] or [c.name for c in CAGED_COLUMNS]
    return "linha, " + ", ".join(q(c) for c in cols)


def explorer_page(f: Filters, columns: list[str], order_by: str, descending: bool,
                  page_size: int, page: int) -> pd.DataFrame:
    where, params = build_where(f)
    if order_by in BY_NAME:
        sort = NUMERIC_SORT.get(order_by, q(order_by))
    else:
        sort = "linha"
    direction = "DESC" if descending else "ASC"
    offset = max(page - 1, 0) * page_size
    return run(f"""
        SELECT {_raw_select(columns)} FROM caged {where}
        ORDER BY {sort} {direction} NULLS LAST, linha
        LIMIT {int(page_size)} OFFSET {int(offset)}
    """, params)


def explorer_sample(f: Filters, columns: list[str], n: int, method: str, seed: int) -> pd.DataFrame:
    """Amostra dos registros filtrados: 'primeiros' (ordem do arquivo) ou 'aleatória'."""
    where, params = build_where(f)
    if method == "aleatória":
        # Ordenação por hash(linha + semente): reprodutível para a mesma semente,
        # independente do número de threads, e cobre o arquivo inteiro.
        return run(f"""
            SELECT {_raw_select(columns)} FROM caged {where}
            ORDER BY hash(linha + ?) LIMIT {int(n)}
        """, [*params, int(seed)])
    return run(f"SELECT {_raw_select(columns)} FROM caged {where} ORDER BY linha LIMIT {int(n)}", params)


def record(linha: int) -> pd.DataFrame:
    """Registro completo (todas as colunas originais e convertidas) de uma linha do arquivo."""
    return run("SELECT * FROM caged WHERE linha = ?", [int(linha)])


EXPORT_MAX_ROWS = 500_000


def export_csv(f: Filters, columns: list[str], order_by: str, descending: bool,
               max_rows: int = EXPORT_MAX_ROWS) -> tuple[bytes, int]:
    """CSV (separador ';', UTF-8 com BOM para o Excel) com os valores ORIGINAIS dos registros filtrados.

    Não usa cache e não passa por pandas: o DuckDB entrega Arrow, gravado direto em CSV.
    """
    where, params = build_where(f)
    sort = NUMERIC_SORT.get(order_by, q(order_by)) if order_by in BY_NAME else "linha"
    direction = "DESC" if descending else "ASC"
    sql = (f"SELECT {_raw_select(columns)} FROM caged {where} "
           f"ORDER BY {sort} {direction} NULLS LAST, linha LIMIT {int(max_rows)}")
    cur = database.get_connection().cursor()
    try:
        rel = cur.sql(sql, params=params)
        # DuckDB >= 2.0: to_arrow_table(); versões 1.x: arrow()
        fetch = getattr(rel, "to_arrow_table", None) or rel.arrow
        table: pa.Table = fetch()
    finally:
        cur.close()
    buf = io.BytesIO()
    buf.write("﻿".encode("utf-8"))
    pacsv.write_csv(table, buf, write_options=pacsv.WriteOptions(delimiter=";"))
    return buf.getvalue(), table.num_rows


# ------------------------------------------------------------------- estatística

RECORD_VARIABLES = {c.typed: c.label for c in CAGED_COLUMNS if c.quantitative}


def numeric_summary(expr: str, f: Filters, extra: str | None = None) -> dict:
    """Estatísticas descritivas calculadas no DuckDB sobre todos os registros filtrados."""
    where, params = build_where(f)
    if extra:
        where = and_where(where, extra)
    df = run(f"""
        WITH b AS (SELECT CAST({expr} AS DOUBLE) AS x FROM caged {where})
        SELECT count(*) AS total, count(x) AS n, avg(x) AS media, median(x) AS mediana,
               mode(x) AS moda, stddev_samp(x) AS desvio_padrao, min(x) AS minimo,
               quantile_cont(x, 0.25) AS q1, quantile_cont(x, 0.75) AS q3, max(x) AS maximo
        FROM b
    """, params)
    return df.iloc[0].to_dict()


def correlation(x: str, y: str, f: Filters, extra: str | None = None) -> dict:
    """Pearson (linear) e Spearman (postos médios, robusto a extremos) no DuckDB."""
    where, params = build_where(f)
    cond = f"{x} IS NOT NULL AND {y} IS NOT NULL" + (f" AND {extra}" if extra else "")
    where = and_where(where, cond)
    df = run(f"""
        WITH b AS (SELECT CAST({x} AS DOUBLE) AS x, CAST({y} AS DOUBLE) AS y FROM caged {where}),
        r AS (
          SELECT x, y,
                 rank() OVER (ORDER BY x) + (count(*) OVER (PARTITION BY x) - 1) / 2.0 AS rx,
                 rank() OVER (ORDER BY y) + (count(*) OVER (PARTITION BY y) - 1) / 2.0 AS ry
          FROM b)
        SELECT count(*) AS n, corr(x, y) AS pearson, corr(rx, ry) AS spearman FROM r
    """, params)
    return df.iloc[0].to_dict()


def scatter_sample(x: str, y: str, f: Filters, n: int = 5000, seed: int = 42,
                   extra: str | None = None, color_dim: str | None = None) -> pd.DataFrame:
    where, params = build_where(f)
    cond = f"{x} IS NOT NULL AND {y} IS NOT NULL" + (f" AND {extra}" if extra else "")
    where = and_where(where, cond)
    color = f", {DIMENSIONS[color_dim].expr} AS grupo" if color_dim else ""
    return run(f"""
        SELECT linha, CAST({x} AS DOUBLE) AS x, CAST({y} AS DOUBLE) AS y {color}
        FROM caged {where} ORDER BY hash(linha + ?) LIMIT {int(n)}
    """, [*params, int(seed)])


def histogram(expr: str, f: Filters, lo: float, hi: float, bins: int = 40,
              extra: str | None = None) -> tuple[pd.DataFrame, int, int]:
    """Histograma agregado no SQL. Devolve (barras, n dentro do intervalo, n fora)."""
    where, params = build_where(f)
    cond = f"{expr} IS NOT NULL" + (f" AND {extra}" if extra else "")
    where = and_where(where, cond)
    width = (hi - lo) / bins if hi > lo else 1.0
    df = run(f"""
        WITH b AS (SELECT CAST({expr} AS DOUBLE) AS x FROM caged {where})
        SELECT least(floor((x - ?) / ?), ? - 1)::INT AS bin, count(*) AS n
        FROM b WHERE x >= ? AND x <= ? GROUP BY 1 ORDER BY 1
    """, [*params, lo, width, bins, lo, hi])
    df["inicio"] = lo + df["bin"] * width
    df["fim"] = df["inicio"] + width
    outside = run(f"""
        SELECT count(*) AS n FROM (SELECT CAST({expr} AS DOUBLE) AS x FROM caged {where})
        WHERE x < ? OR x > ?
    """, [*params, lo, hi])["n"].iloc[0]
    return df, int(df["n"].sum()), int(outside)


def grouped_summary(expr: str, dim_key: str, f: Filters, extra: str | None = None,
                    limit: int = 50) -> pd.DataFrame:
    dim = DIMENSIONS[dim_key]
    where, params = build_where(f)
    cond = f"{expr} IS NOT NULL" + (f" AND {extra}" if extra else "")
    where = and_where(where, cond)
    df = run(f"""
        SELECT {dim.expr} AS {dim_key}, count(*) AS n, avg(CAST({expr} AS DOUBLE)) AS media,
               median(CAST({expr} AS DOUBLE)) AS mediana,
               quantile_cont(CAST({expr} AS DOUBLE), 0.25) AS q1,
               quantile_cont(CAST({expr} AS DOUBLE), 0.75) AS q3,
               stddev_samp(CAST({expr} AS DOUBLE)) AS desvio_padrao
        FROM caged {where} GROUP BY 1 ORDER BY n DESC LIMIT {int(limit)}
    """, params)
    return add_labels(sort_dimension(df, dim_key), dim_key)


MUNICIPAL_VARIABLES = {
    "pop_estimada": "População estimada",
    "pop_censo": "População (Censo 2022)",
    "densidade": "Densidade demográfica (hab/km²)",
    "area_km2": "Área territorial (km²)",
    "escolarizacao": "Escolarização 6 a 14 anos (%)",
    "idhm": "IDHM (2010)",
    "mortalidade_infantil": "Mortalidade infantil",
    "receitas": "Receitas brutas (R$)",
    "despesas": "Despesas brutas (R$)",
    "pib_per_capita": "PIB per capita (R$)",
    "admissoes": "Admissões (CAGED)",
    "desligamentos": "Desligamentos (CAGED)",
    "saldo": "Saldo (CAGED)",
    "saldo_10mil": "Saldo por 10 mil habitantes",
    "mov_10mil": "Movimentações por 10 mil habitantes",
    "mediana_salario_adm": "Mediana salarial das admissões (R$, sem zeros)",
}


def municipal_metrics(f: Filters) -> pd.DataFrame:
    """Uma linha por município: indicadores da base municipal + agregados do CAGED filtrado."""
    where, params = build_where(f)
    return run(f"""
        WITH c AS (
          SELECT municipio, count(*) FILTER (WHERE saldo = 1) AS admissoes,
                 count(*) FILTER (WHERE saldo = -1) AS desligamentos,
                 sum(saldo) AS saldo, count(*) AS movimentacoes,
                 median(salario) FILTER (WHERE saldo = 1 AND salario > 0) AS mediana_salario_adm
          FROM caged {where} GROUP BY 1)
        SELECT m.*, coalesce(c.admissoes, 0) AS admissoes, coalesce(c.desligamentos, 0) AS desligamentos,
               coalesce(c.saldo, 0) AS saldo, coalesce(c.movimentacoes, 0) AS movimentacoes,
               CAST(c.mediana_salario_adm AS DOUBLE) AS mediana_salario_adm,
               coalesce(c.saldo, 0) / m.pop_estimada * 10000 AS saldo_10mil,
               coalesce(c.movimentacoes, 0) / m.pop_estimada * 10000 AS mov_10mil
        FROM municipios m LEFT JOIN c ON c.municipio = m.cod6
        ORDER BY m.nome
    """, params)


# ------------------------------------------------------------------- relações


def aggregate(dim_keys: list[str], f: Filters, min_movements: int = 0) -> pd.DataFrame:
    """Tabela agregada por 1 a 3 dimensões (sem índice de escassez: só medidas descritivas)."""
    dims = [DIMENSIONS[k] for k in dim_keys]
    where, params = build_where(f)
    keys = ", ".join(f"{d.expr} AS {d.key}" for d in dims)
    df = run(f"""
        SELECT {keys},
               count(*) AS movimentacoes,
               count(*) FILTER (WHERE saldo = 1) AS admissoes,
               count(*) FILTER (WHERE saldo = -1) AS desligamentos,
               sum(saldo) AS saldo,
               count(*) FILTER (WHERE tipo_mov = '40') AS deslig_a_pedido,
               CAST(median(salario) FILTER (WHERE salario > 0) AS DOUBLE) AS mediana_salarial,
               CAST(median(salario) FILTER (WHERE salario > 0 AND saldo = 1) AS DOUBLE) AS mediana_adm,
               CAST(median(salario) FILTER (WHERE salario > 0 AND saldo = -1) AS DOUBLE) AS mediana_desl,
               count(DISTINCT cbo) AS ocupacoes,
               count(*) FILTER (WHERE escolaridade = '7') / count(*) AS pct_medio_completo,
               count(*) FILTER (WHERE escolaridade IN ('9', '80', '10', '11')) / count(*) AS pct_superior_ou_mais
        FROM caged {where}
        GROUP BY ALL HAVING count(*) >= ?
        ORDER BY movimentacoes DESC
    """, [*params, int(min_movements)])
    for d in dims:
        df = add_labels(df, d.key)
    return df


def education_distribution(dim_key: str, f: Filters, groups: list[str]) -> pd.DataFrame:
    """Contagem por grupo × grau de instrução, para os grupos informados."""
    dim = DIMENSIONS[dim_key]
    where, params = build_where(f)
    where = and_where(where, f"CAST({dim.expr} AS VARCHAR) IN ({', '.join('?' for _ in groups)})")
    df = run(f"""
        SELECT CAST({dim.expr} AS VARCHAR) AS grupo, escolaridade, count(*) AS n
        FROM caged {where} GROUP BY 1, 2
    """, [*params, *groups])
    return add_labels(df, "escolaridade")


def dictionary_coverage() -> pd.DataFrame:
    """Por coluna codificada: códigos do CAGED (normalizados) ausentes na aba do dicionário."""
    rows = []
    for c in CAGED_COLUMNS:
        if not c.sheet:
            continue
        df = run(f"""SELECT {c.typed} AS codigo, count(*) AS n FROM caged
                     WHERE {c.typed} NOT IN (SELECT codigo FROM rotulos WHERE variavel = ?)
                     GROUP BY 1 ORDER BY n DESC""", [c.sheet])
        rows.append({"coluna": c.name, "aba do dicionário": c.sheet,
                     "códigos fora do dicionário": len(df), "registros afetados": int(df["n"].sum()),
                     "exemplos": ", ".join(f"{r.codigo} ({fmt.integer(r.n)})" for r in df.head(30).itertuples())})
    return pd.DataFrame(rows)


def is_money(column_name: str) -> bool:
    col = BY_NAME.get(column_name)
    return bool(col and col.kind == MONEY)
