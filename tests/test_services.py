"""Testes da camada de dados do CAGED Explorer, contra os arquivos reais.

    python -m unittest tests.test_services -v

Os valores de referência vêm de docs/diagnostico_inicial.md (auditoria inicial).
"""

from __future__ import annotations

import csv
import io
import logging
import tempfile
import unittest
from pathlib import Path

import duckdb
import pandas as pd

from dashboard import formatting as fmt
from dashboard.services import queries as Q
from dashboard.services.catalog import CAGED_COLUMNS, typed_view_sql
from dashboard.services.dictionary import NO_DESCRIPTION, layout_table, load_sheets, search
from dashboard.services.municipalities import load_municipalities
from src.config import MUNICIPIOS_CSV

logging.getLogger("streamlit").setLevel(logging.ERROR)

TOTAL = 3_397_416


class TestLoading(unittest.TestCase):
    def test_caged_counts_match_audit(self):
        k = Q.overview_kpis()
        self.assertEqual(k["registros"], TOTAL)
        self.assertEqual(k["colunas_arquivo"], 30)
        self.assertEqual(k["admissoes"], 1_719_449)
        self.assertEqual(k["desligamentos"], 1_677_967)
        self.assertEqual(int(k["saldo"]), 41_482)
        self.assertEqual(k["admissoes"] + k["desligamentos"], TOTAL)
        self.assertEqual(k["saldo_invalido"], 0)
        self.assertEqual(k["municipios"], 295)
        self.assertEqual((k["dec_min"], k["dec_max"], k["dec_meses"]), ("202509", "202608", 12))

    def test_municipalities_clean(self):
        m = load_municipalities()
        self.assertEqual(len(m.data), 295)
        self.assertEqual(m.footer_rows, 1)
        self.assertTrue(m.data["dv_valido"].all())
        self.assertEqual(m.missing_dash["idhm"], 2)
        self.assertEqual(m.missing_dash["mortalidade_infantil"], 123)
        self.assertNotIn("prefeito", m.data.columns)
        self.assertFalse(any("<" in v for v in m.labels.values()), "cabeçalho com HTML")

    def test_dictionary(self):
        sheets = load_sheets()
        self.assertEqual(len(sheets), 23)
        self.assertEqual(len(layout_table(sheets)), 30)
        hits = search(sheets, "soldador")
        self.assertTrue((hits["aba"] == "cbo2002ocupação").any())
        self.assertEqual(Q.describe("tipomovimentação", "40"), "Desligamento a pedido")
        self.assertEqual(Q.describe("subclasse", "0111301"), "Cultivo de Arroz")  # zero à esquerda restaurado


class TestFilters(unittest.TestCase):
    def test_movement_filter_matches_kpis(self):
        self.assertEqual(Q.explorer_count(Q.Filters(movimento="Admissão")), 1_719_449)
        self.assertEqual(Q.explorer_count(Q.Filters(movimento="Desligamento")), 1_677_967)

    def test_section_and_municipality(self):
        self.assertEqual(Q.explorer_count(Q.Filters(secoes=("C",))), 836_753)
        per_mun = Q.flow_by("municipio").set_index("municipio")["movimentacoes"]
        both = Q.explorer_count(Q.Filters(municipios=("420910", "420540")))
        self.assertEqual(both, per_mun["420910"] + per_mun["420540"])

    def test_period_filter(self):
        dec = Q.flow_by("competencia_dec").set_index("competencia_dec")["movimentacoes"]
        n = Q.explorer_count(Q.Filters(competencia_inicio="202601", competencia_fim="202603"))
        self.assertEqual(n, dec[["202601", "202602", "202603"]].sum())

    def test_salary_filters(self):
        self.assertEqual(TOTAL - Q.explorer_count(Q.Filters(excluir_salario_zero=True)), 33_912)
        self.assertEqual(Q.explorer_count(Q.Filters(salario_min=50000.01)), 535)
        rows = Q.explorer_page(Q.Filters(salario_min=2000, salario_max=2000), ["salário"], "linha", False, 50, 1)
        self.assertTrue((rows["salário"] == "2000,00").all())

    def test_combined_filters_with_types(self):
        f = Q.Filters(secoes=("C",), movimento="Desligamento", tipos_mov=("40",))
        n = Q.explorer_count(f)
        agg = Q.aggregate(["secao"], Q.Filters(secoes=("C",)))
        self.assertEqual(n, int(agg["deslig_a_pedido"].iloc[0]))

    def test_value_filter_on_raw_column(self):
        n = Q.explorer_count(Q.Filters(valores_coluna=(("graudeinstrução", ("80",)),)))
        self.assertEqual(n, 33_303)


class TestPaginationSearchSort(unittest.TestCase):
    def test_pages_do_not_overlap(self):
        f = Q.Filters(municipios=("420005",))
        total = Q.explorer_count(f)
        seen = []
        for page in range(1, 5):
            seen += list(Q.explorer_page(f, [], "linha", False, 50, page)["linha"])
        self.assertEqual(len(seen), total)          # 185 registros em 4 páginas de 50
        self.assertEqual(len(set(seen)), total)     # sem repetição
        self.assertEqual(seen, sorted(seen))

    def test_numeric_sort_on_text_column(self):
        df = Q.explorer_page(Q.Filters(), ["salário"], "salário", True, 10, 1)
        values = df["salário"].str.replace(",", ".").astype(float)
        self.assertEqual(values.iloc[0], 3_471_600.0)
        self.assertTrue(values.is_monotonic_decreasing)

    def test_text_search_modes(self):
        contains = Q.explorer_page(Q.Filters(texto="7155", texto_coluna="cbo2002ocupação"),
                                   ["cbo2002ocupação"], "linha", False, 200, 1)
        self.assertTrue(contains["cbo2002ocupação"].str.contains("7155").all())
        exact = Q.explorer_count(Q.Filters(texto="715505", texto_coluna="cbo2002ocupação", texto_modo="igual"))
        starts = Q.explorer_count(Q.Filters(texto="7155", texto_coluna="cbo2002ocupação", texto_modo="começa com"))
        n_contains = Q.explorer_count(Q.Filters(texto="7155", texto_coluna="cbo2002ocupação"))
        self.assertGreater(exact, 0)
        self.assertLessEqual(exact, starts)
        self.assertLessEqual(starts, n_contains)
        # pesquisa em todas as colunas encontra pelo menos o que a coluna encontra
        self.assertGreaterEqual(Q.explorer_count(Q.Filters(texto="715505")), exact)

    def test_search_is_parameterized(self):
        # um termo com aspas não pode quebrar nem alterar o SQL
        self.assertEqual(Q.explorer_count(Q.Filters(texto="x' OR '1'='1")), 0)

    def test_record_and_samples(self):
        rec = Q.record(1)
        self.assertEqual(len(rec), 1)
        self.assertEqual(rec["salário"].iloc[0], "2018,00")
        self.assertEqual(float(rec["salario"].iloc[0]), 2018.0)
        self.assertTrue(Q.record(TOTAL + 1).empty)
        first = Q.explorer_sample(Q.Filters(), [], 5, "primeiros", 0)
        self.assertEqual(list(first["linha"]), [1, 2, 3, 4, 5])
        a = Q.explorer_sample(Q.Filters(), [], 50, "aleatória", 7)
        b = Q.explorer_sample(Q.Filters(), [], 50, "aleatória", 7)
        c = Q.explorer_sample(Q.Filters(), [], 50, "aleatória", 8)
        self.assertEqual(list(a["linha"]), list(b["linha"]))     # reprodutível
        self.assertNotEqual(list(a["linha"]), list(c["linha"]))  # semente muda a amostra
        self.assertGreater(a["linha"].max(), 1_000_000)          # não fica só no início do arquivo


class TestExport(unittest.TestCase):
    def test_csv_export(self):
        f = Q.Filters(municipios=("420005",))
        data, n = Q.export_csv(f, ["município", "salário"], "linha", False)
        self.assertEqual(n, Q.explorer_count(f))
        self.assertTrue(data.startswith("﻿".encode("utf-8")))
        rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(rows[0], ["linha", "município", "salário"])
        self.assertEqual(len(rows) - 1, n)
        self.assertTrue(all(r[1] == "420005" for r in rows[1:]))
        self.assertTrue(all("," in r[2] for r in rows[1:]))  # valor original preservado (vírgula decimal)

    def test_export_cap(self):
        _, n = Q.export_csv(Q.Filters(), ["município"], "linha", False, max_rows=1000)
        self.assertEqual(n, 1000)


class TestMissingAndInvalid(unittest.TestCase):
    def test_missing_age_excluded_and_counted(self):
        s = Q.numeric_summary("idade_anos", Q.Filters())
        self.assertEqual(int(s["total"] - s["n"]), 2_202)

    def test_invalid_values_become_null_not_zero(self):
        """Valores inválidos viram NULL (e são contados na auditoria), nunca 0."""
        con = duckdb.connect()
        good = {c.name: "1" for c in CAGED_COLUMNS}
        good.update({"salário": "2018,00", "valorsaláriofixo": "2018,00", "idade": "40.0",
                     "horascontratuais": "44,00", "saldomovimentação": "1", "subclasse": "111301",
                     "cbo2002ocupação": "71550"})
        bad = dict(good, **{"salário": "1.234,56", "idade": "", "horascontratuais": "abc",
                            "saldomovimentação": "x"})
        raw = pd.DataFrame([good, bad])
        raw.insert(0, "linha", [1, 2])
        con.execute("CREATE TABLE caged_raw AS SELECT * FROM raw")
        con.execute(typed_view_sql("caged_raw"))
        out = con.execute("SELECT salario, idade_anos, horas, saldo, subclasse7, cbo, divisao_cnae, movimento "
                          "FROM caged ORDER BY linha").df()
        self.assertEqual(float(out["salario"][0]), 2018.0)
        self.assertEqual(out["subclasse7"][0], "0111301")
        self.assertEqual(out["divisao_cnae"][0], "01")
        self.assertEqual(out["cbo"][0], "071550")
        self.assertEqual(out["movimento"][0], "Admissão")
        for col in ["salario", "idade_anos", "horas", "saldo", "movimento"]:
            self.assertTrue(pd.isna(out[col][1]), f"{col} inválido deveria ser NULL")

    def test_municipalities_with_problems(self):
        """CSV com município faltando, valor inválido e '-' : nada é descartado em silêncio."""
        lines = MUNICIPIOS_CSV.read_text(encoding="utf-8").splitlines()
        header, body, footer = lines[0], lines[1:-1], lines[-1]
        body = body[1:]                                   # remove Abdon Batista (4200051)
        cells = body[0].split(",")
        cells[13] = "abc"                                  # PIB per capita inválido
        body[0] = ",".join(cells)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mun.csv"
            path.write_text("\n".join([header, *body, footer]), encoding="utf-8")
            m = load_municipalities(path)
        self.assertEqual(len(m.data), 294)
        self.assertEqual(m.invalid["pib_per_capita"], 1)
        self.assertTrue(m.data["pib_per_capita"].isna().sum() == 1)
        # o código que sumiu da base municipal ficaria órfão no CAGED:
        orphans = Q.explorer_count(Q.Filters(municipios=("420005",)))
        self.assertEqual(orphans, 185)
        self.assertNotIn("420005", set(m.data["cod6"]))

    def test_unknown_codes_are_not_invented(self):
        df = pd.DataFrame({"cbo": ["715505", "999998"], "municipio": ["420910", "999999"]})
        df = Q.add_labels(df, "cbo")
        df = Q.add_labels(df, "municipio")
        self.assertEqual(df["cbo_descricao"][1], NO_DESCRIPTION)
        self.assertEqual(df["municipio_descricao"][0], "Joinville")
        self.assertEqual(df["municipio_descricao"][1], NO_DESCRIPTION)


class TestAggregations(unittest.TestCase):
    def test_aggregate_totals(self):
        agg = Q.aggregate(["secao"], Q.Filters())
        self.assertEqual(int(agg["movimentacoes"].sum()), TOTAL)
        self.assertEqual(int(agg["saldo"].sum()), 41_482)
        c = agg.set_index("secao").loc["C"]
        self.assertEqual(int(c["admissoes"]), Q.explorer_count(Q.Filters(secoes=("C",), movimento="Admissão")))

    def test_multi_dimension_and_minimum(self):
        agg = Q.aggregate(["municipio", "divisao_cnae", "cbo"], Q.Filters(secoes=("C",)), min_movements=100)
        self.assertTrue((agg["movimentacoes"] >= 100).all())
        self.assertTrue(agg[["municipio", "divisao_cnae", "cbo"]].duplicated().sum() == 0)
        self.assertTrue(agg["pct_superior_ou_mais"].between(0, 1).all())

    def test_median_and_quartiles(self):
        s = Q.numeric_summary("salario", Q.Filters())
        self.assertEqual((s["mediana"], s["q1"], s["q3"], s["maximo"]), (2155.0, 1935.0, 2550.0, 3_471_600.0))
        self.assertAlmostEqual(s["media"], 2478.58, places=2)

    def test_spearman_sql_matches_pandas(self):
        f = Q.Filters(municipios=("420010",), excluir_salario_zero=True)   # 5.158 registros, muitos empates
        r = Q.correlation("salario", "idade_anos", f)
        where, params = Q.build_where(f)
        df = Q.run(f"SELECT CAST(salario AS DOUBLE) AS x, idade_anos AS y FROM caged {where} "
                   "AND idade_anos IS NOT NULL", params)
        self.assertEqual(int(r["n"]), len(df))
        self.assertAlmostEqual(r["pearson"], df["x"].corr(df["y"]), places=9)
        self.assertAlmostEqual(r["spearman"], df.corr(method="spearman").iloc[0, 1], places=9)

    def test_histogram_counts_all_rows(self):
        bins, inside, outside = Q.histogram("salario", Q.Filters(), 0, 10000, 20)
        self.assertEqual(inside + outside, TOTAL)
        self.assertEqual(int(bins["n"].sum()), inside)

    def test_education_order(self):
        edu = Q.flow_by("escolaridade")
        order = list(edu["escolaridade"])
        self.assertLess(order.index("9"), order.index("80"))
        self.assertLess(order.index("80"), order.index("10"))


class TestFormatting(unittest.TestCase):
    def test_brazilian_formats(self):
        self.assertEqual(fmt.integer(3397416), "3.397.416")
        self.assertEqual(fmt.brl(2478.584), "R$ 2.478,58")
        self.assertEqual(fmt.pct(0.0287), "2,9%")
        self.assertEqual(fmt.signed(-48616), "−48.616")
        self.assertEqual(fmt.competencia("202509"), "set/2025")
        self.assertEqual(fmt.date_time(pd.Timestamp("2026-11-10 10:31")), "10/11/2026 10:31")
        self.assertEqual(fmt.integer(None), "—")


if __name__ == "__main__":
    unittest.main()
