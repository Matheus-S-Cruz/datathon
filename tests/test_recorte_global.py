"""Recorte global (só indústria, seções, região, população) persiste entre páginas.

O Streamlit apaga o estado de um widget quando uma página roda sem desenhá-lo; o recorte é
guardado em `_recorte_salvo` e restaurado. Estes testes cobrem: persistência por todas as páginas
sem recorte, resultado idêntico ao recorte aplicado direto, padrões, isolamento dos filtros
próprios, regra das seções que deixam de valer e valores salvos inválidos.

    python -m pytest tests/test_recorte_global.py -q
"""

from __future__ import annotations

import json
import logging
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"
logging.getLogger("streamlit").setLevel(logging.ERROR)

KEYS = ("an_ind", "an_secoes", "an_regiao", "an_pop")
DEFAULTS = {"an_ind": False, "an_secoes": [], "an_regiao": "Todas", "an_pop": 0}
RECORTE = {"an_ind": True, "an_secoes": ["C"], "an_regiao": "Joinville", "an_pop": 20_000}
WITH_SCOPE = ["00_painel", "10_territorio", "11_setores", "12_renda_escolaridade"]
WITHOUT_SCOPE = ["01_overview", "02_caged_explorer", "03_municipalities", "04_dictionary", "05_audit",
                 "06_statistics", "07_relations", "13_macrofamilias", "14_contexto_ibge", "15_tabelas"]
OWN_FILTERS = {"13_macrofamilias": ("radio", "mf_recorte"), "14_contexto_ibge": ("radio", "ib_level")}


def session() -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.run()
    return at


def go(at: AppTest, page: str) -> AppTest:
    at.switch_page(f"views/{page}.py").run()
    return at


def apply(at: AppTest, values: dict) -> None:
    at.toggle(key="an_ind").set_value(values["an_ind"]).run()
    at.multiselect(key="an_secoes").set_value(values["an_secoes"]).run()
    at.selectbox(key="an_regiao").set_value(values["an_regiao"]).run()
    at.select_slider(key="an_pop").set_value(values["an_pop"]).run()


def controls(at: AppTest) -> dict:
    return {"an_ind": at.toggle(key="an_ind").value, "an_secoes": list(at.multiselect(key="an_secoes").value),
            "an_regiao": at.selectbox(key="an_regiao").value, "an_pop": at.select_slider(key="an_pop").value}


def problems(at: AppTest) -> list[str]:
    return [str(e.value) for e in at.error] + [str(e.value) for e in at.exception]


def content(at: AppTest) -> dict:
    """O que a página mostra: textos (sem o CSS), tabelas e dados dos gráficos."""
    return {"html": [str(h.proto.body) for h in at.get("html") if "<style>" not in str(h.proto.body)],
            "captions": [c.value for c in at.caption], "markdown": [m.value for m in at.markdown],
            "tables": [d.value.to_csv(index=False) for d in at.dataframe],
            "charts": [json.loads(c.proto.spec)["data"] for c in at.get("plotly_chart")]}


class TestRecorteGlobal(unittest.TestCase):
    def test_1_scope_survives_every_page_without_scope(self):
        for inter in WITHOUT_SCOPE:
            at = session()
            apply(at, RECORTE)
            for dest in WITH_SCOPE[1:]:
                with self.subTest(caminho=f"→ {inter} → {dest}"):
                    go(at, inter)
                    self.assertEqual(problems(at), [])
                    go(at, dest)
                    self.assertEqual(controls(at), RECORTE)
                    self.assertEqual(problems(at), [])

    def test_2_same_result_as_scope_applied_directly(self):
        via = session()
        apply(via, RECORTE)
        go(via, "04_dictionary")
        go(via, "10_territorio")
        direto = go(session(), "10_territorio")
        apply(direto, RECORTE)
        self.assertEqual(controls(via), controls(direto))
        self.assertEqual(content(via), content(direto))

    def test_3_defaults_unchanged(self):
        at = session()
        self.assertEqual(controls(at), DEFAULTS)
        for page in WITHOUT_SCOPE[:3] + WITH_SCOPE[1:]:
            go(at, page)
        self.assertEqual(controls(at), DEFAULTS)
        self.assertEqual(problems(at), [])
        self.assertTrue(set(at.session_state["_recorte_salvo"]) <= set(KEYS))

    def test_4_own_filters_are_isolated(self):
        limpo = session()
        refs = {}
        for page, (kind, key) in OWN_FILTERS.items():
            go(limpo, page)
            w = getattr(limpo, kind)(key=key)
            refs[page] = (w.value, list(w.options))
        go(limpo, "00_painel")
        refs_painel = {"pn_macro": (limpo.segmented_control(key="pn_macro").value,
                                    list(limpo.segmented_control(key="pn_macro").options))}

        at = session()
        apply(at, RECORTE)
        for page, (kind, key) in OWN_FILTERS.items():
            with self.subTest(pagina=page):
                go(at, page)
                w = getattr(at, kind)(key=key)
                self.assertEqual((w.value, list(w.options)), refs[page])
                rendered = {getattr(x, "key", None) for k in ("toggle", "multiselect", "selectbox", "select_slider")
                            for x in getattr(at, k)}
                self.assertFalse(rendered & set(KEYS), "página com filtros próprios desenhou o recorte global")
        # um filtro próprio alterado não entra na memória do recorte nem a altera
        go(at, "13_macrofamilias")
        at.radio(key="mf_recorte").set_value("Todos os setores").run()
        self.assertEqual(set(at.session_state["_recorte_salvo"]), set(KEYS))
        go(at, "00_painel")
        self.assertEqual(controls(at), RECORTE)
        # o seletor próprio das macrofamílias no painel mantém padrão e opções com o recorte aplicado
        self.assertEqual(at.segmented_control(key="pn_macro").value, refs_painel["pn_macro"][0])
        self.assertEqual(list(at.segmented_control(key="pn_macro").options), refs_painel["pn_macro"][1])

    def test_5_sections_rule_unchanged(self):
        at = session()
        at.multiselect(key="an_secoes").set_value(["N", "C"]).run()
        at.toggle(key="an_ind").set_value(True).run()
        self.assertEqual(list(at.multiselect(key="an_secoes").value), ["C"])  # N deixou de valer
        at.toggle(key="an_ind").set_value(False).run()
        self.assertEqual(list(at.multiselect(key="an_secoes").value), ["C"])  # e não volta
        go(at, "04_dictionary")
        go(at, "11_setores")
        self.assertEqual(list(at.multiselect(key="an_secoes").value), ["C"])
        self.assertEqual(problems(at), [])

    def test_6_invalid_saved_values_are_ignored(self):
        at = AppTest.from_file(str(APP), default_timeout=600)
        at.session_state["_recorte_salvo"] = {"an_ind": "sim", "an_secoes": ["ZZ", "N", "C"],
                                              "an_regiao": "Região inexistente", "an_pop": 123}
        at.run()
        self.assertEqual(problems(at), [])
        self.assertEqual(controls(at), {"an_ind": False, "an_secoes": ["N", "C"], "an_regiao": "Todas", "an_pop": 0})

    def test_7_restored_sections_respect_current_group(self):
        at = AppTest.from_file(str(APP), default_timeout=600)
        at.session_state["_recorte_salvo"] = {"an_ind": True, "an_secoes": ["N", "C"]}
        at.run()
        self.assertEqual(problems(at), [])
        self.assertEqual(at.toggle(key="an_ind").value, True)
        self.assertEqual(list(at.multiselect(key="an_secoes").value), ["C"])  # N não é industrial


if __name__ == "__main__":
    unittest.main()
