"""Renderiza cada página do Pulso Industry sem navegador (streamlit.testing.AppTest)
e falha se alguma página mostrar erro ou levantar exceção.

    python -m unittest tests.test_app_pages -v
"""

from __future__ import annotations

import logging
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"
PAGES = ["00_painel", "01_overview", "02_caged_explorer", "03_municipalities", "04_dictionary", "05_audit",
         "06_statistics", "07_relations", "10_territorio", "11_setores", "12_renda_escolaridade",
         "13_macrofamilias", "14_contexto_ibge", "15_tabelas", "16_catalogo"]

logging.getLogger("streamlit").setLevel(logging.ERROR)


def run_page(page: str) -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.run()
    at.switch_page(f"views/{page}.py").run()
    return at


def problems(at: AppTest) -> list[str]:
    return [str(e.value) for e in at.error] + [str(e.value) for e in at.exception]


class TestPagesRender(unittest.TestCase):
    def test_each_page_renders_without_errors(self):
        for page in PAGES:
            with self.subTest(page=page):
                at = run_page(page)
                self.assertEqual(problems(at), [], f"{page} mostrou erro")
                self.assertTrue(at.title, f"{page} sem título")

    def test_overview_shows_audit_counts(self):
        at = run_page("01_overview")
        metrics = {m.label: m.value for m in at.metric}
        self.assertEqual(metrics["Admissões"], "1.719.449")
        self.assertEqual(metrics["Desligamentos"], "1.677.967")
        self.assertEqual(metrics["Saldo"], "+41.482")
        self.assertEqual(metrics["Registros do CAGED"], "3.397.416")

    def test_painel_is_default_and_matches_audit(self):
        at = AppTest.from_file(str(APP), default_timeout=600)
        at.run()
        self.assertEqual(problems(at), [])
        self.assertEqual(at.title[0].value, "Mercado de Trabalho Industrial de Santa Catarina")
        html = " ".join(str(h.proto.body) for h in at.get("html"))
        self.assertIn("+41.482", html)          # mesmo saldo da auditoria
        self.assertIn("1.719.449 admissões", html)

    def test_painel_industrial_scope(self):
        at = AppTest.from_file(str(APP), default_timeout=600)
        at.run()
        at.toggle(key="an_ind").set_value(True).run()
        at.selectbox(key="an_regiao").set_value("Joinville").run()
        self.assertEqual(problems(at), [])

    def test_explorer_filter_and_pagination(self):
        at = run_page("02_caged_explorer")
        submit = [b for b in at.sidebar.button if "Aplicar" in b.label]
        self.assertTrue(submit)
        at.multiselect(key="exp_sec").set_value(["C"])
        at.radio(key="exp_mov").set_value("Desligamento")
        submit[0].click().run()
        metrics = {m.label: m.value for m in at.metric}
        self.assertEqual(metrics["Registros encontrados"], "417.807")
        at.number_input(key="exp_page").set_value(3).run()
        self.assertEqual(problems(at), [])

    def test_relations_custom_grouping(self):
        at = run_page("07_relations")
        at.selectbox(key="rel_preset").set_value("Personalizado").run()
        at.multiselect(key="rel_dims").set_value(["secao", "escolaridade"]).run()
        self.assertEqual(problems(at), [])

    def test_statistics_municipal_level(self):
        at = run_page("06_statistics")
        at.segmented_control(key="stat_level").set_value("Municípios").run()
        self.assertEqual(problems(at), [])


if __name__ == "__main__":
    unittest.main()
