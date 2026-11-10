# Dataset — Datathon CDIA 2026 (Raio-X do Mercado de Trabalho Industrial em SC)

Esta pasta contém as bases de dados do desafio.

## Arquivos

| Arquivo | Descrição | Formato |
|---------|-----------|---------|
| `Novo_Caged_MOV_Limpo.parquet` | Microdados do Novo CAGED (movimentações) dos últimos 12 meses em Santa Catarina. **3.397.416 registros**, 30 colunas. | Parquet (compressão `zstd`) |
| `Municipios_SC_limpo.csv` | Dados demográficos dos municípios de SC (cruzar via código do município). | CSV (`,`) |
| `Dicionario_de_dados.xlsx` | Definição e metadados de cada campo das bases. | XLSX |

## Por que Parquet?

O arquivo original `Novo_Caged_MOV_Limpo.csv` tem **~395 MB**, acima do limite de 100 MB por
arquivo do GitHub. Convertemos para **Parquet com compressão zstd**, reduzindo para **~42 MB**
sem perda de dados (conversão validada por _round-trip_).

Vantagens para a análise:
- Formato colunar e tipado, lido em uma linha por pandas/polars;
- Leitura muito mais rápida que reparsear 3,4 milhões de linhas de CSV;
- Permite carregar apenas as colunas necessárias.

## Como ler

```python
import pandas as pd

df = pd.read_parquet("dataset/Novo_Caged_MOV_Limpo.parquet")
print(df.shape)  # (3397416, 30)

# Carregar apenas algumas colunas (mais rápido / menos memória):
cols = ["competênciamov", "município", "seção", "saldomovimentação",
        "graudeinstrução", "salário", "cbo2002ocupação"]
df = pd.read_parquet("dataset/Novo_Caged_MOV_Limpo.parquet", columns=cols)
```

```python
# Alternativa com polars
import polars as pl
df = pl.read_parquet("dataset/Novo_Caged_MOV_Limpo.parquet")
```

## Observações sobre os dados

- Separador do CSV original: `;`. No CAGED, campos decimais (ex.: `salário`, `horascontratuais`,
  `valorsaláriofixo`) usam vírgula como separador decimal. Todas as colunas foram preservadas como
  **texto** no Parquet para manter fidelidade ao original; faça a conversão de tipos no pipeline
  conforme necessário.
- As colunas `Unnamed: 0.1` e `Unnamed: 0` são artefatos de índice do arquivo de origem e podem ser
  descartadas na etapa de limpeza.
- Chave de cruzamento com `Municipios_SC_limpo.csv`: código do município (`município`).

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
