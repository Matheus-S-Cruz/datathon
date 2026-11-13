"""Ferramenta: consultar o glossário único (definição, fórmula, unidade, fonte, período, limitações).

Reutiliza `src/glossario.py` — a fonte única de conhecimento metodológico. Não duplica definições.
"""

from __future__ import annotations

from src import glossario as G

# Lista branca de indicadores que o assistente pode explicar (todos os ids do glossário).
IDS = tuple(i.id for i in G.INDICADORES)

# Apelidos em linguagem natural -> id do indicador. Permite casar termos comuns sem um LLM.
APELIDOS: dict[str, str] = {
    "saldo": "saldo", "saldo de movimentações": "saldo", "saldo de empregos": "saldo",
    "saldo de vagas": "saldo",
    "admissões": "admissoes", "admissoes": "admissoes",
    "desligamentos": "desligamentos",
    "giro": "giro", "movimentações": "movimentacoes", "movimentacoes": "movimentacoes",
    "rotatividade": "rotatividade_pct", "taxa de rotatividade": "rotatividade_pct",
    "crescimento do emprego": "cresc_emprego_pct", "crescimento": "cresc_emprego_pct",
    "saldo por 10 mil": "saldo_por_10k_censo", "saldo por 10 mil habitantes": "saldo_por_10k_censo",
    "escolaridade": "grau_medio", "escolaridade média": "grau_medio",
    "superior completo": "pct_superior", "com superior": "pct_superior",
    "salário": "salario_mediano", "salario": "salario_mediano", "salário mediano": "salario_mediano",
    "salario mediano": "salario_mediano", "salário médio": "salario_medio", "salario medio": "salario_medio",
    "renda": "salario_mediano",
    "macrofamília": "macrofamilia", "macrofamilia": "macrofamilia", "ocupações": "macrofamilia",
    "ocupacoes": "macrofamilia", "classificação das ocupações": "macrofamilia",
    "indústria no vab": "part_industria_vab_2021", "participação da indústria": "part_industria_vab_2021",
    "período": "periodo", "periodo": "periodo",
}


def resolve_id(termo: str) -> str | None:
    """Casa um termo de linguagem natural com um id de indicador, ou None se não reconhecer."""
    t = (termo or "").strip().lower()
    if t in IDS:
        return t
    if t in APELIDOS:
        return APELIDOS[t]
    # casamento por substring no nome do apelido (ex.: "o que é a rotatividade?")
    for apelido, id_ in APELIDOS.items():
        if apelido in t:
            return id_
    return None


def explicar(id_indicador: str) -> dict:
    """Devolve os campos documentados de um indicador. Erro de chave vira dict vazio controlado."""
    if id_indicador not in IDS:
        return {}
    ind = G.indicador(id_indicador)
    return {
        "id": ind.id, "nome": ind.nome, "grupo": ind.grupo,
        "definicao": ind.definicao, "formula": ind.formula, "unidade": ind.unidade,
        "fonte": ind.fonte, "periodo": ind.periodo, "abrangencia": ind.abrangencia,
        "filtragem": ind.filtragem, "limitacoes": ind.limitacoes,
    }


def nota(id_nota: str) -> str | None:
    try:
        return G.nota(id_nota)
    except KeyError:
        return None
