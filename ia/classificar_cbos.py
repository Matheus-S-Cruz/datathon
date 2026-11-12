"""Classifica os CBOs do CAGED-SC em macrofamílias usando um LLM (Claude, via API).

Reprodução da etapa de enriquecimento com IA. O resultado versionado no repositório
(`ia/cbo_macrofamilias.csv`) foi gerado com este mesmo prompt
(`ia/prompt_classificacao_cbo.md`), em 5 lotes, pelo modelo Claude Opus 5.5.

Uso (a partir da raiz do repositório):
    pip install anthropic pandas
    export ANTHROPIC_API_KEY=...      # ou `ant auth login`
    python ia/classificar_cbos.py      # grava ia/cbo_macrofamilias_api.csv

Depois, compare com o arquivo versionado:
    python ia/validar_classificacao.py ia/cbo_macrofamilias_api.csv
"""
import argparse
import io
from pathlib import Path

import anthropic
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROMPT_MD = RAIZ / "ia" / "prompt_classificacao_cbo.md"
ENTRADA = RAIZ / "ia" / "cbos_para_classificar.csv"

MACROFAMILIAS = {
    "OP_METAL", "OP_TEXTIL", "OP_ALIM", "OP_OUTRAS", "CONSTR", "MANUT", "LOGIST",
    "TEC_IND", "ENG_TI", "GESTAO", "ADM", "COMERCIO", "SERV", "AGRO", "NAO_CLASSIFICADO",
}
NIVEIS = {"OPERACIONAL", "TECNICO", "SUPERIOR", "GESTAO", "NA"}


def carregar_prompt() -> str:
    texto = PROMPT_MD.read_text(encoding="utf-8")
    return texto.split("\n---\n", 1)[1].strip()  # tudo após o primeiro separador


def classificar_lote(client: anthropic.Anthropic, prompt: str, lote: pd.DataFrame) -> pd.DataFrame:
    lista = "\n".join(f"{r.cbo} | {r.titulo}" for r in lote.itertuples())
    with client.beta.messages.stream(
        model="claude-opus-5-5",
        max_tokens=64000,
        output_config={"effort": "medium"},
        # se o modelo recusar, a API repete a chamada num modelo de fallback
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": prompt.replace("{LISTA}", lista)}],
    ) as stream:
        resposta = stream.get_final_message()

    if resposta.stop_reason == "refusal":
        raise RuntimeError(f"Modelo recusou o lote: {resposta.stop_details}")
    if resposta.stop_reason == "max_tokens":
        raise RuntimeError("Resposta truncada (max_tokens) — reduza o tamanho do lote.")

    texto = "".join(b.text for b in resposta.content if b.type == "text").strip()
    texto = texto.removeprefix("```csv").removeprefix("```").removesuffix("```").strip()
    saida = pd.read_csv(io.StringIO(texto), sep=";", dtype=str)

    # validação: mesmos códigos, mesma ordem, valores permitidos
    if saida["cbo"].tolist() != lote["cbo"].tolist():
        raise ValueError("Saída do LLM não corresponde aos CBOs do lote.")
    invalidos = saida[
        ~saida["macrofamilia"].isin(MACROFAMILIAS)
        | ~saida["nivel"].isin(NIVEIS)
        | ~saida["industrial"].isin({"S", "N"})
    ]
    if not invalidos.empty:
        raise ValueError(f"Valores fora do domínio:\n{invalidos}")
    return saida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lotes", type=int, default=5)
    ap.add_argument("--saida", default=str(RAIZ / "ia" / "cbo_macrofamilias_api.csv"))
    args = ap.parse_args()

    prompt = carregar_prompt()
    cbos = pd.read_csv(ENTRADA, dtype={"cbo": str})
    tamanho = -(-len(cbos) // args.lotes)
    client = anthropic.Anthropic()

    partes = []
    for i in range(args.lotes):
        lote = cbos.iloc[i * tamanho:(i + 1) * tamanho]
        print(f"Lote {i + 1}/{args.lotes}: {len(lote)} CBOs ...")
        partes.append(classificar_lote(client, prompt, lote))

    resultado = pd.concat(partes, ignore_index=True)
    resultado.to_csv(args.saida, index=False)
    print(f"OK — {len(resultado)} CBOs classificados em {args.saida}")


if __name__ == "__main__":
    main()
