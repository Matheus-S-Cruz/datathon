"""Ferramenta: metadados e validações (municípios válidos, distinções metodológicas).

Reutiliza serviços oficiais para validar entidades (municípios, regiões) e para expor as diferenças
que o assistente não pode confundir: população Censo 2022 × estimativa 2026, e CBO oficial × as 9
macrofamílias analíticas (§7.2 e §7.4 do prompt).
"""

from __future__ import annotations

from dashboard.services import analytics as A


def municipios_validos() -> set[str]:
    """Nomes de municípios conhecidos pelo projeto (do agregado municipal)."""
    try:
        return set(A.table("agg_municipio")["municipio"])
    except Exception:
        return set()


def encontra_municipio(nome: str) -> str | None:
    """Casa um nome informado com um município conhecido (exato ou por prefixo), ou None."""
    nome = (nome or "").strip()
    if not nome:
        return None
    validos = municipios_validos()
    if nome in validos:
        return nome
    baixo = nome.lower()
    candidatos = [m for m in validos if m.lower() == baixo] or [m for m in validos if m.lower().startswith(baixo)]
    return candidatos[0] if len(candidatos) == 1 else None


def regioes_validas() -> list[str]:
    try:
        return A.region_names()
    except Exception:
        return []


# Distinções metodológicas que o assistente deve explicar quando relevantes (texto do glossário).
DISTINCAO_POPULACAO = (
    "O projeto usa duas medidas de população: **Censo 2022** (denominador das taxas por 10 mil "
    "habitantes nas páginas analíticas) e **estimativa 2026** (usada no Explorador). O mesmo município "
    "pode mostrar valores diferentes conforme a medida — elas não são diretamente comparáveis.")

DISTINCAO_CBO = (
    "Há duas formas de agrupar ocupações: a **classificação oficial da CBO-2002** (10 Grandes Grupos) "
    "e as **9 macrofamílias analíticas do projeto** (que fundem os Grandes Grupos 7 e 8 e usam nomes "
    "próprios). São compatíveis, mas não idênticas; a analítica não é a nomenclatura oficial.")
