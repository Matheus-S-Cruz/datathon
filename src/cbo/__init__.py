"""Classificação Brasileira de Ocupações (CBO-2002): hierarquia oficial e apoio à classificação.

Mantém separadas e documentadas as DUAS estruturas usadas no projeto (ver docs/cbo_classificacao.md):

- Hierarquia OFICIAL da CBO-2002 (`src.cbo.hierarquia`): 10 Grandes Grupos → 48 Subgrupos Principais
  → 194 Subgrupos → 627 Famílias → 2.778 Ocupações. É a referência principal.
- Macrofamílias ANALÍTICAS do projeto (9): agrupamento pelo 1º dígito do CBO, com os grupos 7 e 8
  fundidos em "Produção industrial (operacional)". Definidas no pipeline; NÃO são substituídas por esta
  etapa. As duas coexistem.
"""
