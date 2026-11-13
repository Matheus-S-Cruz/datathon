"""Glossário único (etapa 3.1): completo, fiel aos textos exibidos antes e sem cálculos.

    python -m pytest tests/test_glossario.py -q
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

import pandas as pd

from src import glossario as G
from src.config import OUTPUTS_DIR

ROOT = Path(__file__).resolve().parents[1]

# Textos exibidos ANTES da etapa 3.1, copiados literalmente das páginas (00_painel.py e 15_tabelas.py).
# O glossário não pode reescrevê-los: a etapa 3.1 só muda a origem dos textos.
KPI_AJUDA_ANTES = {
    "saldo": "Admissões − desligamentos no Novo CAGED, set/2025 a ago/2026.",
    "saldo_por_10k_censo": "Métrica do guia do Datathon: normaliza a comparação entre cidades de portes diferentes.",
    "cresc_emprego_pct": "Saldo do CAGED ÷ pessoal assalariado do CEMPRE 2024 × 100.",
    "rotatividade_pct": "Conceito DIEESE: parte do fluxo que é troca de trabalhadores, não vaga nova.",
    # salario_medio deixou de ser a manchete na etapa 3.2c; texto atualizado para marcar que é complemento.
    "salario_medio": "Média do salário declarado em admissões e desligamentos, ponderada pelo nº de "
                     "movimentações. Complemento da mediana; sensível a valores extremos.",
}
COLUMN_HELP_ANTES = {
    "saldo": "Admissões − desligamentos.",
    "giro": "Admissões + desligamentos.",
    "saldo_por_10k": "Saldo ÷ população × 10.000.",
    "giro_por_10k": "Giro ÷ população × 10.000.",
    "grau_medio": "Escolaridade média na escala ordinal 1 (analfabeto) a 12 (doutorado); 'não identificado' fora.",
    "pct_superior": "Fração das movimentações com superior completo, pós, mestrado ou doutorado.",
    "cresc_emprego_pct": "Saldo ÷ assalariados CEMPRE 2024 × 100.",
    "rotatividade_pct": "Mín(admissões, desligamentos) ÷ assalariados CEMPRE 2024 × 100 (conceito DIEESE).",
    "part_industria_vab_2021": "VAB da indústria ÷ VAB total, 2021.",
}
NOTAS_ANTES = {
    "mapa_formulas": "Saldo por 10 mil hab. = (admissões − desligamentos) ÷ população × 10.000. "
                     "Crescimento do emprego = saldo ÷ assalariados do CEMPRE 2024 × 100 (só sem recorte setorial).",
    "limite_fluxo": "Limite: o CAGED mede fluxo de admissões e desligamentos, não o estoque de empregos.",
    "regioes_formulas": "Crescimento = saldo ÷ assalariados do CEMPRE 2024 × 100. Rotatividade = mín(admissões, "
                        "desligamentos) ÷ assalariados × 100 (conceito DIEESE): a parte do fluxo que é troca de "
                        "trabalhadores, não vaga nova.",
    "regioes_leitura": "Leitura: regiões no alto e à esquerda trocam muitos trabalhadores sem crescer — sinal de "
                       "dificuldade de reter mão de obra. Limite: o CEMPRE 2024 é uma aproximação do estoque.",
    "macro_agrupamento": "Agrupamento determinístico pelo 1º dígito do código CBO-2002 (Grande Grupo); os grupos 7 e 8 "
                         "formam a macrofamília operacional.",
    # As três notas salariais foram atualizadas na etapa 3.2c (mediana sem zeros é a medida principal).
    "macro_salario": "Medida principal: mediana sem zeros (estável a valores extremos). A média, quando exibida, "
                     "é complemento e inclui todos os salários declarados (ver limites no fim da página).",
    "salario_relacao": "Relação descritiva: mostra quanto cada grupo recebe (mediana sem zeros), não que a "
                       "escolaridade cause a diferença. O `salário` do Novo CAGED já é mensalizado na origem (MTE).",
    "dispersao_relacao": "Relação descritiva entre três medidas do mesmo município; não indica causa. O salário por "
                         "município é a média (complemento), pois a mediana não é obtida de dados pré-agregados.",
    "renda_ressalva": "Ressalva metodológica: a medida principal é a mediana sem zeros. A média, quando exibida, "
                      "inclui salários informados como zero e valores de periodicidade não mensal (sobretudo por "
                      "hora; também por dia, semana, tarefa ou variável).",
}
IDS_ESPERADOS = {
    "saldo", "admissoes", "desligamentos", "giro", "movimentacoes", "saldo_por_10k_censo",
    "saldo_por_10k_estimativa", "giro_por_10k", "cresc_emprego_pct", "rotatividade_pct",
    "part_industria_vab_2021", "grau_medio", "pct_superior", "salario_medio", "salario_mediano",
    "macrofamilia", "periodo",
}


class TestGlossario(unittest.TestCase):
    def test_sixteen_indicators_with_all_fields(self):
        self.assertEqual({i.id for i in G.INDICADORES}, IDS_ESPERADOS)
        self.assertEqual(len(G.INDICADORES), 17)  # +salario_mediano (etapa 3.2c)
        for ind in G.INDICADORES:
            for campo in G.Indicador.CAMPOS:
                with self.subTest(indicador=ind.id, campo=campo):
                    valor = getattr(ind, campo)
                    self.assertIsInstance(valor, str)
                    self.assertTrue(valor.strip(), "campo vazio: use 'não se aplica' quando for o caso")

    def test_display_texts_are_literal_copies(self):
        for id_, txt in KPI_AJUDA_ANTES.items():
            self.assertEqual(G.texto(id_, "kpi_ajuda"), txt)
        self.assertEqual(G.texto("rotatividade_pct", "kpi_nota"), "reposição: mín(adm., desl.) ÷ estoque")
        self.assertEqual(G.PERIODO, "set/2025 a ago/2026 (competência de declaração do Novo CAGED)")
        self.assertEqual(G.ajuda_colunas(), COLUMN_HELP_ANTES)
        self.assertEqual(list(G.ajuda_colunas()), list(COLUMN_HELP_ANTES))  # mesma ordem de exibição
        self.assertEqual({k: G.nota(k) for k in G.NOTAS}, NOTAS_ANTES)

    def test_notes_reference_existing_indicators(self):
        ids = {i.id for i in G.INDICADORES}
        for nid, nota in G.NOTAS.items():
            self.assertTrue(set(nota.indicadores) <= ids, nid)

    def test_two_population_variants_documented_separately(self):
        censo, estim = G.indicador("saldo_por_10k_censo"), G.indicador("saldo_por_10k_estimativa")
        self.assertIn("Censo 2022", censo.fonte)
        self.assertIn("estimada", estim.fonte)
        self.assertNotEqual(censo.colunas, estim.colunas)
        self.assertNotEqual(censo.formula, estim.formula)
        self.assertIn("estimada 2026", censo.limitacoes)   # cada uma aponta a existência da outra
        self.assertIn("Censo 2022", estim.limitacoes)

    def test_columns_exist_in_data(self):
        cols = set()
        for f in OUTPUTS_DIR.glob("*.parquet"):
            cols |= set(pd.read_parquet(f).columns)
        queries = (ROOT / "dashboard" / "services" / "queries.py").read_text(encoding="utf-8")
        for ind in G.INDICADORES:
            for c in ind.colunas:
                with self.subTest(indicador=ind.id, coluna=c):
                    self.assertTrue(c in cols or f"AS {c}" in queries, f"coluna {c} não encontrada nos dados")

    def test_doc_is_in_sync(self):
        self.assertEqual(G.DOC_PATH.read_text(encoding="utf-8"), G.markdown(),
                         "docs/glossario.md desatualizado: rode `python -m src.glossario`")

    def test_glossary_has_no_calculations(self):
        tree = ast.parse((ROOT / "src" / "glossario.py").read_text(encoding="utf-8"))
        imports = {n.names[0].name if isinstance(n, ast.Import) else n.module
                   for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))}
        self.assertTrue(imports <= {"__future__", "dataclasses", "pathlib"}, imports)

    def test_pages_read_texts_from_glossary(self):
        painel = (ROOT / "dashboard" / "views" / "00_painel.py").read_text(encoding="utf-8")
        tabelas = (ROOT / "dashboard" / "views" / "15_tabelas.py").read_text(encoding="utf-8")
        for txt in list(KPI_AJUDA_ANTES.values()) + list(COLUMN_HELP_ANTES.values()):
            self.assertNotIn(txt, painel + tabelas, "texto ainda duplicado na página")
        self.assertIn("G.ajuda_colunas()", tabelas)


if __name__ == "__main__":
    unittest.main()
