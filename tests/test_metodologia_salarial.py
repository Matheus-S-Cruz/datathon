"""Testes das agregações salariais da metodologia 3.2 (ver docs/metodologia_salarial.md).

Valida que o pipeline acrescentou as medidas salariais da metodologia SEM sobrescrever as
colunas de origem, que os contadores de rastreabilidade conferem com a base e que a medida
principal (mediana sem zeros) equivale ao cálculo direto sobre os microdados.

    python -m pytest tests/test_metodologia_salarial.py -q
"""

from __future__ import annotations

import unittest

import duckdb
import pandas as pd

from dashboard.services import analytics as A
from src.config import CAGED_PARQUET

TOTAL = 3_397_416
ZEROS = 33_912  # salário = 0 (auditoria C1 e docs/metodologia_salarial.md)

# Colunas que a metodologia 3.2 garante existir nas tabelas agregadas por grupo.
NOVAS = ["salario_medio_s0", "salario_mediano_s0", "n_salario", "n_salario_s0"]
# Tabelas agregadas que passam a expor as medidas salariais da metodologia.
TABELAS = ["agg_municipio", "agg_municipio_setor", "agg_setor", "agg_regiao",
           "macrofamilias_cbo", "macrofamilias_industria", "perfil_adm_desl", "salario_por_grau"]


def _base():
    con = duckdb.connect(":memory:")
    con.execute(f"""CREATE VIEW c AS SELECT
        TRY_CAST(replace(trim("salário"), ',', '.') AS DECIMAL(18,2)) AS salario
        FROM read_parquet('{CAGED_PARQUET.as_posix()}')""")
    return con


class TestMetodologiaSalarial(unittest.TestCase):
    def test_novas_colunas_presentes(self):
        for name in TABELAS:
            df = A.table(name)
            for col in NOVAS:
                self.assertIn(col, df.columns, f"{name} sem coluna {col}")

    def test_coluna_de_origem_preservada(self):
        # salario_medio (média histórica, inclui zeros) continua existindo em todas as tabelas
        for name in TABELAS:
            self.assertIn("salario_medio", A.table(name).columns, name)

    def test_contadores_de_rastreabilidade(self):
        # n_salario = movimentações do grupo (salário nunca é nulo nesta base);
        # n_salario - n_salario_s0 = nº de zeros. Soma estadual confere com a auditoria.
        mun = A.table("agg_municipio")
        self.assertEqual(int(mun["n_salario"].sum()), TOTAL)
        self.assertEqual(int(mun["movimentacoes"].sum()), TOTAL)
        self.assertEqual(int(mun["n_salario"].sum() - mun["n_salario_s0"].sum()), ZEROS)
        # salario_por_grau cobre a base inteira e reproduz o mesmo nº de zeros
        sg = A.table("salario_por_grau")
        self.assertEqual(int(sg["n_salario"].sum()), TOTAL)
        self.assertEqual(int(sg["n_salario"].sum() - sg["n_salario_s0"].sum()), ZEROS)

    def test_n_salario_s0_nunca_excede_n_salario(self):
        for name in TABELAS:
            df = A.table(name)
            self.assertTrue((df["n_salario_s0"] <= df["n_salario"]).all(), name)
            self.assertTrue((df["n_salario_s0"] >= 0).all(), name)

    def test_mediana_s0_equivale_ao_calculo_direto_por_grau(self):
        # A medida principal por grau deve bater com a mediana (salário > 0) calculada direto
        # na base, agrupando pelo código do grau de instrução.
        con = _base()
        con.execute(f"""CREATE VIEW g AS SELECT
            trim("graudeinstrução") AS grau_cod,
            TRY_CAST(replace(trim("salário"), ',', '.') AS DECIMAL(18,2)) AS salario
            FROM read_parquet('{CAGED_PARQUET.as_posix()}')""")
        ref = con.execute("SELECT grau_cod, median(salario) FILTER (WHERE salario > 0) AS med "
                          "FROM g GROUP BY grau_cod").df()
        ref = {str(r.grau_cod): r.med for r in ref.itertuples()}
        sg = A.table("salario_por_grau")
        for r in sg.itertuples():
            esperado = ref.get(str(int(r.grau_cod)))
            if esperado is None or pd.isna(esperado):
                continue
            # tolerância de 1 centavo: pandas (float) e DuckDB (DECIMAL) interpolam a mediana
            # com arredondamentos ligeiramente diferentes em grupos com nº par de registros.
            self.assertAlmostEqual(float(r.salario_mediano_s0), float(esperado), delta=0.01,
                                   msg=f"grau {r.grau} difere do cálculo direto")

    def test_media_s0_nao_e_menor_que_media_com_zeros(self):
        # Excluir zeros só pode manter ou elevar a média de cada grupo (zeros puxam para baixo).
        for name in TABELAS:
            df = A.table(name).dropna(subset=["salario_medio", "salario_medio_s0"])
            df = df[df["n_salario_s0"] > 0]
            self.assertTrue((df["salario_medio_s0"] >= df["salario_medio"] - 1e-6).all(), name)

    def test_mediana_estadual_s0_proxima_da_auditoria(self):
        # A mediana sem zeros do estado inteiro é ~R$ 2.156 (auditoria C3 + metodologia 3.2).
        con = _base()
        med = con.execute("SELECT median(salario) FILTER (WHERE salario > 0) FROM c").fetchone()[0]
        self.assertAlmostEqual(float(med), 2156.23, places=2)


if __name__ == "__main__":
    unittest.main()
