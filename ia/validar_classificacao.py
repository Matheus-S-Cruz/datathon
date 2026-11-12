"""Validação da classificação de CBOs feita pelo LLM.

1. Cobertura: todo CBO do CAGED tem classificação, só com valores permitidos.
2. Coerência com a estrutura oficial da CBO 2002 (1º dígito = Grande Grupo):
   ex.: ENG_TI deveria vir do GG 2 (profissionais de nível superior), TEC_IND do GG 3.
   Divergências não são necessariamente erros — são a lista para revisão humana.
3. Amostra aleatória estratificada (seed fixa) para a equipe revisar à mão
   -> grava ia/amostra_revisao.csv com a coluna `correto` em branco (preencher S/N).
4. (Opcional) Concordância com outra classificação (ex.: rodada via API):
       python ia/validar_classificacao.py ia/cbo_macrofamilias_api.csv

Uso (raiz do repositório):  python ia/validar_classificacao.py
"""
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
CLASSIF = RAIZ / "ia" / "cbo_macrofamilias.csv"
ENTRADA = RAIZ / "ia" / "cbos_para_classificar.csv"

# Grande Grupo CBO esperado para cada macrofamília (o que é "coerente")
GG_ESPERADO = {
    "ENG_TI": {"2"},
    "TEC_IND": {"3"},
    "GESTAO": {"1", "3", "4", "5", "6", "7", "8", "9"},  # supervisores existem em vários GGs
    "OP_METAL": {"7", "8"},
    "OP_TEXTIL": {"7", "8"},
    "OP_ALIM": {"7", "8"},
    "OP_OUTRAS": {"7", "8"},
    "CONSTR": {"7"},
    "MANUT": {"9", "7"},
    "AGRO": {"6"},
}


def main():
    c = pd.read_csv(CLASSIF, dtype=str)
    e = pd.read_csv(ENTRADA, dtype={"cbo": str})
    df = e.merge(c, on="cbo", how="left")

    print("=== 1. Cobertura")
    sem = df["macrofamilia"].isna().sum()
    print(f"CBOs no CAGED: {len(e)} | classificados: {len(c)} | sem classificação: {sem}")

    print("\n=== Distribuição (CBOs e movimentações)")
    dist = df.groupby("macrofamilia").agg(cbos=("cbo", "size"), movs=("movs", "sum"))
    dist["%movs"] = (dist["movs"] / dist["movs"].sum() * 100).round(1)
    print(dist.sort_values("movs", ascending=False).to_string())

    print("\n=== 2. Coerência com o Grande Grupo da CBO 2002")
    df["gg"] = df["cbo"].str[0]
    df["coerente"] = [
        gg in GG_ESPERADO.get(m, {gg}) for gg, m in zip(df["gg"], df["macrofamilia"])
    ]
    pct = df["coerente"].mean() * 100
    pct_mov = (df["coerente"] * df["movs"]).sum() / df["movs"].sum() * 100
    print(f"Coerentes: {pct:.1f}% dos CBOs | {pct_mov:.1f}% das movimentações")
    div = df[~df["coerente"]].sort_values("movs", ascending=False)
    print(f"Divergentes (para revisão): {len(div)} — maiores por volume:")
    print(div[["cbo", "titulo", "macrofamilia", "movs"]].head(15).to_string(index=False))

    print("\n=== 3. Amostra para revisão humana")
    # até 4 CBOs sorteados por macrofamília (embaralha com seed fixa e pega os 4 primeiros)
    amostra = (
        df.sample(frac=1, random_state=42)
        .groupby("macrofamilia")
        .head(4)
        .sort_values(["macrofamilia", "cbo"])
        .loc[:, ["cbo", "titulo", "macrofamilia", "nivel", "industrial", "movs"]]
    )
    amostra["correto"] = ""
    destino = RAIZ / "ia" / "amostra_revisao.csv"
    if destino.exists():
        print(f"{destino.name} já existe — mantido (pode conter a revisão da equipe).")
    else:
        amostra.to_csv(destino, index=False)
        print(f"{len(amostra)} CBOs gravados em {destino.name} — preencher a coluna `correto` (S/N).")

    if len(sys.argv) > 1:
        print("\n=== 4. Concordância com outra classificação")
        o = pd.read_csv(sys.argv[1], dtype=str)
        m = c.merge(o, on="cbo", suffixes=("", "_outra"))
        conc = (m["macrofamilia"] == m["macrofamilia_outra"]).mean() * 100
        print(f"Concordância de macrofamília: {conc:.1f}% em {len(m)} CBOs")


if __name__ == "__main__":
    main()
