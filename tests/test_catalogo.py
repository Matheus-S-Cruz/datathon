"""Catálogo de análises (etapa 3.3): página de entrada da Seção 3, só navegação.

Verifica que todos os cards apontam para páginas reais e registradas, que o selo "Filtros próprios"
marca exatamente as páginas com controles independentes do recorte global, e que o catálogo não
desenha gráficos nem altera dados.

    python -m pytest tests/test_catalogo.py -q
"""

from __future__ import annotations

import logging
import re
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
VIEWS = ROOT / "dashboard" / "views"
APP = ROOT / "dashboard" / "app.py"
logging.getLogger("streamlit").setLevel(logging.ERROR)

# Páginas da Seção 3 que usam filtros próprios (independentes do recorte global da barra lateral).
COM_FILTROS_PROPRIOS = {"views/14_contexto_ibge.py", "views/13_macrofamilias.py",
                        "views/06_statistics.py", "views/07_relations.py"}
SEM_FILTROS_PROPRIOS = {"views/10_territorio.py", "views/11_setores.py",
                        "views/12_renda_escolaridade.py", "views/05_audit.py"}


def _temas():
    import importlib.util
    spec = importlib.util.spec_from_file_location("catalogo_mod", VIEWS / "16_catalogo.py")
    mod = importlib.util.module_from_spec(spec)
    # o módulo chama ui.guarded(main) no fim; isso é inócuo fora do runtime do Streamlit
    try:
        spec.loader.exec_module(mod)
    except Exception:
        pass
    return mod.TEMAS


class TestCatalogo(unittest.TestCase):
    def test_todos_os_destinos_existem_em_disco(self):
        for _, _, analises in _temas():
            for a in analises:
                destino = a[1]
                self.assertTrue((ROOT / "dashboard" / destino).exists(),
                                f"card aponta para página inexistente: {destino}")

    def test_todos_os_destinos_estao_registrados_no_app(self):
        app = APP.read_text(encoding="utf-8")
        registradas = set(re.findall(r'page\("(\w+\.py)"', app))
        for _, _, analises in _temas():
            for a in analises:
                arquivo = a[1].split("/")[-1]
                self.assertIn(arquivo, registradas, f"{arquivo} não está no menu do app.py")

    def test_selo_filtros_proprios_bate_com_as_paginas(self):
        marcados = {a[1] for _, _, ans in _temas() for a in ans if a[4]}
        nao_marcados = {a[1] for _, _, ans in _temas() for a in ans if not a[4]}
        self.assertEqual(marcados, COM_FILTROS_PROPRIOS)
        self.assertEqual(nao_marcados, SEM_FILTROS_PROPRIOS)

    def test_quatro_temas_e_sem_duplicatas(self):
        temas = _temas()
        self.assertEqual(len(temas), 4)
        destinos = [a[1] for _, _, ans in temas for a in ans]
        self.assertEqual(len(destinos), len(set(destinos)), "análise duplicada no catálogo")

    def test_pagina_renderiza_sem_graficos_nem_erros(self):
        at = AppTest.from_file(str(APP), default_timeout=600)
        at.run()
        at.switch_page("views/16_catalogo.py").run()
        problems = [str(e.value) for e in at.error] + [str(e.value) for e in at.exception]
        self.assertEqual(problems, [])
        self.assertTrue(at.title)
        # é só navegação: nenhum gráfico desenhado
        self.assertEqual(len(at.get("plotly_chart")), 0)


if __name__ == "__main__":
    unittest.main()
