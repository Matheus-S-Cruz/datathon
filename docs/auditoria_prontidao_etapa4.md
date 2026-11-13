# Auditoria de prontidão para a Etapa 4 — Assistente Inteligente

> **Esta auditoria NÃO implementa o assistente.** Seu objetivo é mapear a arquitetura atual,
> identificar dependências, riscos e requisitos técnicos, e produzir um plano para que o assistente
> seja, quando construído, uma **camada confiável sobre o dashboard** — nunca um chatbot que interpreta
> dados por conta própria ou contradiz a plataforma. (§8 do plano.)
>
> **Nada no código, dados, pipeline ou painel foi alterado por este documento.**

Base factual: inventário técnico da branch `integracao` (serviços, dados, glossário, segurança).
Referências em `arquivo:linha`.

---

## 1. Arquitetura atual

### Duas camadas de dados, com fronteira clara

| Camada | Fonte | Como é lida | Respeita qual recorte | Usada por |
|---|---|---|---|---|
| **Tempo de execução (DuckDB)** | `data/raw/Novo_Caged_MOV_Limpo.parquet` (3,4 M linhas) | Views `caged_raw`/`caged` sobre o Parquet; consultas SQL parametrizadas (`dashboard/services/queries.py`, `database.py`) | `Filters` (Explorador) | Explorador, Estatística, Relações, Auditoria |
| **Pré-agregada** | `outputs/*.parquet` (gerados pelo pipeline) | `analytics.table(name)` (cache) | `Scope` (recorte global) | Painel, Território, Setores, Renda, Macrofamílias, Contexto IBGE, Tabelas |

- **Conexão DuckDB**: `database._connection()` (`database.py:71-90`), `@lru_cache` por `data_signature()` (mtime+tamanho de cada base). O Parquet **não** é carregado em memória; cada consulta lê só as colunas/linhas necessárias.
- **View `caged`**: montada por `catalog.typed_view_sql()` (`catalog.py:181-194`) — colunas convertidas (`TRY_CAST`, vírgula decimal → DECIMAL; zero à esquerda via `lpad`), e derivadas (`divisao_cnae`, `grande_grupo_cbo`, `movimento`). Valores inválidos viram NULL, contados na auditoria (não silenciosos).
- **Pré-agregados** (`analytics.OUTPUT_TABLES`): `agg_municipio`, `agg_setor`, `agg_municipio_setor`, `agg_regiao`, `perfil_adm_desl`, `salario_por_grau`, `macrofamilias_cbo`, `macrofamilias_industria`, `salario_resumo`.
- **Bases IBGE** (`data/external/`): CEMPRE 2024, PIB municipal, regiões, malha; já incorporadas aos agregados. `analytics.coords()/geojson()/external_sources()` leem direto só o que o mapa usa.

### Conhecimento metodológico centralizado

- `src/glossario.py`: fonte única de definições — **17 indicadores** e **9 notas**. Cada `Indicador` tem `id, nome, grupo, definicao, formula, unidade, fonte, periodo, abrangencia, filtragem, limitacoes, colunas, onde, textos`.
- `docs/glossario.md`, `docs/metodologia_salarial.md`, `docs/cbo_classificacao.md`, `docs/dicionario_analitico.md`, `docs/diagnostico_inicial.md`: documentação de apoio.

### Contratos fortes já existentes

- `Filters` (frozen dataclass, `queries.py:44-92`) + `build_where()` parametrizado (lista branca de colunas).
- `Scope` (frozen dataclass, `analytics.py:109-131`): `secoes`, `min_pop`, `regiao`, com `all_sections` e `describe()`.

---

## 2. Arquitetura proposta para o assistente (visão, não implementação)

```
 usuário  ─►  UI do chat (botão flutuante)  ─►  Orquestrador do assistente
                                                      │
                 ┌────────────────────────────────────┼─────────────────────────────┐
                 ▼                                      ▼                             ▼
      Camada de CONHECIMENTO                 Camada de CONSULTA (tools)       Guardrails de resposta
      (glossário: definições,          (contratos sobre queries.py/           (fonte, período, unidade,
       fórmulas, fontes, limites)       analytics.py — SEM SQL livre)          limitações; "não sei")
                 │                                      │
                 └──────────────► o modelo recebe conhecimento + resultado de consultas controladas,
                                   nunca acesso direto a arquivos nem geração de SQL arbitrário.
```

Princípio central (§8.3): **a camada conversacional não acessa arquivos nem executa código/SQL arbitrário.** Ela só pode chamar um conjunto fechado de "contratos de consulta" que reutilizam os serviços já validados. O modelo transforma linguagem natural em uma chamada de contrato (com parâmetros validados) e **nunca** inventa números.

---

## 3. Componentes reutilizáveis (já existem)

### Consultas DuckDB com contrato `Filters` (`queries.py`)
`overview_kpis()`, `flow_by(dim, f)`, `explorer_count(f)`, `explorer_page(...)`, `aggregate(dim_keys, f, min_movements)`, `numeric_summary(expr, f)`, `grouped_summary(expr, dim, f)`, `correlation(x, y, f)`, `histogram(...)`, `municipal_metrics(f)`, `education_distribution(...)`, `distinct_values(...)`, `municipality_names()`, `describe()/describer()`.

### Agregados com contrato `Scope` (`analytics.py`)
`kpis(scope)`, `municipal(scope)`, `sectors()/sectors_in_scope(scope)`, `regions(level)`, `macro(industrial_only)`, `salario_estado()`, `table(name)`.

### Conhecimento (`glossario.py`)
`INDICADORES`, `NOTAS`, `indicador(id)`, `texto(id, chave)`, `nota(id)`, `ajuda_colunas()`, `markdown()`.

### Vocabulário controlado
`DIMENSIONS`, `MUNICIPAL_VARIABLES`, `RECORD_VARIABLES`, `NUMERIC_SORT` (`queries.py`); `catalog.BY_NAME` (lista branca de colunas); `EDUCATION_ORDER`.

### Auditoria e metadados
`profiling.all_findings()` (dataclass `Finding` com o_que/como/porque/recomendacao/natureza/sql), `file_info()`, `validation_checks()`; `dictionary.search()/code_labels()`.

---

## 4. Componentes que precisam ser criados (na Etapa 4, não agora)

1. **Camada de contratos de consulta** (uma fachada fina sobre `queries.py`/`analytics.py`) que:
   - exponha um conjunto **fechado e nomeado** de consultas (ex.: `kpis_do_recorte`, `top_municipios`, `salario_por_escolaridade`, `saldo_por_setor`, `definicao_indicador`);
   - aceite **só parâmetros de um vocabulário controlado** (dimensões/colunas da lista branca, nunca `expr` SQL livre);
   - devolva dados estruturados **＋** metadados (fonte, período, unidade, nº de registros, limitações) tirados do glossário.
2. **Adaptador de modelo desacoplado do provedor** (mesma filosofia da arquitetura CBO 3.5b): interface única, provedor plugável, chave via variável de ambiente.
3. **UI do chat**: botão flutuante, janela, histórico de sessão, estados de carregamento/erro, sugestões, acessibilidade por teclado, minimizar/encerrar.
4. **Guardrails de resposta**: pós-processamento que exige citar fonte/período/unidade e detecta "não há dados suficientes".
5. **Contexto de página/filtros**: passar ao assistente a página atual e o `Scope`/`Filters` ativos, para a resposta corresponder ao recorte exibido.
6. **Camada de segurança**: validação/limite de tamanho das perguntas, separação instrução×dados, rate limiting, logging sem dados sensíveis.

---

## 5. Dependências

- **Dados**: o assistente depende das mesmas bases do dashboard (`data/raw`, `outputs/`, `data/external`, `data/reference`). Se uma base mudar, `data_signature()` já invalida o cache — o assistente deve usar os mesmos serviços para herdar isso.
- **Serviços**: depende de `queries.py` e `analytics.py` permanecerem a única porta de cálculo. **Risco** se o assistente recalcular por fora.
- **Glossário**: depende de `src/glossario.py` como fonte de definições/limitações.
- **Provedor de IA**: dependência externa (API). Deve ser desacoplada (ver §7) e exige chave + autorização de custo.
- **Recorte**: o assistente precisa receber `Scope`/`Filters` ativos; hoje eles vivem no `st.session_state` das páginas.

---

## 6. Riscos

| # | Risco | Gravidade | Mitigação |
|---|---|---|---|
| R1 | Assistente **inventar números** ou recalcular diferente da plataforma | Alta | Só pode responder via contratos de consulta que reutilizam `queries.py`/`analytics.py`; proibido SQL/código livre |
| R2 | Confundir **média vs mediana** do salário | Média | Glossário marca mediana como principal; contratos devem devolver a medida rotulada e a ressalva |
| R3 | Confundir **população Censo 2022 vs estimativa 2026** (mesmo indicador, dois valores) | Média | Glossário tem as duas variantes (`saldo_por_10k_censo`/`_estimativa`); contratos devem declarar qual usam |
| R4 | Confundir **classificação CBO oficial vs 9 macrofamílias analíticas** | Média | `docs/cbo_classificacao.md` documenta a coexistência; o assistente deve diferenciar |
| R5 | **Prompt injection** / instrução embutida na pergunta | Alta | Separar instruções (system) de dados; validar/limitar tamanho; nunca passar texto livre a funções que interpolam `expr` |
| R6 | **SQL injection** se contratos aceitarem `expr`/coluna livres | Alta | Contratos só aceitam vocabulário da lista branca (`BY_NAME`, `DIMENSIONS`); `extra`/`expr` **nunca** vêm do usuário |
| R7 | Vazamento de **caminhos internos/segredos** em erros ou logs | Média | `DataSourceError` já dá mensagem limpa; logging sem PII; chave só em env var |
| R8 | Resposta que **não corresponde ao recorte** exibido | Média | Passar `Scope`/`Filters` ativos ao contrato; declarar o recorte na resposta |
| R9 | Afirmar **causalidade** (escolaridade → salário) | Média | Glossário já tem notas descritivas; guardrail de linguagem |
| R10 | Custo de API sem controle | Média | Teto de orçamento, rate limiting, modelo econômico, cache de respostas |

---

## 7. Custos e infraestrutura

- **Modelo**: tarefa de perguntas-e-respostas sobre dados estruturados + explicação de indicadores — um modelo "mini/flash" econômico basta; não exige modelo premium.
- **Arquitetura desacoplada do provedor** (recomendada): interface única, provedor plugável (OpenAI, Anthropic, Google, ou local), permitindo substituição futura sem reescrever a aplicação. Já há precedente no projeto (arquitetura CBO 3.5b).
- **Chave**: variável de ambiente, nunca versionada (`.gitignore` já cobre `.env`/`*.key`/`secrets.toml`).
- **Latência**: aceitável para chat; cache de respostas frequentes reduz custo e latência.
- **Privacidade**: enviar ao provedor **só** a pergunta + o resultado mínimo da consulta + o conhecimento necessário — nunca a base inteira nem dados desnecessários (§8.4).
- **Não** escolher provedor por popularidade; decidir por custo/latência/privacidade/substituibilidade, com autorização de gasto.

---

## 8. Estratégia de testes (para a Etapa 4)

- **Contratos de consulta**: testar que cada contrato devolve os mesmos números que a página correspondente (reuso de `queries.py`/`analytics.py`), e que rejeita parâmetros fora do vocabulário.
- **Guardrails**: testes de que respostas sem dados retornam "não sei"; que número sempre vem acompanhado de fonte/período/unidade.
- **Segurança**: testes de prompt injection (instrução embutida ignorada), de limite de tamanho, de ausência de SQL livre.
- **Regressão**: a suíte atual (**85 testes / 219 subtestes, todos passam hoje**) deve continuar verde; o assistente é aditivo.
- **Equivalência**: resposta do assistente para "qual o saldo?" = `overview_kpis()`/`kpis(scope)`.

---

## 9. Estratégia de segurança

Estado atual (forte ponto de partida):
- **Nenhum segredo no código** (grep por `OPENAI_API_KEY`/`os.environ`/`eval`/`exec` em `src/` e `dashboard/`: zero ocorrências; o único uso está no passo opcional de LLM do notebook, que no-op sem chave).
- **SQL parametrizado por desenho**: valores do usuário sempre como `?`; colunas só da lista branca (`queries.py:1-11`, `build_where`).
- **Validação defensiva**: `periodo_coluna`, `movimento`, `order_by` restritos; `TRY_CAST` neutraliza valores malformados.
- `.gitignore` já ignora `.env`/`*.key`/`secrets.toml`.

A acrescentar na Etapa 4: validação/limite de tamanho das perguntas; separação instrução×dados; rate limiting; logging sem PII; e a regra de **nunca** passar texto livre do usuário às funções que interpolam `expr` (`numeric_summary`, `correlation`, `histogram`, `grouped_summary`, `scatter_sample`) — elas são seguras só com entrada controlada.

---

## 10. Plano de implementação da Etapa 4 (sequência sugerida)

1. **Camada de contratos** (`dashboard/services/assistant_contracts.py` ou similar): conjunto fechado de consultas sobre os serviços existentes, cada uma devolvendo dados + metadados do glossário. Testar equivalência com as páginas.
2. **Adaptador de provedor** desacoplado (interface + 1 provedor), chave por env var.
3. **Orquestração**: mapear pergunta → contrato (com parâmetros validados), montar o contexto (conhecimento + resultado + `Scope`/`Filters` atuais).
4. **Guardrails de resposta** (fonte/período/unidade/limitações; "não sei").
5. **UI**: botão flutuante nas três seções, janela, histórico, estados, sugestões, acessibilidade, minimizar/encerrar.
6. **Segurança**: validação de entrada, rate limit, logging seguro.
7. **Testes** (contratos, guardrails, segurança, regressão) e **controle de custo** (teto, cache).

---

## 11. Critérios de aceite da Etapa 4

1. Toda resposta numérica vem de um contrato que reutiliza `queries.py`/`analytics.py` (nenhum número inventado).
2. O assistente informa quando não tem dados suficientes.
3. Respostas identificam período, unidade, abrangência e recorte aplicado.
4. Não afirma causalidade; diferencia observação de interpretação.
5. Não confunde média/mediana, Censo/estimativa, oficial/macrofamília.
6. Nenhum SQL/código arbitrário; nenhuma leitura de arquivo fora dos serviços.
7. Nenhum segredo no código; chave só em env var; logs sem PII.
8. Botão flutuante disponível nas três seções, responsivo, acessível por teclado, sem prejudicar gráficos/tabelas.
9. A suíte de testes continua verde e há testes novos para contratos, guardrails e segurança.
10. Custo sob teto autorizado, com plano de interrupção.

---

## 12. Pendências que dependem de decisão humana

1. **Autorização de custo de API** (modelo, teto, amostra) — ainda não concedida.
2. **Escolha do provedor** de IA (custo/latência/privacidade/substituibilidade).
3. **Padronização da população** (Censo 2022 vs estimativa 2026) — o glossário registra que "a escolha de um padrão está pendente"; convém decidir antes de o assistente responder sobre taxas por 10 mil hab.
4. **Qual recorte o assistente assume por padrão** (o `Scope` da página atual? o estado inteiro?).
5. **Classificação CBO experimental** (3.5c/3.5d) permanece pendente de autorização — o assistente não deve usá-la como oficial.

---

## Conclusão

> **Pronto com ressalvas.**

A base técnica é **sólida e favorável** a um assistente confiável: há uma camada de serviços reutilizáveis com contratos fortes (`Filters`, `Scope`), SQL parametrizado por desenho, um glossário único rico em definições/fórmulas/fontes/limitações, e nenhuma dívida de segurança no código atual (sem segredos, sem `eval`/`exec`, sem injeção no fluxo atual).

As **ressalvas** antes de iniciar a Etapa 4 são, todas, decisões humanas (não bloqueios técnicos):
1. autorizar custo e escolher o provedor de IA;
2. decidir o padrão de população (Censo 2022 × estimativa 2026);
3. definir o recorte-padrão do assistente;
4. criar a camada de contratos de consulta (trabalho da própria Etapa 4), garantindo que o assistente **nunca** recalcule por fora nem gere SQL livre.

Nenhuma dessas ressalvas exige refatoração estrutural. Resolvidas as decisões humanas, o projeto está apto a receber o assistente como uma **camada confiável sobre o dashboard**.
