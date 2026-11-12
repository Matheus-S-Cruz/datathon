# Dados — Datathon CDIA 2026

Esta pasta contém as bases do desafio, separadas por papel:

```text
data/
├── raw/          # dados brutos fornecidos pela organização (nunca editar)
├── reference/    # tabelas de apoio: dicionário e dados municipais
└── processed/    # saídas do pipeline (gerado pelo código; NÃO versionado)
```

## Arquivos

| Arquivo | Origem | Tamanho | Conteúdo |
|---|---|---|---|
| `raw/Novo_Caged_MOV_Limpo.parquet` | Organização do Datathon (CSV no Google Drive), convertido pela equipe | 43,9 MB | Microdados de movimentações do Novo CAGED em SC. 3.397.416 registros, 30 colunas, todas como texto. |
| `reference/Municipios_SC_limpo.csv` | Organização do Datathon (dados IBGE e outras fontes, ver rodapé do próprio arquivo) | 41 KB | 295 municípios de SC + 1 linha de rodapé com notas e fontes (HTML). |
| `reference/Dicionario_de_dados.xlsx` | Organização do Datathon (layout oficial do Novo CAGED) | 294 KB | Aba `Layout` com as variáveis e 22 abas com as tabelas de códigos. |

Fonte original do CSV (opcional, ~395 MB, não versionado):
<https://drive.google.com/file/d/1qjMeL681PQpPUERMOL1y_7vY18mugbbm/view>.
O link é público (verificado em 10/11/2026). Se for baixado, salve em `data/raw/Novo_Caged_MOV_Limpo.csv`;
o `.gitignore` impede que ele seja enviado ao GitHub.

## Por que Parquet?

O CSV original tem ~395 MB, acima do limite de 100 MB por arquivo do GitHub. A equipe
(commit `429625d`) converteu para **Parquet com compressão zstd** (~42 MB), mantendo todas as
colunas como **texto** para preservar fidelidade ao original. A conversão foi validada por
_round-trip_ pelo autor do commit.

Vantagens:

- formato colunar: lê-se só as colunas necessárias;
- muito mais rápido que reprocessar 3,4 milhões de linhas de CSV;
- consultável diretamente com DuckDB, sem carregar tudo na memória.

## Como ler

Prefira DuckDB para agregações (lê o arquivo sob demanda):

```python
import duckdb
from src.config import CAGED_PARQUET

con = duckdb.connect()
con.execute(f"CREATE VIEW caged AS SELECT * FROM read_parquet('{CAGED_PARQUET.as_posix()}')")
con.execute("""
    SELECT seção, sum(saldomovimentação::INT) AS saldo
    FROM caged GROUP BY 1 ORDER BY saldo DESC
""").df()
```

Com pandas/polars, carregue **apenas as colunas necessárias**:

```python
import pandas as pd
cols = ["competênciadec", "município", "seção", "saldomovimentação",
        "graudeinstrução", "salário", "cbo2002ocupação"]
df = pd.read_parquet(CAGED_PARQUET, columns=cols)
```

## Cuidados obrigatórios ao usar os dados

Detalhes em [`docs/dicionario_analitico.md`](../docs/dicionario_analitico.md).

- **Tudo é texto**: converta tipos no pipeline. `salário`, `valorsaláriofixo` e `horascontratuais`
  usam vírgula decimal (`"2018,00"`); `idade` vem como `"40.0"` e tem 2.202 valores vazios.
- **Município**: o CAGED usa código de **6 dígitos** (`420005`); o CSV de municípios usa o código
  IBGE de **7 dígitos** (`4200051`). A junção é feita com os 6 primeiros dígitos do IBGE.
- **Rodapé no CSV de municípios**: a última linha não é município (contém HTML de notas/fontes)
  e a coluna `Unnamed: 14` é vazia (vírgula sobrando no fim de cada linha).
- **Valores ausentes no CSV de municípios** aparecem como `-` (ex.: IDHM, mortalidade infantil).
- **Colunas de índice**: `Unnamed: 0.1` e `Unnamed: 0` são artefatos de exportação e podem ser descartadas.
- **Exclusões**: as colunas `competênciaexc` e `indicadordeexclusão`, previstas no dicionário,
  **não existem** nesta base. Ver `docs/diagnostico_inicial.md`, seção D.

## Como o Parquet foi gerado (reprodutibilidade)

```python
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

df = pd.read_csv("Novo_Caged_MOV_Limpo.csv", sep=";", dtype=str,
                 keep_default_na=False, na_values=[])
table = pa.Table.from_pandas(df, preserve_index=False)
pq.write_table(table, "Novo_Caged_MOV_Limpo.parquet",
               compression="zstd", compression_level=19, use_dictionary=True)
```
