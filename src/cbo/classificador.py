"""Apoio à classificação de ocupações (etapa 3.5b) — preparação, SEM chamada paga.

Arquitetura desacoplada do provedor (ver docs/cbo_classificacao.md §2.3): a aplicação fala com a
interface `Provider`; trocar de provedor (baseline determinístico, OpenAI, outro) não muda o resto.

Nesta etapa só existe o `BaselineProvider` — determinístico, sem rede e sem custo. Ele reproduz o
agrupamento que o pipeline já faz (macrofamília = 1º dígito do CBO, grupos 7 e 8 fundidos). Um provedor
de LLM pode ser adicionado depois implementando a mesma interface, e só roda com chave e AUTORIZAÇÃO
explícita de custo (etapa 3.5c). Nenhuma classificação daqui substitui os códigos oficiais.

Preparar a amostra e rodar o baseline (sem custo):

    python -m src.cbo.classificador
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd

from src.cbo.hierarquia import GRANDES_GRUPOS, hierarquia, normaliza
from src.config import ROOT

# As 9 macrofamílias analíticas do projeto (taxonomia fechada). Mesmo mapa do pipeline (seção 8 do
# notebook): os grandes grupos 7 e 8 formam a macrofamília operacional. A IA, quando existir, só pode
# escolher valores desta taxonomia — proibido criar categoria nova (§7.3 do plano).
MACROFAMILIAS: dict[str, str] = {
    "0": "Forças Armadas / Segurança",
    "1": "Dirigentes e Gerentes",
    "2": "Profissionais de nível superior (Técnico/Engenharia)",
    "3": "Técnicos de nível médio",
    "4": "Trabalhadores de apoio administrativo",
    "5": "Serviços, vendas e comércio",
    "6": "Agropecuários e florestais",
    "7": "Produção de bens e serviços industriais (Operacional)",
    "8": "Produção de bens e serviços industriais (Operacional)",
    "9": "Manutenção e reparação",
}
TAXONOMIA = tuple(dict.fromkeys(MACROFAMILIAS.values()))  # valores distintos, na ordem


@dataclass(frozen=True)
class Item:
    """Uma ocupação a classificar."""
    cbo: str
    ocupacao: str
    grande_grupo_oficial: str
    grande_grupo_nome: str
    volume: int = 0


@dataclass(frozen=True)
class Sugestao:
    """Uma sugestão de classificação, com rastreabilidade e espaço para a decisão humana."""
    cbo: str
    ocupacao_original: str
    codigo_original: str
    grupo_oficial_sugerido: str
    justificativa: str
    confianca: str                     # alta / média / baixa
    decisao_humana: str = ""           # aprovado / ajustado / rejeitado (preenchido na revisão)
    resultado_final: str = ""          # grupo após a decisão humana
    revisado_por: str = ""


class Provider(Protocol):
    """Contrato de qualquer classificador. A aplicação só conhece esta interface."""

    nome: str

    def classificar(self, lote: list[Item]) -> list[Sugestao]:
        ...


class BaselineProvider:
    """Classificador determinístico: macrofamília pelo 1º dígito do CBO. Sem rede, sem custo.

    É a mesma regra do pipeline; serve de referência e de valor padrão quando não há IA. A confiança é
    sempre "alta" porque é determinístico — não há incerteza de modelo."""

    nome = "baseline-deterministico"

    def classificar(self, lote: list[Item]) -> list[Sugestao]:
        out = []
        for it in lote:
            macro = MACROFAMILIAS.get(it.cbo[0], "Não classificado")
            out.append(Sugestao(
                cbo=it.cbo, ocupacao_original=it.ocupacao, codigo_original=it.cbo,
                grupo_oficial_sugerido=macro,
                justificativa=f"1º dígito do CBO = {it.cbo[0]} ({it.grande_grupo_nome}).",
                confianca="alta"))
        return out


def amostra_industrial(top_cobertura: float = 0.95, limite: int | None = None) -> pd.DataFrame:
    """Amostra de ocupações da seção C (Transformação) para o piloto.

    Usa os volumes de movimentação por CBO na seção C, lidos do Parquet bruto via DuckDB (só a coluna
    necessária). Seleciona as ocupações mais frequentes que cobrem `top_cobertura` do volume. Se a base
    não estiver disponível, cai para toda a hierarquia (sem volume), para a preparação não travar."""
    h = hierarquia()
    try:
        import duckdb

        from src.config import CAGED_PARQUET
        con = duckdb.connect(":memory:")
        vol = con.execute(f"""
            SELECT lpad(trim("cbo2002ocupação"), 6, '0') AS cbo, count(*) AS volume
            FROM read_parquet('{CAGED_PARQUET.as_posix()}')
            WHERE trim("seção") = 'C'
            GROUP BY 1 ORDER BY volume DESC
        """).df()
    except Exception:
        vol = pd.DataFrame({"cbo": h["cbo"], "volume": 0})

    df = vol.merge(h, on="cbo", how="left")
    df["ocupacao"] = df["ocupacao"].fillna("(sem título no dicionário)")
    df["grande_grupo"] = df["grande_grupo"].fillna(df["cbo"].str[:1])
    df["grande_grupo_nome"] = df["grande_grupo_nome"].fillna(
        df["grande_grupo"].map(GRANDES_GRUPOS)).fillna("(desconhecido)")
    if df["volume"].sum() > 0:
        df["cobertura"] = df["volume"].cumsum() / df["volume"].sum()
        corte = df[df["cobertura"] <= top_cobertura]
        df = df.head(max(len(corte), 1))
    if limite:
        df = df.head(limite)
    return df.reset_index(drop=True)


def monta_lote(df: pd.DataFrame) -> list[Item]:
    return [Item(cbo=normaliza(r.cbo), ocupacao=r.ocupacao, grande_grupo_oficial=r.grande_grupo,
                 grande_grupo_nome=r.grande_grupo_nome, volume=int(r.volume)) for r in df.itertuples()]


def para_frame(sugestoes: list[Sugestao]) -> pd.DataFrame:
    return pd.DataFrame([s.__dict__ for s in sugestoes])


def prepara_piloto(provider: Provider | None = None, limite: int = 150, destino=None) -> pd.DataFrame:
    """Prepara a amostra e roda o provider (baseline por padrão). Grava o CSV de revisão humana."""
    provider = provider or BaselineProvider()
    df = amostra_industrial(limite=limite)
    sugestoes = provider.classificar(monta_lote(df))
    out = para_frame(sugestoes)
    if destino is None:
        pasta = ROOT / "reports" / "ia"
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / "piloto_saida.csv"
    out.to_csv(destino, index=False)
    return out


if __name__ == "__main__":
    df = prepara_piloto()
    print(f"Piloto preparado com o provedor baseline: {len(df)} ocupações.")
    print("Taxonomia fechada (9 macrofamílias):")
    for t in TAXONOMIA:
        print("  -", t)
