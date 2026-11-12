# Notebooks — Pipeline de Dados (Entregável 1)

## `01_pipeline_caged_sc.ipynb`

Pipeline completo do desafio, do carregamento das bases à exportação das tabelas-base
que alimentam o dashboard. Etapas:

1. Ingestão e validação (CAGED Parquet + municípios + dicionário)
2. Limpeza, tipagem e filtragem de exclusões (MOV × EX)
3. Cruzamento CAGED × municípios (código do município)
4. Métricas: saldo, **saldo por 10.000 hab.**, giro/turnover
5. Agregações territorial, setorial e socioeconômica (renda × escolaridade)
6. Enriquecimento com IA — 2.207 CBOs classificados por LLM em 14 macrofamílias
   (resultado versionado em `ia/cbo_macrofamilias.csv`; prompt, script e validação em `ia/`)
7. Exportação das tabelas para `../outputs/`

### Como executar

```bash
pip install -r requirements.txt

jupyter notebook notebooks/01_pipeline_caged_sc.ipynb
# ou, de ponta a ponta:
jupyter nbconvert --to notebook --execute --inplace notebooks/01_pipeline_caged_sc.ipynb
```

O notebook **não chama API**: a etapa de IA carrega a classificação já gerada pelo LLM
(`ia/cbo_macrofamilias.csv`). Para refazê-la: `python ia/classificar_cbos.py` (requer
`ANTHROPIC_API_KEY`). O notebook é gerado por `_build_notebook.py` — edite o script e rode
`python notebooks/_build_notebook.py` em vez de editar o `.ipynb` à mão.

### Saídas geradas em `outputs/`
- `agg_municipio.parquet` — saldo, saldo/10k hab., giro e socioeconômico por município
- `agg_setor.parquet` — saldo e perfil por setor (CNAE), com flag industrial
- `agg_municipio_setor.parquet` — cruzamento território × setor
- `perfil_adm_desl.parquet` — admitidos vs. desligados por escolaridade
- `salario_por_grau.parquet` — salário médio por grau de instrução
- `macrofamilias_cbo.parquet` — saldo e perfil por macrofamília ocupacional (IA)
- `agg_mesorregiao.parquet` — indicadores das 6 mesorregiões (mapa do dashboard)
- `macrofamilia_mesorregiao.parquet` — macrofamília × mesorregião
- `cubo_movimentacoes.parquet` — somas por município × CNAE × macrofamília × nível × tipo
- `municipios.parquet` — municípios com população, IDHM, PIB e mesorregião
