"""Estrutura das respostas do assistente.

Toda resposta carrega o texto e, quando apresenta número, a EVIDÊNCIA que o sustenta (fonte, período,
unidade, abrangência, recorte, ferramenta usada). Isso torna testável a regra de que o assistente não
inventa dados: se há número, há evidência rastreável; se não há dado, o tipo da resposta diz isso.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Kind(str, Enum):
    """Natureza da resposta — diferencia conceito de número e marca ausência de dado/erro."""
    DADO = "dado"                  # número real vindo de uma ferramenta/serviço oficial
    CONCEITO = "conceito"          # explicação conceitual (glossário/metodologia), sem número calculado
    SEM_DADOS = "sem_dados"        # não há dado suficiente para responder com segurança
    ESCLARECIMENTO = "esclarecimento"  # pergunta ambígua: o assistente pede para a pessoa especificar
    ERRO = "erro"                  # falha controlada (ex.: serviço de dados indisponível)


@dataclass(frozen=True)
class Evidencia:
    """Procedência de um número. Campos vazios quando não se aplicam."""
    ferramenta: str = ""           # qual ferramenta/serviço produziu o resultado
    indicador: str = ""            # id do indicador consultado
    fonte: str = ""
    periodo: str = ""
    unidade: str = ""
    abrangencia: str = ""
    recorte: tuple[str, ...] = ()  # recorte aplicado (descrição legível do Scope)
    limitacoes: str = ""


@dataclass(frozen=True)
class Resposta:
    """O que o orquestrador devolve à interface."""
    kind: Kind
    texto: str                     # markdown
    evidencia: Evidencia | None = None
    sugestoes: tuple[str, ...] = ()   # próximas perguntas sugeridas
    tabela: object | None = None      # DataFrame opcional para exibir (pequeno)

    @property
    def tem_numero(self) -> bool:
        return self.kind is Kind.DADO

    def rodape_evidencia(self) -> str:
        """Linha de procedência exibida abaixo de respostas com número (markdown)."""
        e = self.evidencia
        if not e:
            return ""
        partes = []
        if e.fonte:
            partes.append(f"**Fonte:** {e.fonte}")
        if e.periodo:
            partes.append(f"**Período:** {e.periodo}")
        if e.unidade:
            partes.append(f"**Unidade:** {e.unidade}")
        if e.abrangencia:
            partes.append(f"**Abrangência:** {e.abrangencia}")
        if e.recorte:
            partes.append("**Recorte aplicado:** " + ", ".join(e.recorte))
        if e.limitacoes:
            partes.append(f"**Limitações:** {e.limitacoes}")
        return "\n\n".join(partes)
