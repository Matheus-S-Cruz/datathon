"""Perfilamento das bases do desafio (somente leitura).

Gera, em Markdown, os números usados em docs/diagnostico_inicial.md:
volumetria, valores distintos, distribuições, salários, duplicidades e
validação da chave de junção CAGED x Municípios.

O Parquet é lido pelo DuckDB coluna a coluna, sem carregar os 3,4 milhões de
linhas na memória. Não altera nenhum arquivo.

Uso (a partir da raiz do repositório):
    python -m src.validation.profile_sources > reports/perfil_bases.md
"""

from __future__ import annotations

import sys

import duckdb
import openpyxl
import pandas as pd

from src.config import CAGED_PARQUET, DICIONARIO_XLSX, MUNICIPIOS_CSV


def section(title: str, df: pd.DataFrame) -> None:
    print(f"\n### {title}\n")
    print(df.to_markdown(index=False, floatfmt=",.2f"))


def dictionary_codes(wb, sheet: str) -> set[str]:
    rows = list(wb[sheet].iter_rows(values_only=True))[1:]
    return {str(r[0]) for r in rows if r and r[0] is not None}


def ibge_check_digit(code6: str) -> str:
    """Dígito verificador do código IBGE de município (7º dígito)."""
    total = 0
    for digit, weight in zip(code6, [1, 2, 1, 2, 1, 2]):
        product = int(digit) * weight
        total += product // 10 + product % 10
    return str((10 - total % 10) % 10)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    con = duckdb.connect()
    con.execute(f"CREATE VIEW c AS SELECT * FROM read_parquet('{CAGED_PARQUET.as_posix()}')")
    q = lambda sql: con.execute(sql).df()  # noqa: E731

    print("# Perfil das bases (gerado por src/validation/profile_sources.py)")

    # --- Novo CAGED -------------------------------------------------------
    cols = [r[0] for r in con.execute("DESCRIBE c").fetchall()]
    n = con.execute("SELECT count(*) FROM c").fetchone()[0]
    print(f"\n## Novo CAGED\n\nRegistros: {n:,} | Colunas: {len(cols)}")

    stats = []
    for col in cols:
        nd, nnull, nempty, mn, mx = con.execute(
            f'''SELECT count(DISTINCT "{col}"), count(*) - count("{col}"),
                       count(*) FILTER (WHERE trim("{col}") = ''),
                       min("{col}"), max("{col}") FROM c'''
        ).fetchone()
        stats.append({"coluna": col, "distintos": nd, "nulos": nnull, "vazios": nempty,
                      "min (texto)": mn, "max (texto)": mx})
    section("Colunas (todas armazenadas como texto)", pd.DataFrame(stats))

    section("Tipo de movimentação x saldo", q(
        "SELECT tipomovimentação, saldomovimentação, count(*) n FROM c GROUP BY ALL ORDER BY 1"))
    section("Admissões, desligamentos e saldo total", q(
        """SELECT count(*) FILTER (WHERE saldomovimentação = '1') admissoes,
                  count(*) FILTER (WHERE saldomovimentação = '-1') desligamentos,
                  sum(saldomovimentação::INT) saldo FROM c"""))
    section("Competência da declaração", q(
        """SELECT competênciadec, count(*) n,
                  count(*) FILTER (WHERE competênciamov <> competênciadec) mov_de_meses_anteriores,
                  count(*) FILTER (WHERE indicadordeforadoprazo = '1') fora_do_prazo
           FROM c GROUP BY 1 ORDER BY 1"""))
    section("Competência da movimentação", q(
        "SELECT competênciamov, count(*) n, sum(saldomovimentação::INT) saldo FROM c GROUP BY 1 ORDER BY 1"))
    section("Seção CNAE", q(
        "SELECT seção, count(*) n, sum(saldomovimentação::INT) saldo FROM c GROUP BY 1 ORDER BY 1"))
    section("Divisões CNAE da Indústria de Transformação (seção C)", q(
        """SELECT substr(lpad(subclasse, 7, '0'), 1, 2) divisao, count(*) n, sum(saldomovimentação::INT) saldo
           FROM c WHERE seção = 'C' GROUP BY 1 ORDER BY 1"""))
    for col in ["graudeinstrução", "categoria", "unidadesaláriocódigo", "tamestabjan",
                "origemdainformação", "tipoestabelecimento", "sexo"]:
        section(col, q(f'SELECT "{col}", count(*) n FROM c GROUP BY 1 ORDER BY try_cast("{col}" AS INT), 1'))
    section("tamestabjan = 99 por competência da declaração", q(
        "SELECT competênciadec, count(*) n FROM c WHERE tamestabjan = '99' GROUP BY 1"))

    con.execute("""CREATE VIEW s AS SELECT *,
        replace(salário, ',', '.')::DOUBLE sal,
        replace(valorsaláriofixo, ',', '.')::DOUBLE sal_fixo,
        try_cast(nullif(idade, '') AS DOUBLE) idade_num,
        replace(horascontratuais, ',', '.')::DOUBLE horas FROM c""")
    section("Salário (R$) — geral", q(
        """SELECT count(*) FILTER (WHERE sal = 0) zeros, min(sal) minimo,
                  quantile_cont(sal, 0.01) p01, quantile_cont(sal, 0.25) p25, median(sal) mediana,
                  quantile_cont(sal, 0.75) p75, quantile_cont(sal, 0.99) p99, max(sal) maximo,
                  avg(sal) media, count(*) FILTER (WHERE sal > 50000) acima_50mil FROM s"""))
    section("Salário por unidade de pagamento", q(
        """SELECT unidadesaláriocódigo, count(*) n, median(sal) mediana, count(*) FILTER (WHERE sal = 0) zeros
           FROM s GROUP BY 1 ORDER BY 1"""))
    section("Salário mensal (unidade 5, > 0) por tipo de saldo", q(
        """SELECT saldomovimentação, count(*) n, avg(sal) media, median(sal) mediana
           FROM s WHERE unidadesaláriocódigo = '5' AND sal > 0 GROUP BY 1"""))
    section("salário = valorsaláriofixo", q(
        "SELECT count(*) FILTER (WHERE sal = sal_fixo) iguais, count(*) total FROM s"))
    section("Idade e horas contratuais", q(
        """SELECT min(idade_num) idade_min, median(idade_num) idade_mediana, max(idade_num) idade_max,
                  count(*) - count(idade_num) idade_nula, min(horas) horas_min, median(horas) horas_mediana,
                  max(horas) horas_max FROM s"""))
    section("Linhas idênticas (ignorando colunas de índice)", q(
        """SELECT count(*) - (SELECT count(*) FROM (SELECT DISTINCT * EXCLUDE ("Unnamed: 0.1", "Unnamed: 0") FROM c))
           linhas_repetidas FROM c"""))
    section("CBOs distintos", q(
        """SELECT count(DISTINCT cbo2002ocupação) total,
                  count(DISTINCT cbo2002ocupação) FILTER (WHERE seção = 'C') secao_c FROM c"""))
    section("Seção C por grande grupo CBO (1º dígito)", q(
        """SELECT substr(lpad(cbo2002ocupação, 6, '0'), 1, 1) grande_grupo, count(*) n,
                  count(DISTINCT cbo2002ocupação) cbos FROM c WHERE seção = 'C' GROUP BY 1 ORDER BY 1"""))
    section("Seção C — concentração de CBOs", q(
        """WITH t AS (SELECT cbo2002ocupação, count(*) n FROM c WHERE seção = 'C' GROUP BY 1)
           SELECT count(*) FILTER (WHERE n >= 100) cbos_100_mais, count(*) FILTER (WHERE n >= 1000) cbos_1000_mais,
                  (SELECT sum(n) FROM (SELECT n FROM t ORDER BY n DESC LIMIT 200)) / sum(n) participacao_top200,
                  (SELECT count(DISTINCT substr(lpad(cbo2002ocupação, 6, '0'), 1, 4)) FROM c WHERE seção = 'C') familias_cbo
           FROM t"""))

    # --- Municípios ---------------------------------------------------------
    mun = pd.read_csv(MUNICIPIOS_CSV, dtype=str, keep_default_na=False)
    print(f"\n## Municípios SC\n\nLinhas: {len(mun)} | Colunas: {len(mun.columns)}")
    mun_stats = [{"coluna": col, "distintos": mun[col].nunique(),
                  "vazios": int((mun[col].str.strip() == "").sum()),
                  "traço '-'": int((mun[col].str.strip() == "-").sum())} for col in mun.columns]
    section("Colunas", pd.DataFrame(mun_stats))
    codes = mun["Código [-]"]
    valid = codes[codes.str.fullmatch(r"\d{7}")]
    print(f"\nCódigos com 7 dígitos: {len(valid)} | linhas não-município (rodapé): {len(codes) - len(valid)}")
    bad_dv = [c for c in valid if ibge_check_digit(c[:6]) != c[6]]
    print(f"Códigos com dígito verificador inválido: {len(bad_dv)}")

    con.register("m", pd.DataFrame({"cod6": valid.str[:6]}))
    section("Junção CAGED (6 dígitos) x Municípios (7 dígitos sem o verificador)", q(
        """SELECT (SELECT count(DISTINCT município) FROM c) municipios_caged,
                  (SELECT count(*) FROM m) municipios_csv,
                  (SELECT count(DISTINCT município) FROM c WHERE município IN (SELECT cod6 FROM m)) caged_com_par,
                  (SELECT count(*) FROM m WHERE cod6 NOT IN (SELECT DISTINCT município FROM c)) csv_sem_movimento,
                  (SELECT count(*) - count(DISTINCT cod6) FROM m) codigos_duplicados_csv"""))

    # --- Dicionário -----------------------------------------------------------
    wb = openpyxl.load_workbook(DICIONARIO_XLSX, read_only=True, data_only=True)
    rows = []
    for col in ["cbo2002ocupação", "subclasse", "graudeinstrução", "município", "categoria",
                "tamestabjan", "tipomovimentação", "seção", "unidadesaláriocódigo"]:
        known = dictionary_codes(wb, col)
        vals = con.execute(f'SELECT "{col}", count(*) FROM c GROUP BY 1').fetchall()
        missing = sorted([(v, k) for v, k in vals if v not in known], key=lambda x: -x[1])
        rows.append({"coluna": col, "codigos_fora_do_dicionario": len(missing),
                     "registros_afetados": sum(k for _, k in missing),
                     "exemplos": ", ".join(f"{v} ({k})" for v, k in missing[:5])})
    section("Cobertura do dicionário (códigos do CAGED ausentes nas abas)", pd.DataFrame(rows))


if __name__ == "__main__":
    main()
