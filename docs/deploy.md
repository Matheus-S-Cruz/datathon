# Deploy do dashboard — Streamlit Community Cloud

O dashboard é um app **Streamlit** (servidor Python de processo contínuo). A plataforma nativa e
gratuita para publicá-lo é o **Streamlit Community Cloud** (share.streamlit.io). **Não** use a Vercel:
ela é serverless (execuções curtas, sem processo persistente nem WebSocket) e não roda Streamlit.

## Arquivos que preparam o deploy

| Arquivo | Papel |
|---|---|
| `requirements.txt` | Dependências de **execução** do dashboard (enxuto: streamlit, plotly, duckdb, pyarrow, pandas, numpy, openpyxl). É o que o Streamlit Cloud instala. |
| `requirements-pipeline.txt` | Dependências só do pipeline/notebook (jupyter, polars, tabulate). **Não** entram no deploy. |
| `runtime.txt` | Versão do Python no deploy: `python-3.12`. |
| `.streamlit/config.toml` | Tema e configurações da interface. |
| `dashboard/app.py` | **Arquivo principal** (entry point) do app. |

Os dados já estão versionados no repositório (`data/raw/Novo_Caged_MOV_Limpo.parquet`, ~42 MB, e as
bases do IBGE em `data/external/`), então o app funciona no deploy sem baixar nada externo.

## Passo a passo da conexão

1. Garanta que o código a publicar está na branch desejada do GitHub (ex.: `main`).
2. Acesse **https://share.streamlit.io** e entre com a conta do GitHub (a dona do repositório).
3. Clique em **Create app** → **Deploy a public app from GitHub** (ou "Yup, I have an app").
4. Preencha:
   - **Repository:** `Matheus-S-Cruz/datathon`
   - **Branch:** `main`
   - **Main file path:** `dashboard/app.py`
   - **App URL:** (opcional) escolha um subdomínio, ex.: `raio-x-industrial-sc`.
5. (Opcional) Em **Advanced settings**, confirme **Python version 3.12**. Não há segredos a configurar:
   a prévia do assistente não usa chave de API.
6. Clique em **Deploy**. O Cloud instala o `requirements.txt` e sobe o app (leva alguns minutos no
   primeiro build).

Pronto: a URL pública fica no formato `https://<seu-subdominio>.streamlit.app`.

## Observações

- **Primeiro build** é o mais lento (instala as dependências e lê o Parquet de 42 MB). Depois, o app
  inicia rápido porque lê só agregados e usa cache.
- **Reimplantação:** cada push na branch publicada reimplanta automaticamente.
- **Recursos gratuitos:** o tier Community tem limite de memória (~1 GB). O app foi desenhado para isso
  (o CAGED não é carregado inteiro na memória; o DuckDB lê só o necessário do Parquet).
- **Sem segredos no repositório:** se um dia um provedor de IA real for plugado ao assistente, a chave
  deve ser adicionada em **App settings → Secrets** do Streamlit Cloud (nunca no código). Hoje não é
  necessário.
