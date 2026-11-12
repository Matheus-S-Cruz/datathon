"""Enriquecimento com bases públicas do IBGE (APIs oficiais, sem chave de acesso).

Baixa e grava em `data/external/` quatro bases que complementam o CSV municipal
fornecido pela organização (que já traz população, IDHM, PIB per capita etc.):

| Arquivo                         | Fonte (API IBGE)                                   | Para quê |
|---------------------------------|----------------------------------------------------|----------|
| ibge_regioes_sc.parquet         | Localidades v1 — municípios de SC                  | Agregar por região geográfica (imediata/intermediária, meso/microrregião) |
| ibge_cempre_2024.parquet        | SIDRA/Agregados 9509 — CEMPRE 2024                 | Estoque de assalariados: transforma o saldo do CAGED (fluxo) em taxa de crescimento |
| ibge_pib_municipal.parquet      | SIDRA/Agregados 5938 — PIB 2023 + VAB por atividade 2021 | Peso da indústria no valor adicionado de cada município |
| ibge_malha_sc.geojson           | Malhas v3 — limites municipais de SC               | Mapa coroplético (polígonos), em vez de só centroides |

Os arquivos são versionados: o pipeline e o dashboard funcionam sem internet.
Rode este script apenas para atualizar as bases:

    python -m src.enrichment.ibge
"""

from __future__ import annotations

import gzip
import json
import time
import urllib.request
from datetime import date

import pandas as pd

from src.config import EXTERNAL_DIR

UF_SC = 42
API = "https://servicodados.ibge.gov.br/api"
CEMPRE_ANO = "2024"
PIB_ANO = "2023"
# A abertura do VAB por atividade (indústria, serviços...) só está publicada por município
# até 2021 na tabela 5938 (2022 e 2023 aparecem como "..." = não disponível).
VAB_ANO = "2021"
GZIP_MAGIC = bytes([0x1F, 0x8B])  # algumas respostas da API vêm compactadas

CEMPRE_VARS = {  # agregado 9509
    "706": "unidades_locais",
    "367": "empresas",
    "707": "pessoal_ocupado",
    "708": "assalariados",
    "10143": "salario_medio_cempre",  # salário médio mensal em reais
}
PIB_VARS = {"37": "pib"}  # agregado 5938, mil reais
VAB_VARS = {  # agregado 5938, mil reais
    "498": "vab_total",
    "513": "vab_agropecuaria",
    "517": "vab_industria",
    "6575": "vab_servicos",
    "525": "vab_adm_publica",
}


def _get(url: str, retries: int = 3) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "datathon-caged-sc/1.0"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = resp.read()
                return gzip.decompress(body) if body[:2] == GZIP_MAGIC else body
        except OSError:
            if attempt == retries - 1:
                raise
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("inalcançável")


def _agregado(agregado: int, periodo: str, variaveis: dict[str, str]) -> pd.DataFrame:
    """Valores de um agregado SIDRA para todos os municípios de SC (formato largo)."""
    ids = "|".join(variaveis)
    url = f"{API}/v3/agregados/{agregado}/periodos/{periodo}/variaveis/{ids}?localidades=N6[N3[{UF_SC}]]"
    data = json.loads(_get(url))
    cols: dict[str, dict[str, float | None]] = {}
    for var in data:
        name = variaveis[var["id"]]
        for serie in var["resultados"][0]["series"]:
            raw = serie["serie"].get(periodo)
            # SIDRA usa '-', '...', 'X' para zero, não disponível e sigilo
            value = pd.to_numeric(raw, errors="coerce")
            cols.setdefault(name, {})[serie["localidade"]["id"]] = value
    df = pd.DataFrame(cols)
    df.index.name = "codigo_ibge"
    return df.reset_index()


def regioes() -> pd.DataFrame:
    data = json.loads(_get(f"{API}/v1/localidades/estados/{UF_SC}/municipios"))
    rows = []
    for m in data:
        micro, imediata = m["microrregiao"], m["regiao-imediata"]
        rows.append({
            "codigo_ibge": str(m["id"]),
            "nome_ibge": m["nome"],
            "microrregiao": micro["nome"],
            "mesorregiao": micro["mesorregiao"]["nome"],
            "regiao_imediata": imediata["nome"],
            "regiao_intermediaria": imediata["regiao-intermediaria"]["nome"],
        })
    return pd.DataFrame(rows)


def cempre() -> pd.DataFrame:
    return _agregado(9509, CEMPRE_ANO, CEMPRE_VARS)


def pib_municipal() -> pd.DataFrame:
    pib = _agregado(5938, PIB_ANO, PIB_VARS).rename(columns={"pib": f"pib_{PIB_ANO}"})
    vab = _agregado(5938, VAB_ANO, VAB_VARS)
    vab["part_industria_vab"] = vab["vab_industria"] / vab["vab_total"]
    vab = vab.rename(columns={c: f"{c}_{VAB_ANO}" for c in vab.columns if c != "codigo_ibge"})
    return pib.merge(vab, on="codigo_ibge", how="outer")


def malha() -> dict:
    url = (f"{API}/v3/malhas/estados/{UF_SC}?formato=application/vnd.geo%2Bjson"
           "&intrarregiao=municipio&qualidade=intermediaria")
    return json.loads(_get(url))


def main() -> None:
    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    out = {
        "ibge_regioes_sc.parquet": regioes(),
        f"ibge_cempre_{CEMPRE_ANO}.parquet": cempre(),
        "ibge_pib_municipal.parquet": pib_municipal(),
    }
    for name, df in out.items():
        assert len(df) == 295, f"{name}: esperados 295 municípios, vieram {len(df)}"
        df.to_parquet(EXTERNAL_DIR / name, index=False)
        print(f"{name}: {df.shape}")

    geo = malha()
    assert len(geo["features"]) == 295, "malha: esperados 295 polígonos"
    (EXTERNAL_DIR / "ibge_malha_sc.geojson").write_text(json.dumps(geo, separators=(",", ":")), encoding="utf-8")
    print(f"ibge_malha_sc.geojson: {len(geo['features'])} polígonos")

    meta = {
        "baixado_em": date.today().isoformat(),
        "fontes": {
            "regioes": f"{API}/v1/localidades/estados/{UF_SC}/municipios",
            "cempre": f"IBGE, Cadastro Central de Empresas (CEMPRE) {CEMPRE_ANO} — SIDRA tabela 9509",
            "pib": (f"IBGE, PIB dos Municípios — SIDRA tabela 5938 (mil reais, preços correntes): PIB {PIB_ANO}; "
                    f"VAB por atividade {VAB_ANO}, último ano publicado por município"),
            "malha": f"{API}/v3/malhas/estados/{UF_SC} (intrarregiao=municipio)",
        },
    }
    (EXTERNAL_DIR / "fontes.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
