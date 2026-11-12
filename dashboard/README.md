# Dashboard Analítico (Entregável 2)

Painel interativo em **Streamlit** que responde à pergunta central do desafio, consumindo
as tabelas-base geradas pelo pipeline (`outputs/*.parquet`).

## Como executar

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

Abre em `http://localhost:8501`.

> As tabelas em `outputs/` já estão versionadas, então o dashboard roda direto.
> Se quiser regenerá-las, execute antes o notebook `notebooks/01_pipeline_caged_sc.ipynb`.

## O que o painel mostra

**KPIs (topo):** saldo de vagas, admissões, desligamentos, salário médio e nº de municípios —
todos reagem aos filtros.

**Filtros (barra lateral):** apenas setores industriais (B, C, D, F), seleção de setores (CNAE)
e população mínima do município.

**Abas de storytelling:**
- 🗺️ **Território** — **mapa de calor interativo de SC** (bolhas por município com hover
  mostrando cidade, saldo, rotatividade, salário e população; verde = expansão, vermelho =
  apagão), top municípios em expansão e em apagão (saldo por 10 mil hab.) e dispersão
  saldo × giro (identifica rotatividade).
- 🏭 **Setores** — saldo por setor (CNAE), destacando os industriais, e os maiores polos
  industriais (município × setor).
- 🎓 **Renda × Escolaridade** — salário por grau de instrução (compressão salarial),
  admitidos vs. desligados por escolaridade, e dispersão municipal salário × escolaridade.
- 🤖 **Macrofamílias (IA)** — saldo por macrofamília ocupacional (agrupamento de CBOs),
  revelando se o apagão é operacional ou técnico/engenharia.

Gráficos: **barras** (território/setor), **dispersão** (renda × escolaridade, rotatividade)
e tabelas de apoio — cobrindo os tipos exigidos pelo guia.
