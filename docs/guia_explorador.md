# Guia das páginas de exploração — Pulso Industry

Guia de uso para toda a equipe, inclusive quem não usa SQL nem estatística no dia a dia.
Para instalar e abrir a aplicação, veja o [README](../README.md#como-rodar)
(`streamlit run dashboard/app.py` e depois <http://localhost:8501>).

## O que é (e o que não é)

As páginas de exploração do Pulso Industry servem para **entender e conferir os dados** antes da
modelagem. Todos os números são calculados na hora, a partir dos arquivos em `data/`. Elas **não** trazem
índice de escassez,
ranking definitivo de municípios, previsões nem recomendações automáticas. Essas etapas vêm depois.

> **Onde fica no dashboard:** as páginas deste guia estão nas seções **Exploração e consulta**
> (Explorador, Municípios, Dicionário, Bases e validação) e **Análises complementares** (Exploração
> estatística, Relações, Auditoria) do menu. A antiga "Visão geral" do explorador agora se chama
> **Bases e validação**; a **Visão geral** do menu é o painel executivo (ver `dashboard/README.md`).

Três ideias para ter em mente em todas as páginas:

1. **Cada linha do CAGED é uma movimentação**: uma admissão (+1) ou um desligamento (−1).
   Não é uma pessoa nem uma vaga.
2. O CAGED mede **fluxo**, não estoque: não diz quantas pessoas estão empregadas nem quantas vagas
   estão abertas.
3. **Correlação não é causa.** Quando duas variáveis andam juntas, pode haver uma terceira por trás.

## Navegação e filtros

- O **menu lateral** lista as 7 páginas, em dois grupos: *Bases* e *Validação e exploração*.
- Nas páginas que consultam o CAGED, os **filtros** ficam na barra lateral, dentro de um quadro.
  Escolha os valores e clique em **Aplicar filtros**: nada é consultado antes disso.
- Logo abaixo do título aparece a linha **"Filtros ativos"**, com o que está valendo.
- Os códigos aparecem com a **descrição oficial do dicionário** (ex.: `40 · Desligamento a pedido`).
  Quando o dicionário não tem a descrição, aparece *(sem descrição no dicionário)*. Nenhum
  significado é inventado.
- **Competência**: escolha entre *Declaração* (mês em que a empresa informou; exatamente 12 meses)
  e *Movimentação* (mês em que o fato ocorreu; inclui 36.940 declarações fora do prazo de meses
  anteriores). Depois de trocar a opção, clique em *Aplicar filtros* para atualizar a régua de período.
- Os botões **Baixar tabela (CSV)** geram arquivos com separador `;` e decimal `,`, que abrem
  direto no Excel em português.

### Selos e cores

| Selo | Significado |
|---|---|
| **Constatação verificada** (azul) | Número medido agora nos arquivos. |
| **Hipótese** (violeta) | Interpretação plausível, ainda não comprovada. |
| **Limitação** (laranja) | Característica da base que restringe a análise. |
| **Resultado exploratório** (cinza) | Descrição de uma distribuição, sem juízo de qualidade. |
| *Situação: …* | Resolvido, Sem ação necessária, Tratado no app (falta no pipeline), Pendente ou Exige validação externa. |

Nos gráficos, **azul = admissões** e **laranja = desligamentos**. As cores identificam o tipo de
movimento; **não** significam "bom" ou "ruim". O saldo usa as mesmas cores pelo sinal. A paleta foi
validada para daltonismo nos temas claro e escuro.

---

## 1. Bases e validação (antiga Visão geral)

**O que mostra**

- **Indicadores do período**: admissões, desligamentos, saldo (admissões − desligamentos),
  municípios com movimentação, seções CNAE e ocupações (CBO) distintas.
- **Gráfico "Por mês"**: admissões e desligamentos lado a lado em cada mês. Use o seletor
  *Declaração/Movimentação* para trocar a competência.
- **Saldo mensal**: barras acima de zero = mais admissões que desligamentos naquele mês. A queda de
  dezembro é sazonal (fim de ano) e aparece todos os anos no CAGED.
- **Bases de dados**: arquivo, tamanho e **data da última atualização** de cada base.
- **Situação da validação**: 8 checagens rápidas (ex.: nº de registros = 3.397.416, todos os
  municípios com correspondência). Se alguma falhar, aparece um aviso.

## 2. Explorador do Novo CAGED

É a página para olhar os registros um a um.

**Pesquisar e filtrar por valores** (quadro no topo)

- **Coluna pesquisada + Modo + Texto**: procura um texto em uma coluna (ou em todas). Modos:
  *contém*, *igual* e *começa com*. Maiúsculas e minúsculas são tratadas como iguais.
  A base guarda **códigos**, não nomes: para achar Joinville, use o filtro *Município* da barra
  lateral, ou pesquise o código `420910`.
- **Filtrar valores da coluna**: escolha qualquer coluna e marque os valores desejados (com a
  contagem de cada um). Funciona para colunas com até 400 valores distintos. Para as demais
  (CBO, subclasse), use a pesquisa por texto ou os filtros laterais.

**Aba "Tabela paginada"**

- Mostra os registros com os **nomes originais das colunas** e os **valores exatamente como estão
  no arquivo** (texto, com vírgula decimal).
- **linha** = posição do registro no arquivo Parquet. É o identificador usado em todas as páginas de exploração.
- *Colunas exibidas*, *Ordenar por* (salário, idade e horas são ordenados pelo número, não pelo
  texto), *Decrescente*, *Registros por página* (25 a 500) e *Página*.
- Só a página visível é enviada ao navegador; a contagem total aparece acima.
- Marque a caixa à esquerda de uma linha para abri-la na aba *Registro individual*.
- **Exportar resultados filtrados**: clique em *Preparar arquivo* e depois em *Baixar CSV*. O limite
  é de 500.000 linhas por arquivo; refine os filtros se precisar de tudo.

**Aba "Amostras"**

- *Primeiros registros*: as primeiras linhas do filtro, na ordem do arquivo. **Não** é
  representativa, porque o arquivo está ordenado por mês.
- *Amostra aleatória simples*: sorteio sem reposição entre todos os registros filtrados. A mesma
  **semente** com os mesmos filtros reproduz a mesma amostra.

**Aba "Registro individual"**

Para cada uma das 30 colunas de uma linha: o valor original, o valor convertido (ex.: `2018,00` →
R$ 2.018,00), o significado do código no dicionário, o tipo identificado e a descrição do campo.

**Aba "Estrutura das colunas"**

Tipo armazenado (todas as colunas são texto), tipo identificado, nome da coluna convertida usada nas
consultas, aba de códigos do dicionário e descrição oficial.

## 3. Municípios

- **Tabela**: os 295 municípios com todos os indicadores e o total de movimentações e o saldo no
  CAGED. Pesquise por nome ou código (7 dígitos do IBGE ou 6 do CAGED) e ordene por população,
  PIB per capita, IDHM etc. `—` = valor ausente no arquivo.
- **Valores ausentes**: quantos `-` há em cada indicador (IDHM: 2; mortalidade infantil: 123) e
  quais municípios são afetados.
- **Registro completo**: o valor original do arquivo ao lado do valor interpretado, mais o código
  usado no CAGED e a validação do dígito verificador do IBGE.
- **Gráficos exploratórios**: distribuição da população (escala logarítmica opcional), do PIB per
  capita e do IDHM; dispersões população × PIB per capita e PIB per capita × IDHM; tabela com
  Pearson e Spearman.

Cuidados: o IDHM é de **2010** e o PIB per capita de **2023**. O rodapé do CSV indica anos de
referência diferentes dos cabeçalhos (ver auditoria, A14). A coluna *Prefeito* não é exibida
(dado pessoal sem uso analítico).

## 4. Dicionário de dados

- **Campos e utilização**: uma linha por campo, nas colunas
  `Campo | Tipo identificado | Descrição | Formato | Aba de códigos | Base | Utilização`.
  As descrições vêm da aba `Layout`. "Utilização" resume `docs/dicionario_analitico.md`.
  Também aparecem as colunas da base municipal (sem descrição no dicionário) e os campos do
  dicionário que **não existem** no CAGED (`competênciaexc`, `indicadordeexclusão`).
- **Consultar uma aba**: mostra qualquer uma das 23 abas. Nas abas de códigos, a coluna
  *registros no CAGED* indica quantas vezes cada código aparece na base.
- **Pesquisar códigos e descrições**: procura um código ou palavra em todas as abas (ex.: `soldador`).
- **Cobertura dos códigos**: códigos presentes no CAGED que não estão no dicionário (28 CBOs e
  1 subclasse).

## 5. Resultados da auditoria

Recalcula **31 constatações** a partir dos arquivos. Na primeira abertura, isso leva cerca de 30 s;
depois fica em cache. Os indicadores do topo mostram quantas constatações reproduzem o valor
publicado em `docs/diagnostico_inicial.md`. Na versão atual, são **28 de 28**.

Cada cartão responde:

1. **O que foi encontrado**: o número medido agora.
2. **Como foi calculado**: no expansor, com o SQL exato.
3. **Registros envolvidos**.
4. **Por que importa**.
5. **Tratamento ou investigação recomendada**.
6. **Situação**: selo.

Quando há uma interpretação ainda não comprovada, ela aparece separada, com o selo **Hipótese**.

| Aba | Conteúdo |
|---|---|
| A. Integridade | Ausentes, tipos (tudo é texto), linhas idênticas, zeros à esquerda, coerência saldo × tipo, fora do prazo, admissões sem subtipo, porte em 202608, exclusões ausentes, escolaridade 80, colunas constantes, EmpregadoWEB, estrutura e anos da base municipal. |
| B. Distribuição | Admissões × desligamentos e distribuição por competência, município, seção CNAE, CBO e escolaridade, com gráficos. |
| C. Remuneração | Salários zerados, extremos, quartis, histograma (ajustável; separa admissões e desligamentos), salário por unidade de pagamento, admitidos × desligados, salário = salário fixo. |
| D. Relacionamentos | Formato dos códigos municipais, correspondência CAGED × municípios, cobertura do dicionário, colunas × variáveis e a chave `municipio_codigo` citada no guia. |

Use os filtros *Natureza* e *Situação* para ver, por exemplo, só o que está pendente. O
*Resumo em tabela* pode ser baixado em CSV.

Destaques desta versão:

- **A3 — Linhas idênticas**: 97.635 linhas repetem outra em todas as colunas. Isso é uma
  constatação. Dizer que são duplicidades indevidas seria hipótese: contratações em lote geram
  linhas iguais legítimas. Recomendação: não remover.
- **A12 — EmpregadoWEB**: a hipótese da auditoria inicial foi **confirmada**. Os 510 registros com
  origem 3 são exatamente os de categoria 999, horas 0 e intermitente 9.
- **B2 — Saldo de dezembro**: −48.616 pela competência da **movimentação** (valor citado no
  diagnóstico) e −47.676 pela competência da **declaração**. O diagnóstico não dizia qual
  competência usou; o cartão mostra as duas.

## 6. Exploração estatística

Escolha o **nível de análise**:

- **Registros do CAGED**: variáveis X e Y entre salário, salário fixo, idade e horas contratuais.
  - *Estatísticas descritivas* (n, média, mediana, moda, desvio-padrão, mínimo, quartis, máximo),
    calculadas sobre **todos** os registros filtrados. A legenda informa quantos ficaram de fora por
    falta de valor (ex.: 2.202 idades vazias).
  - *Relação entre X e Y*: Pearson, Spearman e o número de pares usados, com uma frase que
    interpreta o resultado. O gráfico usa uma **amostra aleatória** de até 10 mil pontos, sinalizada.
    Os números usam todos os pares.
  - *Tabela agregada por categoria*: a variável escolhida resumida por grau de instrução, seção,
    faixa salarial etc.
- **Municípios**: uma observação por município, combinando indicadores da base municipal
  (população, PIB per capita, IDHM…) e agregados do CAGED filtrado (saldo, saldo por 10 mil
  habitantes, mediana salarial de admissão…). Use *Mínimo de movimentações* para tirar municípios
  muito pequenos, cujas taxas oscilam muito.

**Como ler**

- **Média × mediana**: se a média é bem maior que a mediana, há valores extremos puxando para cima.
  É o caso do salário: média de R$ 2.478,58 e mediana de R$ 2.155.
- **Pearson** mede relação em linha reta; **Spearman** mede se a ordem acompanha. Os dois vão de
  −1 a +1. Faixas usadas (convenção): até 0,1 praticamente nula; até 0,3 fraca; até 0,5 moderada;
  até 0,7 forte; acima disso, muito forte.
- Só variáveis quantitativas aparecem em X e Y. Códigos (CBO, CNAE, escolaridade) são categorias:
  correlacioná-los como números não tem significado. Para eles, use a tabela agregada.
- Marque **Excluir salários zerados** nos filtros ao analisar salário.

## 7. Relações territoriais e setoriais

1. Escolha o **nível de agrupamento**: Município × Divisão CNAE, Município × CBO, Divisão CNAE ×
   Escolaridade, CBO × Escolaridade, Município × Divisão CNAE × CBO, ou *Personalizado* (até 3
   dimensões, incluindo faixa salarial e competência).
2. Defina o **mínimo de movimentações por grupo** (padrão 30) para evitar medianas instáveis.
3. Leia as abas:
   - **Tabela agregada**: movimentações, admissões, desligamentos, saldo, desligamentos a pedido,
     medianas salariais (geral, de admissões e de desligamentos; sem zeros), ocupações distintas,
     % com médio completo e % com superior completo ou mais. Baixe em CSV.
   - **Gráficos**: admissões × desligamentos e saldo dos maiores grupos; dispersão saldo × mediana
     salarial de admissão (cada ponto é um grupo); e, com 2 dimensões, um **mapa de calor**
     (ex.: município × divisão CNAE).
   - **Distribuição educacional**: barras 100% empilhadas da escolaridade nos maiores grupos, em
     6 faixas (até fundamental incompleto; fundamental completo/médio incompleto; médio completo;
     superior incompleto; superior completo; pós/mestrado/doutorado), com tabela dos 12 níveis
     originais.

Tudo aqui é **descritivo**. Um grupo com saldo alto e salário de admissão alto **não** prova
escassez nem expansão: pode ser sazonalidade, composição de ocupações ou um mês atípico.

---

## Perguntas frequentes

**Por que a busca por "Joinville" não encontra nada?** Porque o CAGED guarda o código do município
(`420910`). Use o filtro *Município* da barra lateral, que mostra os nomes.

**Por que a primeira abertura de algumas páginas demora?** Os cálculos rodam sobre 3,4 milhões de
linhas. Os resultados ficam em cache, e as próximas aberturas são quase instantâneas.

**Os números estão diferentes da auditoria?** A página *Resultados da auditoria* compara cada
número com o valor publicado. Divergências aparecem com o selo laranja *Diverge da auditoria
inicial*.

**Atualizei um arquivo de dados. O que faço?** Nada: o Pulso Industry percebe a mudança e recalcula. Veja
*Como adicionar ou atualizar as bases* no README.
