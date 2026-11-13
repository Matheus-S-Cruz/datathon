"""Seção 3 — Catálogo de análises: ponto de entrada que organiza e aponta para as análises existentes.

Esta página NÃO calcula nada e NÃO desenha gráficos novos: é só navegação. Cada card descreve uma
análise que já existe em outra página e leva até ela. O selo "Filtros próprios" marca as páginas que
usam controles independentes do recorte global da barra lateral (etapa 3.3).
"""

import streamlit as st

from dashboard.components import ui

# Cada análise: (título, página de destino, explicação curta, o que investigar, usa filtros próprios?).
# O título e a explicação refletem o conteúdo real da página de destino; nada aqui altera essas páginas.
Analise = tuple[str, str, str, str, bool]

TEMAS: list[tuple[str, str, list[Analise]]] = [
    ("Território e municípios", "map",
     [("Território", "views/10_territorio.py",
       "Municípios em expansão, em retração e com alta rotatividade.",
       "Quais cidades criam ou perdem vagas e onde a troca de trabalhadores é maior.", False),
      ("Contexto regional (IBGE)", "views/14_contexto_ibge.py",
       "Estoque de emprego formal (CEMPRE 2024), peso da indústria no PIB e divisão regional oficial, "
       "cruzados com o saldo do CAGED.",
       "Como o fluxo do CAGED se compara ao estoque de empregos e à economia de cada região.", True)]),

    ("Setores e atividades econômicas", "factory",
     [("Setores", "views/11_setores.py",
       "Setores que lideram a criação e a perda de vagas, e onde estão os polos industriais.",
       "Quais seções CNAE puxam o saldo e em que municípios se concentram.", False)]),

    ("Ocupações e escolaridade", "school",
     [("Renda e escolaridade", "views/12_renda_escolaridade.py",
       "Quem entra e quem sai por grau de instrução, quanto cada nível recebe (salário mediano) e como "
       "isso se relaciona com o saldo dos municípios.",
       "Se há compressão salarial e como renda e escolaridade acompanham o saldo.", False),
      ("Macrofamílias de ocupações", "views/13_macrofamilias.py",
       "Os CBOs agrupados em macrofamílias pelo Grande Grupo da CBO-2002.",
       "Se o gargalo está em famílias de alta qualificação (técnico) ou na base operacional.", True)]),

    ("Mercado de trabalho e movimentações", "query_stats",
     [("Exploração estatística", "views/06_statistics.py",
       "Relações entre variáveis quantitativas, por registro do CAGED ou por município. "
       "Resultados exploratórios — associação, não causa.",
       "Correlações entre salário, escolaridade, saldo e indicadores municipais.", True),
      ("Relações territoriais e setoriais", "views/07_relations.py",
       "Combine município, setor, ocupação, escolaridade, salário e competência em medidas descritivas.",
       "Cruzamentos sob medida entre as dimensões do CAGED.", True),
      ("Resultados da auditoria", "views/05_audit.py",
       "Cada constatação recalculada agora a partir dos arquivos e comparada com o diagnóstico inicial.",
       "Se os números do projeto reproduzem a auditoria inicial das bases.", False)]),
]


def _card(analise: Analise) -> None:
    titulo, destino, explicacao, investigar, filtros_proprios = analise
    with ui.card(titulo, explicacao, key=f"cat_{destino}"):
        st.markdown(f"**O que investigar:** {investigar}")
        if filtros_proprios:
            st.badge("Filtros próprios", color="violet", icon=":material/tune:")
        st.page_link(destino, label=f"Abrir {titulo}", icon=":material/arrow_forward:")


def main() -> None:
    ui.header("Catálogo de análises",
              "Ponto de entrada das Análises complementares: escolha por tema e vá direto à análise. "
              "O selo “Filtros próprios” marca páginas com controles independentes do recorte da barra lateral.",
              eyebrow="Análises complementares")

    for nome_tema, icone, analises in TEMAS:
        ui.section(nome_tema, step=f":material/{icone}:")
        cols = st.columns(2, gap="medium")
        for i, analise in enumerate(analises):
            with cols[i % 2]:
                _card(analise)


ui.guarded(main)
