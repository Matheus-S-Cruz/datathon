"""Ferramenta: consultar indicadores calculados pelos serviços OFICIAIS do projeto.

Reutiliza `dashboard/services/analytics.py` (contrato `Scope`). NÃO recalcula nenhuma fórmula aqui:
cada número vem da mesma função que a página usa. Toda saída inclui a evidência (fonte/período/
unidade/limitações) extraída do glossário, para que a resposta seja rastreável.

Parâmetros são validados contra listas brancas; municípios e indicadores desconhecidos resultam em
"sem dados", nunca em invenção.
"""

from __future__ import annotations

import pandas as pd

from dashboard.services import analytics as A
from dashboard.services.assistant.tools import glossary as gloss
from src import glossario as G


def _evidencia(id_indicador: str, scope: A.Scope | None = None) -> dict:
    """Metadados do glossário para compor a evidência de um número."""
    meta = gloss.explicar(id_indicador)
    rec = tuple(scope.describe()) if scope is not None else ()
    return {"indicador": id_indicador, "fonte": meta.get("fonte", ""),
            "periodo": meta.get("periodo", ""), "unidade": meta.get("unidade", ""),
            "abrangencia": meta.get("abrangencia", ""), "limitacoes": meta.get("limitacoes", ""),
            "recorte": rec}


def kpis_do_recorte(scope: A.Scope) -> dict:
    """KPIs do recorte: reusa analytics.kpis(scope). Devolve números + evidência por indicador."""
    k = A.kpis(scope)
    return {"valores": k, "scope_desc": tuple(scope.describe())}


def salario_estado() -> dict:
    """Salário mediano de SC (medida principal) + média, da tabela salario_resumo do pipeline."""
    s = A.salario_estado()
    return {"valores": s, "evidencia": _evidencia("salario_mediano")}


def top_municipios(scope: A.Scope, indicador: str = "saldo", n: int = 5, maiores: bool = True) -> dict:
    """Ranking de municípios por um indicador do agregado municipal (reusa analytics.municipal).

    `indicador` é validado contra as colunas disponíveis; valor fora da lista -> sem dados."""
    mun = A.municipal(scope)
    colunas_ok = {"saldo", "saldo_por_10k", "giro_por_10k", "salario_medio", "populacao",
                  "cresc_emprego_pct", "rotatividade_pct", "admissoes", "desligamentos"}
    if indicador not in colunas_ok or indicador not in mun.columns:
        return {"ok": False, "motivo": "indicador_invalido"}
    d = mun.dropna(subset=[indicador]).sort_values(indicador, ascending=not maiores).head(max(1, min(n, 20)))
    tab = d[["municipio", indicador]].reset_index(drop=True)
    return {"ok": True, "tabela": tab, "indicador": indicador,
            "scope_desc": tuple(scope.describe())}


def salario_por_escolaridade() -> dict:
    """Salário mediano (sem zeros) por grau de instrução — reusa a tabela do pipeline."""
    sg = A.table("salario_por_grau").sort_values("grau_ord")
    tab = sg[["grau", "salario_mediano_s0", "salario_medio"]].reset_index(drop=True)
    return {"ok": True, "tabela": tab, "evidencia": _evidencia("salario_mediano")}


def saldo_por_setor(scope: A.Scope, n: int = 8) -> dict:
    """Saldo por seção CNAE no recorte — reusa analytics.sectors_in_scope."""
    sec = A.sectors_in_scope(scope).sort_values("saldo", ascending=False)
    tab = sec[["setor", "saldo"]].head(max(1, min(n, 22))).reset_index(drop=True)
    return {"ok": True, "tabela": tab, "indicador": "saldo", "scope_desc": tuple(scope.describe())}
