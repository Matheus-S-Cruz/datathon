"""Hierarquia oficial da CBO-2002 e preparação do piloto (etapas 3.5a e 3.5b).

Verifica que a estrutura oficial dos 5 níveis bate com a CBO-2002, que as 9 macrofamílias analíticas
do projeto são preservadas e mapeadas contra a oficial, e que o piloto baseline roda sem rede/custo e
só usa categorias da taxonomia fechada.

    python -m pytest tests/test_cbo.py -q
"""

from __future__ import annotations

import unittest

from src.cbo import classificador as C
from src.cbo import hierarquia as H


class TestHierarquiaOficial(unittest.TestCase):
    def test_cinco_niveis_batem_com_a_cbo2002(self):
        r = H.resumo()
        self.assertEqual(r["grandes_grupos"], 10)
        self.assertEqual(r["subgrupos_principais"], 48)
        self.assertEqual(r["subgrupos"], 194)
        self.assertEqual(r["familias"], 627)
        self.assertEqual(r["ocupacoes"], 2778)

    def test_dez_grandes_grupos_oficiais(self):
        self.assertEqual(set(H.GRANDES_GRUPOS), set("0123456789"))
        # grupos 7 e 8 têm o mesmo título oficial (produção industrial)
        self.assertEqual(H.GRANDES_GRUPOS["7"], H.GRANDES_GRUPOS["8"])

    def test_niveis_sao_prefixos_do_codigo(self):
        h = H.hierarquia()
        amostra = h.head(200)
        for r in amostra.itertuples():
            self.assertEqual(r.familia, r.cbo[:4])
            self.assertEqual(r.subgrupo, r.cbo[:3])
            self.assertEqual(r.subgrupo_principal, r.cbo[:2])
            self.assertEqual(r.grande_grupo, r.cbo[:1])

    def test_normaliza_reconstroi_zero_a_esquerda(self):
        self.assertEqual(H.normaliza(10105), "010105")   # origem numérica perde 1 zero
        self.assertEqual(H.normaliza("723410"), "723410")
        self.assertEqual(H.normaliza(" 848520 "), "848520")


class TestCoexistenciaMacrofamilias(unittest.TestCase):
    def test_nove_macrofamilias_preservadas(self):
        # 10 grandes grupos, mas 7 e 8 fundidos -> 9 macrofamílias distintas
        self.assertEqual(len(C.TAXONOMIA), 9)
        self.assertEqual(C.MACROFAMILIAS["7"], C.MACROFAMILIAS["8"])

    def test_macrofamilias_mapeiam_para_grandes_grupos_oficiais(self):
        # toda macrofamília analítica corresponde a um ou mais grandes grupos oficiais
        self.assertEqual(set(C.MACROFAMILIAS), set(H.GRANDES_GRUPOS))


class TestPilotoBaseline(unittest.TestCase):
    def test_baseline_classifica_sem_rede_e_so_na_taxonomia(self):
        lote = [C.Item(cbo="784205", ocupacao="Alimentador de Linha de Producao",
                       grande_grupo_oficial="7", grande_grupo_nome=H.GRANDES_GRUPOS["7"], volume=1000),
                C.Item(cbo="411005", ocupacao="Auxiliar de Escritorio",
                       grande_grupo_oficial="4", grande_grupo_nome=H.GRANDES_GRUPOS["4"], volume=500)]
        sug = C.BaselineProvider().classificar(lote)
        self.assertEqual(len(sug), 2)
        for s in sug:
            self.assertIn(s.grupo_oficial_sugerido, C.TAXONOMIA)  # nunca cria categoria nova
            self.assertEqual(s.confianca, "alta")
            self.assertEqual(s.codigo_original, s.cbo)            # código oficial preservado
            self.assertEqual(s.decisao_humana, "")                # revisão humana fica em aberto
        self.assertEqual(sug[0].grupo_oficial_sugerido, C.MACROFAMILIAS["7"])
        self.assertEqual(sug[1].grupo_oficial_sugerido, C.MACROFAMILIAS["4"])

    def test_saida_tem_campos_de_rastreabilidade_e_revisao(self):
        df = C.para_frame(C.BaselineProvider().classificar(
            [C.Item(cbo="723410", ocupacao="Soldador", grande_grupo_oficial="7",
                    grande_grupo_nome=H.GRANDES_GRUPOS["7"])]))
        for col in ["cbo", "ocupacao_original", "codigo_original", "grupo_oficial_sugerido",
                    "justificativa", "confianca", "decisao_humana", "resultado_final", "revisado_por"]:
            self.assertIn(col, df.columns)


if __name__ == "__main__":
    unittest.main()
