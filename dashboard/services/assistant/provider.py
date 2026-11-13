"""Abstração do provedor do assistente (§10.1 do prompt).

O "cérebro" que interpreta a pergunta é desacoplado do resto. Trocar o provedor (simulado → LLM real)
não exige mudar interface, ferramentas, contexto nem contratos.

PRÉVIA: só o `SimulatedProvider` existe — determinístico, local, SEM custo. Ele mapeia a pergunta a uma
INTENÇÃO (e parâmetros) por palavras-chave. Não gera texto livre: devolve uma intenção estruturada que
o orquestrador transforma em chamada de ferramenta. Assim, a prévia é funcional e nunca inventa número.

Um `LLMProvider` futuro implementaria a mesma interface `classifica_intencao`, idealmente com
function-calling restrito às mesmas ferramentas — sem acesso a SQL/código livre.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Intencao:
    """Intenção estruturada que o orquestrador sabe executar."""
    nome: str                               # ver INTENCOES abaixo
    parametros: dict = field(default_factory=dict)
    confianca: str = "media"                # alta / media / baixa


# Intenções reconhecidas na prévia (cada uma é atendida por uma ferramenta controlada).
INTENCOES = (
    "kpis_painel",            # "quais os principais indicadores", "resumo"
    "explicar_indicador",     # "o que é X", "como é calculado X"
    "top_municipios",         # "municípios com maior/menor <indicador>"
    "salario_escolaridade",  # "salário por escolaridade"
    "salario_estado",        # "qual o salário", "renda mediana"
    "saldo_setores",         # "saldo por setor", "como a indústria se distribui"
    "distincao_populacao",   # "diferença entre as populações"
    "distincao_cbo",         # "o que significa a classificação das ocupações"
    "limitacoes_caged",      # "limitações dos dados"
    "causalidade",           # pergunta se X causou Y
    "ajuda",                 # "o que você faz"
    "desconhecida",          # nada reconhecido -> "não sei"
)


class Provider(Protocol):
    nome: str

    def classifica_intencao(self, pergunta: str, contexto) -> Intencao:
        ...


class SimulatedProvider:
    """Classificador de intenção determinístico por palavras-chave (prévia, sem custo)."""

    nome = "simulado-local"

    # (regex, intenção, extrator de parâmetros opcional)
    _REGRAS = [
        (r"\b(caus(ou|a|ar)|por causa|porque.*(aument|sob)|é por isso)\b", "causalidade"),
        (r"\b(o que (você|vc) faz|como funciona|o que posso perguntar|ajuda|me ajuda)\b", "ajuda"),
        (r"\b(limita[çc][õo]es|limita[çc][ãa]o|restri[çc][õo]es).*(caged|dados|base)|"
         r"\b(limita[çc][õo]es|limita[çc][ãa]o)\b", "limitacoes_caged"),
        (r"\b(diferen[çc]a|diferen[çc]as).*(popula[çc])|censo.*estimativa|estimativa.*censo|"
         r"popula[çc][ãa]o.*(2022|2026)", "distincao_populacao"),
        (r"\b(classifica[çc][ãa]o|agrupamento).*(ocupa|cbo|macrofam)|macrofam[íi]lia|"
         r"grande grupo|o que significa.*ocupa", "distincao_cbo"),
        (r"\b(sal[áa]rio|renda).*(escolaridade|grau|instru)|escolaridade.*(sal[áa]rio|renda)",
         "salario_escolaridade"),
        (r"\b(sal[áa]rio|renda|remunera)\b", "salario_estado"),
        (r"\b(setor|setores|ind[úu]stria|cnae).*(saldo|distribu|regi)|saldo.*(setor|cnae)|"
         r"como.*ind[úu]stria.*distribu", "saldo_setores"),
        (r"\b(munic[íi]pio|cidade).*(maior|menor|mais|top|ranking)|"
         r"(maior|menor).*(saldo|emprego).*munic", "top_municipios"),
        (r"\b(principais|resumo|panorama|vis[ãa]o geral).*(indicador|painel|dados)|"
         r"quais.*(indicador|kpi)|resumo do painel", "kpis_painel"),
        (r"\b(o que (é|e|significa)|defini[çc][ãa]o de|como.*(calcul|interpret)|explic)", "explicar_indicador"),
    ]

    def classifica_intencao(self, pergunta: str, contexto=None) -> Intencao:
        p = (pergunta or "").lower().strip()
        for regra in self._REGRAS:
            padrao, nome = regra[0], regra[1]
            if re.search(padrao, p):
                return Intencao(nome=nome, parametros=self._parametros(nome, p), confianca="media")
        return Intencao(nome="desconhecida", confianca="baixa")

    def _parametros(self, nome: str, p: str) -> dict:
        params: dict = {}
        if nome == "top_municipios":
            params["maiores"] = not bool(re.search(r"\bmenor|menos|pior|retra", p))
            if re.search(r"sal[áa]rio|renda", p):
                params["indicador"] = "salario_medio"
            elif re.search(r"popula", p):
                params["indicador"] = "populacao"
            elif re.search(r"rotativ", p):
                params["indicador"] = "rotatividade_pct"
            else:
                params["indicador"] = "saldo"
        if nome == "explicar_indicador":
            params["termo"] = p
        return params
