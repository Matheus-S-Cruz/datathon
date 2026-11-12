"""Testes das tabelas analíticas (pipeline + IBGE) usadas pelo painel.

    python -m pytest tests/test_analytics.py -q
"""

from __future__ import annotations

import unittest

import pandas as pd

from dashboard.services import analytics as A
from src.config import EXTERNAL_DIR


class TestAnalytics(unittest.TestCase):
    def test_state_totals_match_audit(self):
        k = A.kpis(A.Scope())
        self.assertEqual(k["saldo"], 41_482)
        self.assertEqual(k["admissoes"], 1_719_449)
        self.assertEqual(k["desligamentos"], 1_677_967)
        self.assertEqual(k["municipios"], 295)

    def test_education_is_ordinal_scale(self):
        # média de códigos (80 = pós) gerava valores acima de 11; a escala ordinal vai de 1 a 12
        for name in ["agg_municipio", "agg_setor", "macrofamilias_cbo"]:
            g = A.table(name)["grau_medio"].dropna()
            self.assertTrue(g.between(1, 12).all(), name)
        self.assertTrue(A.table("agg_municipio")["pct_superior"].between(0, 1).all())

    def test_ibge_bases_cover_all_municipalities(self):
        for name in ["ibge_regioes_sc", "ibge_cempre_2024", "ibge_pib_municipal"]:
            df = pd.read_parquet(EXTERNAL_DIR / f"{name}.parquet")
            self.assertEqual(len(df), 295, name)
            self.assertEqual(df.isna().sum().sum(), 0, name)
        mun = A.table("agg_municipio")
        self.assertEqual(mun["assalariados"].isna().sum(), 0)
        self.assertEqual(mun["regiao_intermediaria"].nunique(), 7)

    def test_regions_add_up_to_state(self):
        reg = A.regions("regiao_intermediaria")
        self.assertEqual(int(reg["saldo"].sum()), 41_482)
        self.assertEqual(int(A.regions("regiao_imediata")["saldo"].sum()), 41_482)

    def test_sector_scope_sums_and_hides_stock_rates(self):
        ind = A.Scope(secoes=A.INDUSTRIAL_SECTIONS)
        mun = A.municipal(ind)
        sec = A.sectors()
        expected = int(sec[sec["industrial"]]["saldo"].sum())
        self.assertEqual(int(mun["saldo"].sum()), expected)
        self.assertTrue(mun["cresc_emprego_pct"].isna().all())  # CEMPRE não é aberto por setor

    def test_region_filter(self):
        mun = A.municipal(A.Scope(regiao="Joinville"))
        self.assertTrue((mun["regiao_intermediaria"] == "Joinville").all())
        self.assertEqual(len(mun), 25)

    def test_geojson_ids_match_caged_codes(self):
        geo = A.geojson()
        ids = {f["id"] for f in geo["features"]}
        self.assertEqual(ids, set(A.table("agg_municipio")["mun_cod"]))


if __name__ == "__main__":
    unittest.main()
