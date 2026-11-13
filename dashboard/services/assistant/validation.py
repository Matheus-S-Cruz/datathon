"""Validação e proteção do assistente (etapa 4, §9 do prompt).

As permissões são aplicadas AQUI, no código, não no prompt do modelo. A camada conversacional nunca
recebe SQL, Python, caminho de arquivo ou nome de ferramenta livres: tudo passa por validação contra
listas brancas. Perguntas são tratadas como DADOS, nunca como instruções superiores.
"""

from __future__ import annotations

import re

MAX_PERGUNTA = 500          # limite de tamanho da pergunta (caracteres)
MIN_PERGUNTA = 2

# Padrões que indicam tentativa de injeção/abuso. Não bloqueiam a conversa — marcam a pergunta para
# que o orquestrador responda com a recusa padrão, sem repassar nada a ferramentas.
_INJECAO = re.compile(
    r"(ignore\s+(as\s+)?(instru|regras|anteriores)|esque[çc]a\s+as\s+instru|"
    r"voc[êe]\s+agora\s+é|aja\s+como|system\s+prompt|prompt\s+do\s+sistema|"
    r"revele\s+(suas|as)\s+instru|mostre\s+o\s+prompt|api[_\s-]?key|chave\s+de\s+api|"
    r"senha|credenc|token\s+secreto|\.env|secrets|"
    r"\bSELECT\b.+\bFROM\b|\bDROP\b|\bDELETE\b|\bos\.|subprocess|eval\(|exec\(|import\s+os|"
    r"/etc/|\.\./|sistema\s+de\s+arquivos)",
    re.IGNORECASE | re.DOTALL)


class EntradaInvalida(ValueError):
    """Pergunta vazia, longa demais ou malformada."""


def sanitiza_pergunta(texto: str) -> str:
    """Normaliza e valida o tamanho da pergunta. Não interpreta o conteúdo — só higieniza."""
    if texto is None:
        raise EntradaInvalida("Pergunta vazia.")
    t = " ".join(str(texto).split())          # colapsa espaços/quebras
    if len(t) < MIN_PERGUNTA:
        raise EntradaInvalida("Pergunta vazia.")
    if len(t) > MAX_PERGUNTA:
        raise EntradaInvalida(f"Pergunta longa demais (máximo {MAX_PERGUNTA} caracteres).")
    return t


def parece_injecao(texto: str) -> bool:
    """True se a pergunta tenta manipular o assistente, extrair segredos ou executar código."""
    return bool(_INJECAO.search(texto or ""))


def valida_na_lista(valor: str, permitidos, rotulo: str) -> str:
    """Garante que `valor` está na lista branca `permitidos`; senão, erro claro (sem vazar internals)."""
    if valor not in permitidos:
        raise EntradaInvalida(f"{rotulo} não reconhecido.")
    return valor
