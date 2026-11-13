# Metodologia da variável salarial — diagnóstico (Etapa 3.2a)

> **Status:** documento de diagnóstico metodológico. **Nada no pipeline, no painel ou
> nos dados foi alterado por este documento.** Ele estabelece a base para decidir,
> nas etapas seguintes (3.2b pipeline e 3.2c painel), se e como a apresentação do
> indicador salarial deve mudar. As alterações de pipeline e de painel dependem de
> aprovação explícita antes de serem implementadas.
>
> **Escopo:** apenas a variável salarial do Novo CAGED. Não toca em nenhum outro
> indicador, consulta, filtro ou classificação do projeto.

---

## 0. Por que este documento existe

O glossário (`src/glossario.py`) marca o indicador `salario_medio` como
*"definição atual, em revisão na etapa 3.2 do projeto"*. A página de auditoria
(`dashboard/services/profiling.py`, achados C1–C6) já havia sinalizado zeros,
valores extremos e periodicidades de pagamento como pendências a tratar.

Este documento responde às 10 perguntas metodológicas da Etapa 3.2a com base em
**duas fontes primárias** e em **medições diretas sobre a base**, sem assumir
nenhuma interpretação apenas porque ela "parece coerente".

### Fontes primárias consultadas

1. **Dicionário oficial do Novo CAGED** — `data/reference/Dicionario_de_dados.xlsx`,
   aba `Layout` e aba `unidadesaláriocódigo` (arquivo oficial distribuído com os
   microdados, versionado no repositório).
2. **Comunicado oficial do Ministério do Trabalho e Emprego (MTE)** — "Atualização
   dos microdados no Novo CAGED":
   <https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/comunicados/1831-comunicado-atualizacao-dos-microdados-no-novo-caged>
   *(conteúdo parafraseado para conformidade com restrições de licenciamento).*

### Como os números deste documento foram obtidos

Todas as estatísticas abaixo foram calculadas **diretamente** sobre
`data/raw/Novo_Caged_MOV_Limpo.parquet` (3.397.416 registros) com DuckDB,
usando exatamente a mesma conversão de tipo da aplicação
(`TRY_CAST(replace(trim("salário"), ',', '.') AS DECIMAL(18,2))`). Os valores
reproduzem os já verificados pela página de auditoria (C1–C6), o que confirma
a consistência entre este diagnóstico e o que o dashboard mede.

---

## 1. O que exatamente representa a variável salarial?

**`salário` = "Salário mensal declarado"** (dicionário oficial, aba `Layout`,
formato `999999999,99`).

O ponto metodológico mais importante vem do **comunicado oficial do MTE**: a partir
da atualização dos microdados, o MTE passou a divulgar duas variáveis adicionais
— `unidade salário` e `valor salário fixo` — e esclareceu que **continua
divulgando o valor do salário mensalizado, que resulta da combinação dessas duas
variáveis com as horas contratuais semanais**.

Em outras palavras:

- **`salário` já é o valor mensalizado pela própria origem (MTE).** Não é um valor
  "bruto por hora" nem "por semana"; é o resultado de um cálculo que o MTE já
  aplicou, combinando a parte fixa, a unidade de pagamento e as horas contratuais.
- **`unidadesaláriocódigo`** = "Unidade de pagamento **da parte fixa da remuneração**"
  (dicionário). Ou seja, descreve a periodicidade de **`valorsaláriofixo`**, e **não**
  de `salário`.
- **`valorsaláriofixo`** = "Salário base do trabalhador, correspondente à **parte
  fixa da remuneração**" (dicionário). É um insumo, de uso secundário.

**Consequência direta:** não se deve converter manualmente valores "semanais", "por
tarefa" ou "por hora" de `salário`, porque ele já está em base mensal. Fazer essa
conversão seria aplicar uma mensalização sobre um valor já mensalizado — um erro.
Isto também cumpre a instrução do plano (§4.2): *"Não faça conversões próprias de
valores semanais, por tarefa ou de outras periodicidades sem comprovação documental
e metodológica."* A comprovação documental mostra que **a conversão não deve ser
feita.**

---

## 2. Qual é a unidade de medida?

**Reais por mês (R$/mês).** O valor é mensalizado na origem. A formatação na
aplicação (`fmt.brl`) exibe em reais.

---

## 3. Quais periodicidades existem?

A variável `unidadesaláriocódigo` (periodicidade da **parte fixa**, não de `salário`)
tem os seguintes códigos (dicionário oficial) e a seguinte distribuição **real** na
base:

| Código | Descrição | Registros | % da base | % com salário = 0 |
|---:|---|---:|---:|---:|
| 5 | Mês | 3.005.066 | **88,45%** | 0,0% |
| 1 | Hora | 339.833 | 10,00% | 0,4% |
| 7 | Variável | 22.319 | 0,66% | **100,0%** |
| 2 | Dia | 15.888 | 0,47% | 0,0% |
| 99 | Não Identificado | 6.391 | 0,19% | 92,1% |
| 6 | Tarefa | 4.040 | 0,12% | 74,5% |
| 3 | Semana | 3.848 | 0,11% | 0,1% |
| 4 | Quinzena | 31 | 0,00% | 0,0% |

> **Nota sobre o "88,5%" usado hoje no app:** o help do filtro "Só salários com
> unidade 'Mês'" (`dashboard/components/filters.py`) diz "88,5% dos registros". A
> medição direta dá **88,45%**. O número está correto (arredonda para 88,5%). Este
> é um texto estático; não é calculado em tempo de execução.

---

## 4. Quais registros podem ser comparados?

Como `salário` **já está mensalizado para todas as unidades**, em princípio todos os
registros com salário válido e > 0 estão na mesma unidade (R$/mês) e são comparáveis
entre si. Isso é **confirmado empiricamente**: a mediana salarial por unidade de
pagamento (considerando apenas `salário > 0`) é praticamente a mesma para as duas
unidades dominantes —

| Unidade | n (salário > 0) | mediana | média |
|---|---:|---:|---:|
| 5 · Mês | 3.003.603 | R$ 2.156,00 | R$ 2.459,45 |
| 1 · Hora | 338.607 | R$ 2.167,00 | R$ 2.876,09 |
| 2 · Dia | 15.882 | R$ 3.256,20 | R$ 3.523,22 |

A mediana de "Hora" (R$ 2.167) é quase idêntica à de "Mês" (R$ 2.156). **Se `salário`
estivesse em valor-hora para a unidade 1, essa mediana seria uma fração da de "Mês" —
o que não acontece.** Isso corrobora, com dados, o que o comunicado do MTE afirma:
`salário` está mensalizado.

**Exceções que merecem cautela (volumes pequenos):**

- **Unidade 3 (Semana)** e **unidade 6 (Tarefa)** apresentam medianas muito baixas
  (R$ 43,05 e R$ 9,51 considerando apenas > 0), incompatíveis com salário mensal.
  São casos atípicos — possivelmente registros onde a mensalização não se aplicou
  bem — mas representam **0,11% e 0,12% da base** (3.848 e 4.040 registros, a maioria
  destes zerados). Devem ser **sinalizados, não escondidos** (ver §7 e §10).
- **Unidade 7 (Variável): 22.319 registros, 100% com salário zero.** São a maior
  fonte isolada de zeros.

---

## 5. Como são tratados valores zero?

**Hoje:** nas páginas analíticas (Painel `00`, Renda e escolaridade `12`), a métrica é
a **média** e **inclui os zeros**. No Explorador (DuckDB), as medianas de `aggregate`
e `municipal_metrics` já **excluem zeros** (`FILTER (WHERE salario > 0)`), e há um
filtro opcional "Excluir salários zerados".

**Fato medido:** existem **33.912 registros com `salário` = 0** (1,00% da base). Deles,
**22.319 (65,8%)** estão na unidade 7 (Variável) e vários outros nas unidades
99/Tarefa. Zeros quase nunca representam remuneração real de R$ 0; costumam indicar
que o valor não foi captado para aquela forma de pagamento.

**Impacto de excluí-los** (base inteira): média passa de R$ 2.478,58 → R$ 2.503,57;
mediana de R$ 2.155,00 → R$ 2.156,23. **A mediana é praticamente insensível; a média
sobe.** Zeros puxam a média para baixo.

---

## 6. Como são tratados valores ausentes?

Valores que não convertem para decimal viram **NULL** (`TRY_CAST`). **Na base atual
não há nenhum salário ausente após a conversão** (`validos = 3.397.416 = total`;
`nulos = 0`). As estatísticas DuckDB (`median`, `avg`, `count(x)`) já ignoram NULL
por construção; o pipeline pandas usa `errors="coerce"` + `mean`/`median`, que também
ignoram `NaN`. Portanto, ausência não é um problema prático nesta base — mas o
mecanismo que a trataria existe e é não-silencioso (a auditoria conta falhas de
conversão).

---

## 7. Como são tratados valores extremos?

**Hoje:** não há nenhuma winsorização, clipe ou corte automático de extremos em
nenhum dos dois caminhos (pandas ou DuckDB). O único amortecedor é a escolha de
**mediana** no Explorador. As páginas analíticas usam **média**, que é sensível a
extremos.

**Fato medido:** **535 registros acima de R$ 50 mil** (0,016% da base); máximo de
**R$ 3.471.600,00**; percentil 99 = R$ 7.649,31. Esses poucos valores elevam a média
bem acima da mediana (R$ 2.478,58 vs R$ 2.155,00). Não é possível, só com esta base,
distinguir erro de digitação de remuneração real alta.

---

## 8. Qual estatística representa melhor a distribuição?

A distribuição salarial é **fortemente assimétrica à direita** (média > mediana;
Q1 = R$ 1.935, mediana = R$ 2.155, Q3 = R$ 2.550, p99 = R$ 7.649, máx = R$ 3,47 mi).

Avaliação das opções (conforme §4.3 do plano):

| Medida | Comportamento nesta base | Papel recomendado |
|---|---|---|
| **Mediana** | Estável a zeros e extremos (R$ 2.155 → R$ 2.156 ao excluir zeros; muda pouco entre recortes) | **Medida principal** |
| **Média** | Instável; puxada por 535 extremos e deprimida por 33.912 zeros | **Medida complementar**, sempre rotulada e acompanhada da ressalva |
| **Média aparada 5%** | R$ 2.301 (base unidade Mês, > 0) — fica entre média (R$ 2.459) e mediana (R$ 2.156); reduz o efeito dos extremos sem descartá-los totalmente | **Análise de sensibilidade** (opcional), nunca como número principal |

**Recomendação metodológica (a validar nas etapas 3.2b/3.2c):** adotar a **mediana**
como medida principal do indicador salarial nas páginas analíticas, mantendo a
**média como complemento rotulado**. Isto alinha as páginas analíticas ao que o
Explorador e a auditoria já fazem, e ao que o catálogo/glossário já recomendam
("Usar mediana; tratar zeros e extremos").

> **Atualização:** a recomendação foi **aprovada e implementada** nas etapas 3.2b (pipeline)
> e 3.2c (painel). A mediana sem zeros (`salario_mediano_s0`) é agora a medida principal nos
> gráficos por escolaridade e macrofamília e no KPI de salário; a média permanece como
> complemento rotulado. Nenhuma coluna de origem foi sobrescrita (ver §11).

### Sobre o mínimo de 30 observações por grupo

O critério de n ≥ 30 deve ser tratado como **limiar de apresentação/estabilidade, não
como garantia de validade** (plano §4.3). Grupos abaixo do limite devem ser
**identificados explicitamente, não ocultados**.

Na agregação atual por grau de instrução (`outputs/salario_por_grau.parquet`),
**todos os 12 grupos têm n muito acima de 30** (o menor é Doutorado, n = 1.510). Logo,
o critério não afeta a apresentação por grau hoje — mas deve ser aplicado em qualquer
recorte mais fino (por município × ocupação, por exemplo), onde grupos pequenos podem
surgir.

---

## 9. Qual é a população de registros utilizada?

- **Universo:** 3.397.416 movimentações do Novo CAGED de Santa Catarina no período do
  projeto (admissões e desligamentos), conforme `data/raw`.
- **Observação importante sobre a definição atual:** `salario_medio` (hoje) é calculado
  sobre **admissões e desligamentos juntos**, **sem filtro de unidade** e **incluindo
  zeros**. Essa é a definição que o glossário marca como "em revisão".
- **Rastreabilidade dos incluídos/excluídos** (se a mediana > 0 for adotada):

  | Recorte | n | média | mediana |
  |---|---:|---:|---:|
  | A) toda a base (zeros + todas as unidades) | 3.397.416 | R$ 2.478,58 | R$ 2.155,00 |
  | B) excluir zeros | 3.363.504 | R$ 2.503,57 | R$ 2.156,23 |
  | C) só unidade Mês (5) | 3.005.066 | R$ 2.458,25 | R$ 2.156,00 |
  | D) unidade Mês + sem zero | 3.003.603 | R$ 2.459,45 | R$ 2.156,00 |

  Excluir zeros remove **33.912** registros; restringir à unidade Mês remove **392.350**;
  os dois juntos, **393.813** (11,6% da base). A mediana é estável em todos os recortes
  (R$ 2.155–2.156); a decisão de recorte afeta sobretudo a **média** e a **contagem**.

---

## 10. Quais são as limitações da análise?

1. **`salário` é fluxo de contratações, não estoque.** Representa quem foi admitido ou
   desligado no período, não o salário de toda a força de trabalho de SC.
2. **Zeros (33.912) e extremos (535 acima de R$ 50 mil)** convivem na mesma coluna e
   não podem ser separados de erro de digitação com esta base.
3. **Unidades Semana (3) e Tarefa (6)** têm medianas incompatíveis com salário mensal
   em um subconjunto pequeno de registros (~0,2% da base). Devem ser sinalizadas.
4. **`valorsaláriofixo` é apenas a parte fixa**; em 89,5% dos registros é igual a
   `salário`, então agrega pouca informação. Não deve ser usado como medida principal.
5. **Relação renda × escolaridade é descritiva, não causal.** A linguagem do painel não
   deve afirmar que escolaridade causa determinado salário (plano §4.5). As notas do
   glossário (`salario_relacao`, `dispersao_relacao`, `renda_ressalva`) já fazem essa
   ressalva e devem ser preservadas.
6. **Não comparar grupos com bases incompatíveis** (ex.: um grupo dominado por zeros
   contra um grupo sem zeros) sem explicitar a diferença de base.

---

## 11. Resumo executivo das decisões propostas (para aprovação na 3.2b/3.2c)

| Tema | Situação atual | Proposta (a aprovar) |
|---|---|---|
| Medida principal (páginas analíticas) | Média, incluindo zeros | **Mediana** |
| Média | Única medida exibida | Manter como **complemento rotulado** |
| Zeros | Incluídos na média | **Excluir** das estatísticas de salário |
| Unidade de pagamento | Todas misturadas | `salário` já é mensal; **manter todas**, sinalizar Semana/Tarefa |
| Extremos | Nenhum tratamento; média exposta | Mediana resolve; média aparada 5% opcional como sensibilidade |
| Conversão de periodicidade | — | **Nunca converter**: `salário` já vem mensalizado do MTE |
| n por grupo | Sem sinalização | **Sinalizar** grupos com n < 30 em recortes finos |
| Dados de origem | `salário`, `valorsaláriofixo`, `unidadesaláriocódigo` | **Preservados; nenhuma coluna de origem é sobrescrita** |

> **Status:** estas propostas foram **aprovadas e implementadas** nas etapas 3.2b (pipeline,
> colunas aditivas `salario_mediano_s0`, `salario_medio_s0`, `n_salario`, `n_salario_s0` e a
> tabela `salario_resumo`) e 3.2c (painel, mediana como manchete do salário e medida principal
> dos gráficos por escolaridade e macrofamília; média como complemento rotulado). As dispersões
> municipais mantêm a média, rotulada como tal, porque a mediana não é derivável de dados
> pré-agregados sem reabrir os microdados (decisão da Opção A, para preservar o desempenho das
> páginas analíticas validado na Fase A). Dados de origem preservados.
