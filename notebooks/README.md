# Notebooks — Pipeline de Dados (Entregável 1)

## `01_pipeline_caged_sc.ipynb`

Pipeline completo do desafio, do carregamento das bases à exportação das tabelas-base
que alimentam o dashboard. Etapas:

1. Ingestão e validação (CAGED Parquet + municípios + dicionário)
2. Limpeza, tipagem e filtragem de exclusões (MOV × EX)
3. Cruzamento CAGED × municípios (código do município)
4. Métricas: saldo, **saldo por 10.000 hab.**, giro/turnover
5. Agregações territorial, setorial e socioeconômica (renda × escolaridade)
6. Enriquecimento com IA — agrupamento de CBOs em macrofamílias
   (baseline determinístico por Grande Grupo CBO + refino opcional via LLM)
7. Exportação das tabelas para `../outputs/`

### Como executar

```bash
pip install pandas pyarrow openpyxl
# opcional, para gráficos/IA:
pip install plotly openai

jupyter notebook notebooks/01_pipeline_caged_sc.ipynb
# ou, de ponta a ponta:
jupyter nbconvert --to notebook --execute --inplace notebooks/01_pipeline_caged_sc.ipynb
```

O passo de IA só chama o LLM se `OPENAI_API_KEY` estiver definida; caso contrário usa o
baseline determinístico (não depende de rede).

### Saídas geradas em `outputs/`
- `agg_municipio.parquet` — saldo, saldo/10k hab., giro e socioeconômico por município
- `agg_setor.parquet` — saldo e perfil por setor (CNAE), com flag industrial
- `agg_municipio_setor.parquet` — cruzamento território × setor
- `perfil_adm_desl.parquet` — admitidos vs. desligados por escolaridade
- `salario_por_grau.parquet` — salário médio por grau de instrução
- `macrofamilias_cbo.parquet` — saldo e perfil por macrofamília ocupacional
