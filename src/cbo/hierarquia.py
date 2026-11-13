"""Hierarquia oficial da CBO-2002 (etapa 3.5a).

A Classificação Brasileira de Ocupações 2002 (Ministério do Trabalho e Emprego) tem cinco níveis,
lidos pelos primeiros dígitos do código de 6 dígitos da ocupação:

    dígitos  nível                 exemplo
    1        Grande Grupo          "7" = Trabalhadores da produção de bens e serviços industriais
    2        Subgrupo Principal    "72"
    3        Subgrupo              "723"
    4        Família               "7234"
    6        Ocupação              "723410" (código completo dos microdados)

Fonte da estrutura: Ministério do Trabalho e Emprego — CBO-2002
(https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/cbo). Os títulos das ocupações (nível 6) vêm do
dicionário oficial distribuído com os microdados do Novo CAGED
(`data/reference/Dicionario_de_dados.xlsx`, aba `cbo2002ocupação`). Os nomes dos Grandes Grupos são os
dez títulos oficiais da CBO-2002 (estáveis desde 2002).

Esta hierarquia é a REFERÊNCIA OFICIAL. Ela NÃO substitui as 9 macrofamílias analíticas do projeto
(agrupamento pelo 1º dígito com fusão dos grupos 7 e 8); as duas estruturas coexistem — ver
`docs/cbo_classificacao.md`.

Gerar a tabela de referência (`data/reference/cbo_hierarquia.parquet`):

    python -m src.cbo.hierarquia
"""

from __future__ import annotations

import pandas as pd

from src.config import DICIONARIO_XLSX, REFERENCE_DIR

# Os dez Grandes Grupos oficiais da CBO-2002 (1º dígito do código). Títulos oficiais do MTE.
GRANDES_GRUPOS: dict[str, str] = {
    "0": "Membros das Forças Armadas, Policiais e Bombeiros Militares",
    "1": "Membros superiores do poder público, dirigentes de organizações de interesse público e de "
         "empresas e gerentes",
    "2": "Profissionais das ciências e das artes",
    "3": "Técnicos de nível médio",
    "4": "Trabalhadores de serviços administrativos",
    "5": "Trabalhadores dos serviços, vendedores do comércio em lojas e mercados",
    "6": "Trabalhadores agropecuários, florestais, da caça e pesca",
    "7": "Trabalhadores da produção de bens e serviços industriais",
    "8": "Trabalhadores da produção de bens e serviços industriais",
    "9": "Trabalhadores de manutenção e reparação",
}

# Nível de qualificação associado ao Grande Grupo na metodologia da CBO-2002 (derivado da própria CBO,
# não de IA). É informativo; a referência é sempre o código oficial.
NIVEL_QUALIFICACAO: dict[str, str] = {
    "0": "Militar / segurança pública",
    "1": "Dirigentes e gerentes",
    "2": "Nível superior",
    "3": "Nível médio técnico",
    "4": "Administrativo",
    "5": "Serviços e comércio",
    "6": "Agropecuário",
    "7": "Operacional industrial",
    "8": "Operacional industrial",
    "9": "Manutenção e reparação",
}


def normaliza(codigo) -> str:
    """Normaliza o código da CBO para 6 dígitos com zero à esquerda.

    O Novo CAGED grava a CBO como número na planilha de domínio, então `010105` chega como `10105`.
    O menor código de 6 dígitos da CBO-2002 é `010105` (grande grupo e subgrupo principal nunca são
    zero ao mesmo tempo), então uma origem numérica perde no máximo um zero à esquerda — `zfill(6)`
    reconstrói com segurança."""
    return str(codigo).strip().zfill(6)


def ocupacoes() -> pd.DataFrame:
    """Lê as 2.778 ocupações (nível 6) do dicionário oficial, com código normalizado e título."""
    df = pd.read_excel(DICIONARIO_XLSX, sheet_name="cbo2002ocupação", dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={"código": "cbo", "descrição": "ocupacao"}).dropna(subset=["cbo"])
    df["cbo"] = df["cbo"].map(normaliza)
    return df[["cbo", "ocupacao"]].drop_duplicates("cbo").reset_index(drop=True)


def hierarquia() -> pd.DataFrame:
    """Tabela de referência: uma linha por ocupação, com os cinco níveis oficiais preenchidos.

    Colunas: cbo, ocupacao, familia, subgrupo, subgrupo_principal, grande_grupo, grande_grupo_nome,
    nivel_qualificacao. Os níveis intermediários (família, subgrupo, subgrupo principal) são os
    prefixos do código; o nome deles não vem no dicionário dos microdados (só o do Grande Grupo e o
    da ocupação são nomeados aqui — os CSV oficiais de família/subgrupo do MTE podem ser anexados
    depois, ver docs/cbo_classificacao.md)."""
    df = ocupacoes()
    df["familia"] = df["cbo"].str[:4]
    df["subgrupo"] = df["cbo"].str[:3]
    df["subgrupo_principal"] = df["cbo"].str[:2]
    df["grande_grupo"] = df["cbo"].str[:1]
    df["grande_grupo_nome"] = df["grande_grupo"].map(GRANDES_GRUPOS)
    df["nivel_qualificacao"] = df["grande_grupo"].map(NIVEL_QUALIFICACAO)
    return df[["cbo", "ocupacao", "familia", "subgrupo", "subgrupo_principal",
               "grande_grupo", "grande_grupo_nome", "nivel_qualificacao"]]


def resumo() -> dict[str, int]:
    """Contagem de níveis distintos — serve de checagem contra a estrutura oficial da CBO-2002."""
    h = hierarquia()
    return {
        "ocupacoes": h["cbo"].nunique(),
        "familias": h["familia"].nunique(),
        "subgrupos": h["subgrupo"].nunique(),
        "subgrupos_principais": h["subgrupo_principal"].nunique(),
        "grandes_grupos": h["grande_grupo"].nunique(),
    }


def exporta(path=None) -> str:
    path = path or (REFERENCE_DIR / "cbo_hierarquia.parquet")
    hierarquia().to_parquet(path, index=False)
    return str(path)


if __name__ == "__main__":
    caminho = exporta()
    r = resumo()
    print("Hierarquia CBO-2002 gerada:", caminho)
    for k, v in r.items():
        print(f"  {k}: {v}")
