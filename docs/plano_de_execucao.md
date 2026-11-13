# Plano de execução

Complementa o [`diagnostico_inicial.md`](diagnostico_inicial.md). Pensado para o prazo real do
evento: **Dia 1 (10/11)** e **Dia 2 (13/11, 08:30–11:40, pitches a partir das 10:00)**, com os dias
11 e 12 como janela de trabalho (a confirmar com a equipe).

---

## 1. Arquitetura técnica

```text
data/raw/*.parquet ──► [1] ingestão/tipagem ──► [2] limpeza ──► [3] junção ──► data/processed/caged_sc.parquet
                          (DuckDB, SQL)                          ▲                    │
data/reference/*.csv/.xlsx ──────────────────────────────────────┘                    │
data/reference/cbo_macrofamilias.csv ◄── [4] classificação IA + revisão humana        │
                                                │                                      ▼
                                                └──────────────► [6] tabelas agregadas (data/processed/agg_*.parquet)
                                                                               │
                                                                               ▼
                                                               [7] dashboard Streamlit + Plotly
```

| Escolha | Motivo |
|---|---|
| **DuckDB** para todo o processamento pesado | SQL direto sobre o Parquet, lê só as colunas usadas, roda local e no Colab, sem servidor. |
| **Pandas** só para tabelas já agregadas | Poucas linhas (municípios × setores), integração direta com Plotly/Streamlit. |
| **Parquet** como formato intermediário | Tipado, compacto, rápido. |
| **Dashboard lê apenas agregados** | Inicialização rápida; o painel não precisa abrir 3,4 milhões de linhas. |
| **Streamlit + Plotly** | Exigência de dashboard em Python; publicação gratuita no Streamlit Community Cloud. |
| **IA via chat gratuito, com entrada/saída em arquivos** | Sem custo, sem chave de API no repositório e com rastreabilidade. API só com autorização e orçamento. |
| Polars | Opcional; DuckDB já cobre a necessidade. Não introduzir os dois no mesmo passo. |

**Memória**: nunca usar `pd.read_parquet(...)` sem `columns=`. Toda agregação sobre o CAGED é SQL no DuckDB.

**Colab**: clonar o repositório, `pip install -r requirements.txt`, executar a partir da raiz
(os caminhos vêm de `src/config.py`).

### Estrutura alvo do repositório

```text
context/                 # regras do desafio (português)
  originais/             # .docx e .pptx oficiais
data/
  raw/                   # CAGED (Parquet) — nunca editar
  reference/             # dicionário, municípios e, depois, cbo_macrofamilias.csv e regiões
  processed/             # gerado; não versionado
docs/                    # diagnóstico, dicionário analítico, plano, metodologia
notebooks/               # notebook de entrega (pipeline narrado) — etapa 10
reports/                 # perfil das bases, prompts e saídas da IA, figuras do pitch
src/
  config.py              # caminhos
  validation/            # perfil e checagens
  preprocessing/         # tipagem, limpeza, junção — etapa 1–3
  enrichment/            # CBO → macrofamília — etapa 4
  analytics/             # indicadores e agregados — etapa 6
dashboard/               # app Streamlit — etapa 7
```

Pastas só serão criadas quando houver conteúdo real nelas.

---

## 2. Etapas

Cada etapa lista **pré-requisitos**, **entregáveis** e **critério de conclusão** ("pronto quando…").

### Etapa 1 — Ingestão e validação
- **Pré-requisitos**: respostas para E1 (exclusões) e E3 (competência) do diagnóstico, ou adoção das propostas padrão.
- **Entregáveis**: `src/preprocessing/load.py` com uma view DuckDB tipada (inteiros, decimais com vírgula convertidos, códigos com zero à esquerda, data da competência); checagens automáticas (contagem total, soma do saldo, domínios de códigos).
- **Pronto quando**: contagens batem com `reports/perfil_bases.md` (3.397.416 registros; saldo +41.482) e nenhuma conversão gera nulos inesperados.

### Etapa 2 — Limpeza e tratamento
- **Pré-requisitos**: etapa 1; decisões E5 (salários) e E6 (categorias).
- **Entregáveis**: regras de limpeza documentadas em `docs/metodologia.md` (tabela regra → motivo → registros afetados); colunas derivadas: `divisao_cnae`, `grande_grupo_cbo`, `escolaridade_ordem`, `salario_valido`, `tipo_desligamento_agrupado` (pedido / demissão / fim de contrato / outros).
- **Pronto quando**: cada registro removido ou marcado tem um motivo contabilizado; nada é descartado sem registro.

### Etapa 3 — Cruzamento das bases
- **Pré-requisitos**: etapa 2; decisão E4 (região) e E7 (população).
- **Entregáveis**: municípios limpos (sem rodapé, `-` → nulo, `cod6`); junção N:1; opcional: tabela de regiões do IBGE em `data/reference/` com fonte e data de acesso; `data/processed/caged_sc.parquet`.
- **Pronto quando**: contagem de linhas antes = depois da junção (LEFT JOIN não multiplica linhas), 0 municípios sem par, população presente em 100% dos registros.

### Etapa 4 — Agrupamento de CBOs com IA
- **Pré-requisitos**: etapa 2; decisão E8 (ferramenta) e E11 (taxonomia).
- **Estratégia** (rastreável e revisável):
  1. **Escopo**: CBOs com movimentação na seção C (1.467). Classificar individualmente os que somam a maior parte do volume (os 200 mais frequentes cobrem 89,9% da seção C; definir corte em ~95%) e agrupar a cauda pelo grande grupo da CBO.
  2. **Taxonomia fechada definida pela equipe antes do prompt** (8 a 12 macrofamílias). Exemplo para discussão, não validado: Engenharia e P&D · Técnicos industriais · Metalmecânica e usinagem · Têxtil e confecção · Alimentos e bebidas · Eletroeletrônica · Operação de máquinas e montagem (outros) · Manutenção industrial · Logística e movimentação · Qualidade e inspeção · Gestão e supervisão · Administrativo e apoio.
  3. **Nível de qualificação derivado da própria CBO**, não da IA: o 1º dígito (grande grupo) da CBO 2002 separa dirigentes, profissionais de nível superior, técnicos de nível médio, administrativos, serviços, agropecuária, produção industrial e manutenção (confirmar a estrutura na documentação oficial do MTE e citar a fonte).
  4. **Entrada para a IA**: CSV com `cbo`, `descricao` (aba `cbo2002ocupação` do dicionário), `grande_grupo`, volume. Lotes de ~100 linhas.
  5. **Saída exigida**: `cbo, macrofamilia, justificativa, confianca (alta/média/baixa)` — somente categorias da taxonomia; proibido criar categoria nova.
  6. **Revisão humana**: 100% dos itens de confiança baixa/média + amostra aleatória de 10% dos de alta; coluna `revisado_por`.
  7. **Versionamento**: `reports/ia/prompt_v1.md`, `reports/ia/saida_bruta_v1.csv`, `data/reference/cbo_macrofamilias.csv` (com `modelo`, `data`, `versao_prompt`).
- **Pronto quando**: 100% dos CBOs da seção C têm macrofamília; nenhuma categoria fora da taxonomia; itens de baixa confiança revisados.

### Etapa 5 — Análise exploratória
- **Pré-requisitos**: etapas 3 e 4.
- **Entregáveis**: notebook com as perguntas dos três eixos (ver diagnóstico, seção I), série mensal (sazonalidade), sensibilidade às regras de limpeza.
- **Pronto quando**: cada eixo tem 2–3 achados com número, gráfico e a limitação associada; achados separados entre fato e interpretação.

### Etapa 6 — Construção dos indicadores
- **Pré-requisitos**: etapa 5; limiares da matriz de sinais definidos pela equipe.
- **Entregáveis**: `src/analytics/indicators.py` com uma função/consulta por indicador; tabelas `data/processed/agg_*.parquet` nas granularidades do dashboard; `docs/metodologia.md` atualizado com fórmulas.
- **Pronto quando**: os totais dos agregados reconciliam com a base (soma dos saldos por município = saldo estadual); volume mínimo aplicado nos rankings.

### Etapa 7 — Dashboard
- **Pré-requisitos**: etapa 6; decisão sobre o mapa (malha IBGE disponível ou não).
- **Entregáveis**: `dashboard/app.py` (Streamlit) com as páginas do diagnóstico, seção G; `plotly` e `streamlit` habilitados no `requirements.txt`.
- **Pronto quando**: abre em menos de ~5 s lendo só agregados; ≥ 3 KPIs visíveis na primeira tela; filtros funcionam; limitações visíveis na página de diagnóstico; roda a partir de um clone limpo.

### Etapa 8 — Recomendações
- **Pré-requisitos**: etapas 5–7.
- **Entregáveis**: 3–5 recomendações, cada uma ligada a um indicador e a uma macrofamília/região (exigência do critério 4 da banca), com o público-alvo (indústria, federação, gestor público).
- **Pronto quando**: toda recomendação aponta para a evidência no dashboard e declara sua limitação.

### Etapa 9 — Pitch executivo (3 min)
- **Pré-requisitos**: etapa 8.
- **Entregáveis**: slides (exigidos pela apresentação oficial) com roteiro problema → método → 3 achados → recomendações → limites; ensaio cronometrado.
- **Pronto quando**: ensaio ≤ 2min50s; cada integrante sabe sua parte.

### Etapa 10 — Documentação e entrega
- **Pré-requisitos**: todas as anteriores.
- **Entregáveis**: notebook/script de pipeline documentado (do carregamento à exportação, incluindo prompts de IA); README final; repositório **público**; formulário de entrega enviado.
- **Pronto quando**: alguém de fora clona o repositório, instala `requirements.txt` e reproduz agregados e dashboard seguindo apenas o README.

---

## 3. Sugestão de divisão de trabalho (5 integrantes)

Seguindo a tabela de papéis do guia (técnico/dados × IA e negócios); a alocação de pessoas é decisão da equipe.

| Frente | Etapas | Perfil |
|---|---|---|
| Pipeline de dados | 1, 2, 3, 6 | Técnico |
| IA e CBOs | 4 (prompt, taxonomia, revisão) | IA & negócios + 1 técnico para o script |
| Análise e indicadores | 5, 6 | Técnico + negócios |
| Dashboard | 7 | Técnico + negócios (layout/storytelling) |
| Narrativa e pitch | 8, 9 | IA & negócios |

Caminho crítico: **1 → 2 → 3 → 6 → 7**. A etapa 4 pode correr em paralelo a partir do fim da etapa 2
(só precisa da lista de CBOs e do dicionário).

---

## 4. Próxima atividade

1. Equipe valida este diagnóstico e responde (ou aceita as propostas padrão de) **E1–E11**.
2. Enviar à organização as perguntas **E1, E4, E9 e E10**.
3. Iniciar a **etapa 1** (view tipada + checagens) e, em paralelo, a **taxonomia de macrofamílias** (etapa 4, passo 2).
