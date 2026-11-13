"""Contexto do assistente: página atual e recorte, a partir do estado da aplicação (§6 do prompt).

O contexto é lido de uma ESTRUTURA CONTROLADA (o `st.session_state` e um mapa de páginas), não da
interpretação do título visual. Páginas com filtros próprios são marcadas como tal, para o assistente
não assumir que o recorte global vale nelas.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dashboard.services import analytics as A

# Páginas do dashboard e se usam o recorte global (Scope) ou filtros próprios. Espelha o menu do app.py
# e a classificação já consolidada na etapa 3.3/3.4. (nome legível, usa_recorte_global, tem_filtros_proprios)
PAGINAS: dict[str, dict] = {
    "00_painel":            {"nome": "Painel executivo",            "recorte_global": True,  "filtros_proprios": False},
    "01_overview":          {"nome": "Bases e validação",           "recorte_global": False, "filtros_proprios": False},
    "02_caged_explorer":    {"nome": "Explorador do Novo CAGED",    "recorte_global": False, "filtros_proprios": True},
    "03_municipalities":    {"nome": "Municípios",                  "recorte_global": False, "filtros_proprios": True},
    "04_dictionary":        {"nome": "Dicionário de dados",         "recorte_global": False, "filtros_proprios": False},
    "05_audit":             {"nome": "Resultados da auditoria",     "recorte_global": False, "filtros_proprios": False},
    "06_statistics":        {"nome": "Exploração estatística",      "recorte_global": False, "filtros_proprios": True},
    "07_relations":         {"nome": "Relações territoriais e setoriais", "recorte_global": False, "filtros_proprios": True},
    "10_territorio":        {"nome": "Território",                  "recorte_global": True,  "filtros_proprios": False},
    "11_setores":           {"nome": "Setores",                     "recorte_global": True,  "filtros_proprios": False},
    "12_renda_escolaridade":{"nome": "Renda e escolaridade",        "recorte_global": True,  "filtros_proprios": False},
    "13_macrofamilias":     {"nome": "Macrofamílias de ocupações",  "recorte_global": False, "filtros_proprios": True},
    "14_contexto_ibge":     {"nome": "Contexto regional (IBGE)",    "recorte_global": False, "filtros_proprios": True},
    "15_tabelas":           {"nome": "Tabelas analíticas",          "recorte_global": True,  "filtros_proprios": False},
    "16_catalogo":          {"nome": "Catálogo de análises",        "recorte_global": False, "filtros_proprios": False},
}

# Chaves do recorte global no session_state (definidas em dashboard/components/filters.py).
_RECORTE_KEYS = ("an_ind", "an_secoes", "an_regiao", "an_pop")


@dataclass(frozen=True)
class Contexto:
    pagina_id: str = ""
    pagina_nome: str = ""
    recorte_global: bool = False      # a página desenha o recorte global?
    filtros_proprios: bool = False    # a página tem controles independentes?
    scope: A.Scope = field(default_factory=A.Scope)

    def recorte_legivel(self) -> tuple[str, ...]:
        """Descrição do recorte ativo (vazio = Santa Catarina inteira)."""
        return tuple(self.scope.describe())


def _scope_do_estado(state) -> A.Scope:
    """Reconstrói o Scope a partir do session_state, só com valores válidos. Sem estado, Scope padrão."""
    if state is None:
        return A.Scope()
    get = state.get if hasattr(state, "get") else (lambda k, d=None: state.get(k, d))
    only_ind = bool(get("an_ind", False))
    secoes = tuple(get("an_secoes", []) or ())
    if not secoes and only_ind:
        secoes = A.INDUSTRIAL_SECTIONS
    regiao = get("an_regiao", "Todas")
    regiao = None if regiao in (None, "Todas") else regiao
    pop = get("an_pop", 0) or 0
    try:
        return A.Scope(secoes=secoes, min_pop=int(pop), regiao=regiao)
    except Exception:
        return A.Scope()


def resolve(pagina_id: str = "", state=None) -> Contexto:
    """Monta o contexto a partir do id da página e do session_state.

    O recorte global só é considerado ativo quando a página o desenha (`recorte_global=True`); em
    páginas de filtros próprios, o Scope fica padrão (não se assume o recorte global)."""
    meta = PAGINAS.get(pagina_id, {"nome": pagina_id or "desconhecida",
                                   "recorte_global": False, "filtros_proprios": False})
    scope = _scope_do_estado(state) if meta["recorte_global"] else A.Scope()
    return Contexto(pagina_id=pagina_id, pagina_nome=meta["nome"],
                    recorte_global=meta["recorte_global"], filtros_proprios=meta["filtros_proprios"],
                    scope=scope)
