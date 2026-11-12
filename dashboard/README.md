# Dashboard Analítico (Entregável 2)

Painel em **Streamlit** que responde à pergunta central do desafio.

```bash
pip install -r requirements.txt      # na raiz do repositório
streamlit run dashboard/app.py
```

Abre em `http://localhost:8501`. As tabelas em `outputs/` já estão versionadas; para regerá-las,
execute o notebook `notebooks/01_pipeline_caged_sc.ipynb`.

## Navegação

### 1. Visualizações Essenciais — *Painel principal*
- **Capa: mapa 3D das 6 mesorregiões de SC.** Clique numa região: ela sobe e **todo o painel
  passa a mostrar só aquela região** (clique de novo ou em "Ver Santa Catarina inteira" para voltar).
- **KPIs:** saldo de vagas, saldo por 10 mil hab., admissões, desligamentos, % de desligamentos
  **a pedido** e salário de admissão (vs. desligados), mais um **ponto de atenção** automático
  (macrofamília industrial que mais desliga em relação ao que contrata).
- **Abas:** 🗺️ Território (mapa de bolhas por município, rankings, expansão × rotatividade) ·
  🏭 Setores (saldo por CNAE, polos industriais) · 🎓 Renda × Escolaridade (salário de quem entra ×
  quem sai por escolaridade, municípios salário × anos de estudo) · 🤖 Macrofamílias (IA).
- Filtro lateral: apenas setores industriais (CNAE B, C, D, F).

### 2. Consulta e Exploração dos Dados — *CAGED Explorer*
Páginas para ver, consultar e conferir as bases: visão geral, explorador do CAGED (filtros,
paginação, exportação), municípios, dicionário de dados, resultados da auditoria (31 constatações
recalculadas), exploração estatística e relações territoriais/setoriais. Usa DuckDB direto sobre o
Parquet. Guia de uso: [`docs/guia_explorador.md`](../docs/guia_explorador.md).

### 3. Visualizações Complementares — *Gráficos complementares*
Sazonalidade (saldo mensal), motivo dos desligamentos (a pedido × demissão), salário de admissão ×
desligamento por macrofamília, mapa de calor macrofamília × mesorregião e contexto socioeconômico
(PIB per capita, IDHM).

## Arquivos

| Arquivo | Papel |
|---|---|
| `app.py` | Entrada e navegação |
| `paginas/painel_principal.py`, `paginas/complementares.py` | Visualizações |
| `mapa3d.py` | Componente do mapa 3D (SVG + `st.components.v2`, sem bibliotecas externas) |
| `dados.py` | Carga das tabelas de `outputs/` e indicadores por recorte |
| `views/`, `services/`, `components/`, `formatting.py` | CAGED Explorer |
