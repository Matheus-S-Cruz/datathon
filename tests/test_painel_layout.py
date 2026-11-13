"""Painel executivo (Fase 2): organização, selos de escopo e "Ver dados" fiéis aos gráficos.

    python -m pytest tests/test_painel_layout.py -q
"""

from __future__ import annotations

import base64
import json
import logging
import re
import unittest
from pathlib import Path

import numpy as np
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"
logging.getLogger("streamlit").setLevel(logging.ERROR)

# card -> escopo esperado (recorte = segue os filtros; estado = Santa Catarina inteira)
CARD_SCOPES = {"map": "recorte", "regions": "estado", "sectors": "recorte", "macro": "estado",
               "salary": "estado", "scatter": "recorte"}


def decode(values) -> list:
    """Plotly serializa arrays numéricos como {"dtype", "bdata"} (base64)."""
    if isinstance(values, dict) and "bdata" in values:
        return np.frombuffer(base64.b64decode(values["bdata"]), dtype=np.dtype(values["dtype"])).astype(float).tolist()
    return list(values)


def as_float(values) -> np.ndarray:
    return np.array([np.nan if v is None else v for v in decode(values)], dtype=float)


def render(*actions) -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.run()
    for kind, key, value in actions:
        getattr(at, kind)(key=key).set_value(value).run()
    return at


class TestPainelLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.at = render()
        cls.html = [str(h.proto.body) for h in cls.at.get("html") if "<style>" not in str(h.proto.body)]

    def test_global_css_has_no_html_inside(self):
        """Um sinal de menor dentro do CSS (ex.: citar uma tag num comentário) faz o sanitizador do
        st.html descartar o bloco de estilo inteiro — a página fica sem nenhum estilo, sem erro."""
        css = next(str(h.proto.body) for h in self.at.get("html") if "<style>" in str(h.proto.body))
        inner = css[css.index("<style>") + len("<style>"):css.rindex("</style>")]
        self.assertNotIn("<", inner)

    def test_no_errors(self):
        self.assertEqual([str(e.value) for e in self.at.error] + [str(e.value) for e in self.at.exception], [])

    def test_section_order(self):
        sections = [re.search(r"<b>(.*?)</b>", h).group(1) for h in self.html if 'class="rx-section"' in h]
        self.assertEqual(sections, ["A resposta em 3 leituras", "Onde o emprego cresce e onde ele gira",
                                    "Setores e funções", "Como a renda se relaciona com a escolaridade"])

    def test_each_chart_card_has_scope_badge(self):
        badges = [re.search(r"rx-scope (\w+)", h).group(1) for h in self.html
                  if "rx-card-title" in h and "rx-scope" in h]
        # 3 cards de leitura (estado inteiro) + os 6 gráficos, na ordem do painel
        self.assertEqual(badges, ["estado"] * 3 + list(CARD_SCOPES.values()))

    def test_reading_links_point_to_existing_sections(self):
        links = re.findall(r'href="#([\w-]+)"', " ".join(self.html))
        ids = re.findall(r'id="([\w-]+)"', " ".join(self.html))
        self.assertEqual(links, ["ev-onde", "ev-setores", "ev-renda"])
        self.assertTrue(set(links) <= set(ids))

    def test_income_reading_is_descriptive_with_caveat(self):
        text = " ".join(m.value for m in self.at.markdown)
        self.assertIn("Nos registros de movimentações com superior completo, a média dos valores salariais "
                      "informados é de R$ 3.990, contra R$ 2.354 para o médio completo — uma diferença de "
                      "aproximadamente 70%.", text)
        self.assertNotIn("paga", text)
        captions = " ".join(c.value for c in self.at.caption)
        self.assertIn("as médias incluem salários informados como zero e valores de periodicidade não mensal",
                      captions)

    def test_kpi_help_is_clickable(self):
        kpis = next(h for h in self.html if "rx-kpis" in h)
        self.assertEqual(kpis.count('class="rx-kpi-help"'), 5)

    def test_data_views_match_chart_data(self):
        for actions in [(), (("toggle", "an_ind", True),), (("selectbox", "an_regiao", "Joinville"),)]:
            at = render(*actions) if actions else self.at
            with self.subTest(recorte=actions):
                figs = [json.loads(c.proto.spec)["data"] for c in at.get("plotly_chart")]
                tabs = [d.value for d in at.dataframe]
                self.assertEqual(len(figs), 6)
                self.assertEqual(len(tabs), 6)
                expanders = [e.label for e in at.expander]
                self.assertEqual(expanders.count("Ver dados e método"), 6)
                mapa, reg, setores, macro, sal, disp = figs
                tm, tr, ts, tmac, tsal, tdisp = tabs
                np.testing.assert_array_equal(as_float(mapa[0]["z"]), tm.iloc[:, 2].astype(float).to_numpy())
                self.assertEqual(decode(mapa[0]["locations"]), list(tm.iloc[:, 0]))
                np.testing.assert_array_equal(as_float(reg[0]["x"]), tr.iloc[:, 1].to_numpy(float))
                np.testing.assert_array_equal(as_float(reg[0]["y"]), tr.iloc[:, 2].to_numpy(float))
                self.assertEqual(sorted(sum((decode(t["x"]) for t in setores), [])), sorted(ts.iloc[:, 2].tolist()))
                np.testing.assert_array_equal(as_float(macro[0]["x"]), tmac.iloc[:, 1].to_numpy(float))
                self.assertEqual(decode(macro[0]["y"]), list(tmac.iloc[:, 0]))
                np.testing.assert_array_equal(as_float(sal[0]["x"]), tsal.iloc[:, 1].to_numpy(float))
                self.assertEqual(decode(sal[0]["y"]), list(tsal.iloc[:, 0]))
                np.testing.assert_array_equal(as_float(disp[0]["x"]), tdisp.iloc[:, 1].to_numpy(float))
                np.testing.assert_array_equal(as_float(disp[0]["y"]), tdisp.iloc[:, 2].to_numpy(float))


if __name__ == "__main__":
    unittest.main()
