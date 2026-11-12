# Diagnóstico inicial — Datathon 2026

**Raio-X do Mercado de Trabalho e Vagas Industriais em Santa Catarina**
Auditoria realizada em 10/11/2026 (Dia 1 do evento), antes de qualquer análise de negócio.

> **Como ler este documento**
> - **[Fato]** = verificado nos arquivos, com número reproduzível por `python -m src.validation.profile_sources`.
> - **[Hipótese]** = interpretação plausível que ainda precisa ser confirmada.
> - **[Recomendação]** = proposta de decisão para a equipe.
>
> Nenhuma conclusão sobre o mercado de trabalho catarinense é apresentada aqui:
> os números citados descrevem **as bases**, não o mercado.

---

## A. Resumo executivo

**O desafio.** Somos uma "consultoria" contratada por uma entidade da indústria. Precisamos dizer
**onde** (municípios/regiões) e **em quais setores industriais** há sinais de *apagão de mão de obra*
(dificuldade de contratar ou de reter pessoas) ou de *expansão acelerada* (muitas vagas novas), e
**por que** — usando salário e escolaridade como possíveis explicações. A entrega é um repositório
Git público com o código, um dashboard em Python com pelo menos 3 indicadores-chave e um pitch de
3 minutos com slides.

**Os dados.** O insumo principal é o **Novo CAGED**: o registro oficial de cada admissão e de cada
desligamento de trabalhadores com carteira assinada. Temos 3,4 milhões dessas movimentações em SC,
declaradas entre setembro/2025 e agosto/2026. Cada linha diz *onde* (município), *em que setor*
(CNAE), *em qual ocupação* (CBO), *com qual salário* e *com qual escolaridade* alguém entrou ou saiu
de um emprego. Uma segunda base traz dados dos 295 municípios (população, PIB per capita, IDHM) e
serve para normalizar a comparação: 500 vagas em Joinville não significam o mesmo que 500 vagas
em um município de 3 mil habitantes.

**O que é importante entender desde já.**

1. O CAGED mede **fluxo** (entradas e saídas), não **estoque** (quantas pessoas estão empregadas)
   nem **vagas abertas**. Por isso ele **não mede escassez diretamente**. Saldo negativo pode
   significar falta de gente, mas também crise, sazonalidade ou automação. Saldo positivo pode ser
   expansão, mas também recuperação de um mês ruim.
2. Para falar em "apagão" com responsabilidade, precisamos **combinar sinais**: saldo, motivo dos
   desligamentos (pedidos de demissão indicam trabalhadores com alternativas), diferença salarial
   entre quem entra e quem sai, e exigência de escolaridade. Mesmo assim, será um **indício**, não uma prova.
3. As bases já estão em boa forma (a chave entre elas casa 100%), mas há **decisões metodológicas
   pendentes**: o que conta como "indústria", qual mês considerar, como tratar exclusões (que não
   estão na base) e como agrupar municípios em regiões (não há coluna de região).

---

## B. Inventário das bases

| Arquivo | Origem | Tamanho | Registros | Colunas | Finalidade | Situação atual |
|---|---|---|---|---|---|---|
| `data/raw/Novo_Caged_MOV_Limpo.parquet` | Organização (CSV no Drive), convertido pela equipe no commit `429625d` | 43,9 MB | **3.397.416** [Fato] | **30** [Fato] | Movimentações trabalhistas (fato principal) | Versionado. Todas as colunas como texto. Lido sem problemas com DuckDB. |
| `Novo_Caged_MOV_Limpo.csv` (Google Drive) | Organização | ~395 MB (segundo o README do colega; não medido) | não medido | não medido | Original do Parquet | **Link público** [Fato: responde com a página de download do Drive]. Não baixado: desnecessário enquanto o Parquet estiver validado. Não versionar. |
| `data/reference/Municipios_SC_limpo.csv` | Organização (fontes no rodapé: IBGE, PNUD, DATASUS, Siconfi) | 41 KB | **295** municípios + 1 linha de rodapé [Fato] | **15** (1 vazia) [Fato] | Normalização e contexto territorial | Versionado. Ausentes como `-`. |
| `data/reference/Dicionario_de_dados.xlsx` | Organização (layout oficial do Novo CAGED) | 294 KB | 23 abas [Fato] | — | Significado das variáveis e tabelas de códigos | Versionado. Cobre 30 variáveis; 2 delas não estão na base. |
| `context/Guia do Participante.md` | Conversão do `.docx` oficial | 11 KB | — | — | Regras do desafio | Conversão com perda de estrutura (títulos fora de ordem, tabela quebrada), mas texto íntegro. |
| `context/originais/*.docx`, `*.pptx` | Organização | 89 KB / 385 KB | — | — | Documentos oficiais | Recuperados do Git (estavam apagados localmente). |

**Período coberto** [Fato]: `competênciadec` (mês da declaração) vai de **202509 a 202608** — 12 meses.
`competênciamov` (mês do fato) tem 24 valores, de 202409 a 202608, porque 36.940 movimentações
(1,09%) foram declaradas **fora do prazo**, referentes a meses anteriores.

**Volumes gerais** [Fato]: 1.719.449 admissões, 1.677.967 desligamentos, saldo +41.482.
A seção C (Indústria de Transformação) tem 836.753 movimentações (24,6% do total), presentes em
294 dos 295 municípios.

---

## C. Dicionário analítico (resumo)

O mapeamento completo — campo a campo, com valores observados e uso por eixo — está em
[`dicionario_analitico.md`](dicionario_analitico.md). Os campos que sustentam a análise são:

| Campo | O que é | Papel |
|---|---|---|
| `saldomovimentação` | +1 admissão / −1 desligamento | Medida base: somar = saldo; contar = admissões e desligamentos. |
| `tipomovimentação` | Motivo da movimentação | Distingue desligamento **a pedido** (sinal de mercado aquecido) de **demissão** (sinal de retração) e **fim de contrato** (sazonalidade). |
| `município` | Código de 6 dígitos | Recorte territorial e chave de junção. |
| `seção` / `subclasse` | Setor (CNAE 2.0) | Recorte setorial; os 2 primeiros dígitos da subclasse = **divisão** (ex.: 14 Vestuário). |
| `cbo2002ocupação` | Ocupação | Base das macrofamílias (Eixo 3). |
| `graudeinstrução` | Escolaridade | Perfil de admitidos × desligados (Eixo 2). |
| `salário` | Salário mensal declarado | Renda (Eixo 2). Usar mediana. |
| `competênciadec` / `competênciamov` | Mês | Série temporal e janela de 12 meses. |
| População estimada (base municipal) | Habitantes | Denominador do saldo por 10 mil habitantes. |

---

## D. Problemas identificados

### D.1 Estado do repositório

| # | Problema | Situação/ação |
|---|---|---|
| R1 | O snapshot informava `main` limpo, mas a cópia local estava na branch **`Nyrx`**, com 6 arquivos versionados **apagados** (`dataset/…`, `documentos_apoio/…`) e 4 não rastreados. | Nada foi descartado. Os arquivos apagados foram **recuperados do Git** em novos caminhos (hash idêntico ⇒ o Git registra como renomeação, sem aumentar o repositório). |
| R2 | `README.md` local estava **vazio** (0 bytes). | Reescrito. |
| R3 | O `.gitignore` apontava para `dataset/`, que deixou de existir; não ignorava `data/processed/` nem arquivos de segredos além de `.env`. | Atualizado. |
| R4 | Não havia registro de dependências; o Python local (3.14) não tinha DuckDB/Polars/PyArrow. | Criado `requirements.txt` e ambiente `.venv` (ignorado pelo Git). |
| R5 | `Municipios_SC_limpo.csv` local difere do versionado apenas em quebras de linha (CRLF × LF; 297 bytes = 297 linhas). | Conteúdo idêntico; sem ação. Sugestão: `.gitattributes` se isso gerar diffs ruidosos. |
| R6 | A branch remota `origin/engenharia` (do colega) já foi integrada à `main` via PR #1. | Sem conflito. Alinhar com a equipe antes de abrir novo PR. |

### D.2 Qualidade e consistência dos dados

| # | Problema | Evidência [Fato] | Impacto | Tratamento proposto |
|---|---|---|---|---|
| Q1 | **Exclusões ausentes** | `competênciaexc` e `indicadordeexclusão` estão no dicionário, mas **não na base** | O guia manda "aplicar a filtragem das exclusões (MOV × EX)", mas não há como identificá-las | Perguntar à organização (E1). [Hipótese] o sufixo "Limpo" indica que as exclusões já foram removidas. |
| Q2 | **Admissões sem subtipo** | 1.718.686 das 1.719.449 admissões são `97` "Admissão de Tipo Ignorado"; os códigos 10, 20, 25 e 70 não aparecem | Impossível separar primeiro emprego de reemprego | Tratar admissão como categoria única. Registrar como limitação. |
| Q3 | **Tudo armazenado como texto** | 30 colunas VARCHAR; decimais com vírgula; `idade` como `"40.0"` | Agregações erradas se não houver conversão | Etapa de tipagem explícita no pipeline. |
| Q4 | **Salários zerados e extremos** | 33.912 zeros (1,0%); 535 acima de R$ 50 mil; máximo R$ 3.471.600; unidade `7` Variável sempre com salário 0 | Médias distorcidas | Usar **mediana**; excluir zeros das estatísticas de salário; definir regra para extremos (E5). |
| Q5 | **Grau de instrução `80` fora de ordem** | `80` = Pós-Graduação completa (33.303 registros) | Ordenar pelo código numérico coloca Pós depois de Doutorado | Mapear para uma escala ordinal explícita. |
| Q6 | **Códigos sem zero à esquerda** | 105.072 subclasses com 6 dígitos; 8 CBOs com 5 dígitos | Junção com dicionário e derivação de divisão/grande grupo falham | `lpad(subclasse, 7, '0')`, `lpad(cbo, 6, '0')`. |
| Q7 | **Códigos fora do dicionário** | 28 CBOs (2.117 registros) e 1 subclasse (`8630505`, 13 registros) | Ficam sem descrição | Manter com rótulo "sem descrição no dicionário"; impacto pequeno. |
| Q8 | **Porte do estabelecimento ausente no último mês** | `tamestabjan = 99` em 100% dos 272.463 registros de 202608 | Análise por porte perde agosto/2026 | Excluir 202608 de análises por porte ou não usar o campo. |
| Q9 | **Linhas idênticas** | 97.635 linhas (2,87%) iguais em todas as colunas (exceto índices) | Podem ser duplicatas **ou** pessoas diferentes com mesmo perfil (microdado não tem identificador) | **Não remover** [Recomendação]: o CAGED não identifica o trabalhador; contratações em lote geram linhas idênticas legítimas. Documentar. |
| Q10 | **Colunas de índice** | `Unnamed: 0.1`, `Unnamed: 0` | Ruído | Descartar. |
| Q11 | **Registros EmpregadoWEB** | 510 registros com `origemdainformação = 3` | [Hipótese] são os mesmos com `categoria = 999` e horas = 0 | Verificar; volume desprezível. |
| Q12 | **Rodapé e coluna vazia no CSV de municípios** | Linha 296 é HTML; `Unnamed: 14` vazia | Leitura ingênua gera um "município" falso | Filtrar código com 7 dígitos; descartar a coluna. |
| Q13 | **Rótulos de ano inconsistentes no CSV de municípios** | Cabeçalho "[2026]" × rodapé "estimativa de 1º/07/2024"; escolarização "[2022]" × "Censo 2010" | Citar o ano errado no pitch | Citar a fonte do rodapé ou dizer "estimativa mais recente fornecida". |
| Q14 | Ausentes na base municipal | IDHM: 2 (`-`); Mortalidade infantil: 123 (`-`) | Mortalidade praticamente inutilizável | Não usar mortalidade; IDHM só como contexto. |

### D.3 Riscos metodológicos

| # | Risco | Por que importa | Mitigação |
|---|---|---|---|
| M1 | **Confundir movimentação com escassez** | Saldo é diferença entre fluxos; não mede vagas não preenchidas | Linguagem de "sinais/indícios"; matriz de sinais combinados (ver I). |
| M2 | **Ausência de estoque de emprego** | Sem estoque não se calcula taxa de rotatividade oficial nem crescimento percentual do emprego | Usar indicadores relativos à população e razões internas (ex.: % a pedido). Estoque viria da RAIS (externa). |
| M3 | **Sazonalidade** | 202512 tem saldo −48.616 [Fato]; fim de ano e safras afetam setores de forma diferente | Mostrar série mensal; comparar janelas completas de 12 meses; não comparar meses isolados. |
| M4 | **Municípios pequenos** | Por 10 mil habitantes, poucas movimentações viram números enormes | Volume mínimo para ranquear; mostrar valor absoluto junto. |
| M5 | **Local do estabelecimento ≠ local de moradia** | [Hipótese: no Novo CAGED o município é o do estabelecimento] Polos atraem trabalhadores de cidades vizinhas | Preferir agregação regional para conclusões; citar a limitação. |
| M6 | **Salário nominal** | 12 meses incluem reajuste anual do salário mínimo (janeiro) | Comparar admissão × desligamento **no mesmo mês/recorte**; evitar comparar meses distantes. |
| M7 | **Composição** | Diferença salarial pode refletir mix de ocupações, não "pagar menos" | Comparar dentro da mesma macrofamília/CBO. |
| M8 | **Classificação de CBO por IA** | LLM pode inventar ou errar categorias | Taxonomia fixa, justificativa por item, revisão humana, versionamento (ver plano, etapa 4). |
| M9 | **Correlação ≠ causa** | Escolaridade e salário "explicam" no sentido descritivo | Apresentar como associação. |

### D.4 Integração, limitações técnicas e dependências externas

- **Integração** [Fato]: o guia cita `municipio_codigo`, que **não existe**. A chave real é
  `município` (6 dígitos) ↔ `Código [-]` (7 dígitos). Os 295 municípios casam sem órfãos.
  Cardinalidade N:1 validada (sem códigos duplicados no lado municipal).
- **Sem região**: nenhuma base traz meso/microrregião. O guia pede "microrregiões". Requer tabela
  externa do IBGE (gratuita) — ver E4.
- **Mapa**: um mapa coroplético exige a malha geográfica dos municípios (IBGE/`geobr`, gratuita).
  Dependência externa; alternativa sem mapa: gráficos de barras/dispersão.
- **IA generativa**: não há chave de API configurada. Nenhuma chamada paga foi feita.
- **Memória**: o Parquet cabe em DuckDB sem problemas; evitar `pd.read_parquet` sem `columns=`.
- **Prazo**: Dia 1 tem 1h40 (10:00–11:40) e o Dia 2, 13/11, 08:30–11:40, segundo a apresentação
  oficial. O guia mostra horários diferentes para o Dia 1 (08:30–11:40) — ver E9.

---

## E. Perguntas que a equipe precisa responder

| # | Pergunta | Para quem | Proposta padrão enquanto não houver resposta |
|---|---|---|---|
| E1 | As exclusões (EX) já foram removidas da base "Limpo"? O que significa "aplicar filtros (EX)" se a coluna não existe? | Organização | Assumir que já foram removidas e declarar isso no pitch. |
| E2 | O que é "setor industrial"? Só a seção C (Transformação) ou B–F (inclui extrativa, energia, saneamento e **construção**)? | Equipe | Foco principal na **seção C**, detalhada por divisão CNAE; B, D, E e F como comparação. |
| E3 | Qual mês usar: declaração (`competênciadec`, 12 meses exatos) ou movimentação (`competênciamov`, inclui 1,09% de meses anteriores)? | Equipe | Totais da janela por `competênciadec`; séries mensais por `competênciamov` restrita a 202509–202608. |
| E4 | Podemos usar dados externos (regiões do IBGE, malha para mapa)? Qual recorte regional: regiões geográficas imediatas/intermediárias (IBGE 2017) ou associações de municípios? | Organização / Equipe | Usar regiões do IBGE (fonte oficial e gratuita), se permitido. |
| E5 | Regra para salários: excluir zeros? Limite para extremos (ex.: percentil 99,5 ou R$ 50 mil)? Só unidade "Mês"? | Equipe | Excluir zeros e unidade `7`; mediana como medida principal; extremos mantidos na mediana, cortados na média. |
| E6 | Incluir aprendizes, temporários e intermitentes? | Equipe | Incluir no saldo (é emprego formal); mostrar recorte sem eles como sensibilidade. |
| E7 | População de referência: Censo 2022 ou estimativa? | Equipe | Estimativa (mais recente), citando a fonte do rodapé. |
| E8 | Qual ferramenta de IA está disponível gratuitamente para a equipe (chat ou API)? Há orçamento? | Equipe | Classificação via interface de chat gratuita, com arquivos de entrada/saída versionados. |
| E9 | Horário real do Dia 1: 08:30–11:40 (guia) ou 10:00–11:40 (apresentação)? | Organização | Planejar pelo cenário mais curto. |
| E10 | O pitch exige slides (apresentação) além do dashboard? | Organização | Sim — a apresentação oficial lista "Apresentação de slides contendo o pitch". |
| E11 | Quantas macrofamílias e com que critério (ex.: 8 a 12, por área técnica)? | Equipe | Taxonomia proposta no plano (etapa 4), validada pela equipe antes de rodar a IA. |

---

## F. Plano de trabalho

O plano detalhado — com pré-requisitos, entregáveis e critérios de conclusão de cada etapa e a
arquitetura técnica — está em [`plano_de_execucao.md`](plano_de_execucao.md). Ordem:

1. Ingestão e validação → 2. Limpeza e tratamento → 3. Cruzamento das bases →
4. Agrupamento de CBOs com IA → 5. Análise exploratória → 6. Indicadores →
7. Dashboard → 8. Recomendações → 9. Pitch → 10. Documentação e entrega.

---

## G. Proposta de dashboard (Streamlit + Plotly)

Princípio: o diretor deve **localizar → entender → decidir** (seção 2.3 do guia). Filtros globais:
período, seção/divisão CNAE, região/município, macrofamília.

| Página | Pergunta que responde | Conteúdo |
|---|---|---|
| 1. Visão geral | "Como está o emprego industrial em SC?" | KPIs: admissões, desligamentos, saldo, saldo por 10 mil hab., % desligamentos a pedido, mediana salarial de admissão. Série mensal do saldo (barras +/−). |
| 2. Território | "Onde estão os polos e as retrações?" | Mapa coroplético de saldo por 10 mil hab. (se a malha estiver disponível; senão, barras ranqueadas); tabela de municípios/regiões com volume mínimo; dispersão saldo × PIB per capita. |
| 3. Setores | "Quais setores industriais lideram?" | Barras divergentes de saldo por divisão CNAE; heatmap divisão × região; % a pedido por divisão. |
| 4. Renda e escolaridade | "Quem entra × quem sai?" | Mediana salarial de admitidos × desligados por divisão/escolaridade; distribuição de escolaridade (barras 100% empilhadas, admitidos × desligados); prêmio salarial por escolaridade. |
| 5. Ocupações (IA) | "Os gargalos são técnicos ou operacionais?" | Treemap de movimentações por macrofamília; dispersão saldo × gap salarial por macrofamília (tamanho = volume); tabela de CBOs com justificativa da classificação. |
| 6. Diagnóstico e recomendações | "O que fazer?" | Matriz de sinais (ver I.13) com os focos priorizados, recomendações e **limitações** explícitas. |

Mínimo exigido pelo guia: 3 indicadores-chave. Os candidatos mais fortes são **saldo por 10 mil
habitantes**, **gap salarial admissão × desligamento** e **% de desligamentos a pedido**, sempre
segmentados por macrofamília.

---

## H. Recomendações iniciais (onde a análise pode gerar valor)

Sem conclusões sobre o mercado — apenas **perguntas valiosas** que os dados permitem responder:

- **Para uma indústria**: em quais ocupações da minha divisão CNAE e região o salário de admissão
  está **abaixo** do de desligamento e os pedidos de demissão são altos? Isso sugere dificuldade de
  retenção por remuneração — insumo para revisão de faixas salariais e políticas de retenção.
- **Para uma entidade de classe (ex.: federação das indústrias)**: quais macrofamílias técnicas
  concentram saldo positivo e exigem escolaridade média/técnica? Isso orienta **oferta de cursos
  técnicos e de qualificação** por região (ligação direta com o critério 4 da banca).
- **Para um gestor público**: quais regiões concentram expansão (pressão sobre infraestrutura,
  transporte e moradia) e quais encolhem (necessidade de requalificação e atração de investimento)?
- **Transversal**: a combinação "saldo positivo + muitos pedidos de demissão + salário de admissão
  em alta" é o padrão mais próximo de "mercado disputado" que o CAGED consegue sinalizar.

---

## I. Indicadores propostos

Notação: para um recorte *r* (município, região, divisão CNAE, macrofamília, mês ou combinação),
**A** = nº de registros com `saldomovimentação = 1`; **D** = nº com `−1`; **Dₚ** = desligamentos
a pedido (`tipomovimentação = 40`); **P** = população estimada; **med(·)** = mediana do `salário`
(excluídos zeros, conforme E5).

### Indicadores de movimentação (calculáveis com os dados atuais)

| # | Indicador | Objetivo de negócio | Fórmula | Campos | Granularidade | Interpretação | Limitações | Visualização |
|---|---|---|---|---|---|---|---|---|
| 1 | Admissões, desligamentos e saldo | Volume e direção do emprego formal | A; D; S = A − D | `saldomovimentação` | Qualquer recorte | S > 0: criação líquida de postos | Não é estoque; sensível à sazonalidade | KPI; barras divergentes; série mensal |
| 2 | **Saldo por 10 mil habitantes** | Comparar territórios de tamanhos diferentes | S / P × 10.000 | + `município`, população | Município, região | Intensidade relativa da criação de postos | Moradia ≠ trabalho (M5); instável em municípios pequenos (M4) | Mapa; barras ranqueadas |
| 3 | Movimentação por 10 mil habitantes | Dinamismo/rotatividade territorial | (A + D) / P × 10.000 | idem | Município, região | Mercado muito "girando" | Não distingue expansão de rotatividade | Dispersão contra o indicador 2 |
| 4 | Razão de reposição | Equilíbrio entre entradas e saídas | A / D | `saldomovimentação` | Qualquer | > 1 expansão; ≈ 1 reposição; < 1 retração | Indefinida com D pequeno | Barras com linha em 1 |
| 5 | **% de desligamentos a pedido** | Sinal de poder de barganha do trabalhador | Dₚ / D | + `tipomovimentação` | Qualquer | Alto: trabalhadores saem por escolha (alternativas no mercado, insatisfação) | Não diz o motivo do pedido | Barras; heatmap setor × região |
| 6 | Composição dos desligamentos | Diferenciar retração de sazonalidade | % por tipo (31, 32, 40, 43, 90…) / D | `tipomovimentação` | Setor, região | Muita demissão sem justa causa = retração; muito fim de contrato = sazonal | Admissões não têm subtipo (Q2) | Barras 100% empilhadas |
| 7 | Saldo acumulado e tendência | Distinguir pico pontual de tendência | Σ S por mês; S dos últimos 3 meses vs. 3 anteriores | + `competênciamov` | Mês × recorte | Aceleração ou desaceleração | Janela curta (12 meses) | Linha acumulada; sparklines |
| 8 | Concentração territorial | Identificar polos | S do município / S do estado no setor; ou HHI | `município`, `seção`/`subclasse` | Setor | Saldo concentrado em poucos municípios = polo | Saldos de sinais opostos dificultam a participação | Pareto; treemap |

### Indicadores de renda e escolaridade

| # | Indicador | Objetivo | Fórmula | Campos | Granularidade | Interpretação | Limitações | Visualização |
|---|---|---|---|---|---|---|---|---|
| 9 | Mediana e média salarial (A e D) | Remuneração de entrada e de saída | med(salário \| A), med(salário \| D) | `salário`, `unidadesaláriocódigo` | Setor, município, CBO, escolaridade | Nível salarial do recorte | Nominal (M6); zeros/extremos (Q4) | Barras; boxplot |
| 10 | **Gap salarial admissão × desligamento** | Compressão ou valorização salarial | med(sal \| A) / med(sal \| D) − 1 | idem | Recorte × mês | > 0: contratando mais caro (disputa); < 0: substituindo por mais barato | Efeito composição (M7) — calcular dentro da macrofamília | Barras divergentes; dispersão com indicador 1 |
| 11 | Perfil de escolaridade (A × D) | O mercado está exigindo mais formação? | % de A por nível − % de D por nível (pontos percentuais) | `graudeinstrução` | Setor, macrofamília | Positivo em níveis altos: admissões mais escolarizadas | Escolaridade declarada, não exigida pela vaga | Barras 100% empilhadas lado a lado |
| 12 | Prêmio salarial por escolaridade | Quanto a escolaridade paga em cada setor | med(sal \| nível k) / med(sal \| Médio completo) − 1 | `salário`, `graudeinstrução` | Setor, macrofamília | Prêmio baixo em nível alto: possível compressão salarial (pergunta do guia) | Amostras pequenas em Mestrado/Doutorado | Linhas por nível; heatmap |

### Indicadores do Eixo 3 e síntese

| # | Indicador | Objetivo | Fórmula | Campos | Granularidade | Interpretação | Limitações | Visualização |
|---|---|---|---|---|---|---|---|---|
| 13 | Movimentação e saldo por macrofamília | Gargalos técnicos × operacionais | Indicadores 1, 5, 10 e 11 por macrofamília | `cbo2002ocupação` + tabela de macrofamílias | Macrofamília × setor × região | Onde estão os sinais por tipo de função | Depende da qualidade da classificação (M8) | Treemap; dispersão saldo × gap |
| 14 | **Matriz de sinais** (síntese) | Responder à pergunta central | Regras com base em 1/2, 5, 10, 11 (ex.: saldo/10 mil alto **e** gap > 0 **e** % a pedido alto ⇒ "sinal de mercado disputado") | todos acima | Região × divisão × macrofamília | Classifica recortes em "expansão", "disputa/possível escassez", "retração", "rotatividade" | **É uma heurística definida pela equipe**, não um índice oficial; limiares devem ser documentados | Quadrantes; tabela semafórica |

### O que **não** pode ser calculado com os dados disponíveis

| Medida | Por quê | Fonte que permitiria |
|---|---|---|
| Vagas abertas / não preenchidas / tempo de preenchimento | O CAGED só registra contratações efetivadas | Bases de vagas (ex.: Sine, portais de emprego) |
| Taxa de rotatividade oficial e variação % do emprego | Requer estoque de vínculos | RAIS / estoque do CAGED publicado pelo MTE |
| Desemprego ou oferta de trabalhadores por município | CAGED cobre só o emprego formal | PNAD Contínua (só UF/capital), Censo |
| Oferta de formação (cursos técnicos, egressos) | Não está nas bases | Censo Escolar / Sistec, dados do SENAI |
| Mobilidade individual (o mesmo trabalhador saindo e entrando) | Microdado sem identificador | Não disponível publicamente |

**Escassez efetiva** só seria medida com demanda (vagas) **e** oferta (trabalhadores disponíveis).
Nossos indicadores medem **movimentação** e permitem levantar **sinais** de escassez.
