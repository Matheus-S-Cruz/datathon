# Glossário de indicadores — Raio-X Industrial SC

> Arquivo gerado por `python -m src.glossario` a partir de `src/glossario.py`. Não edite à mão: edite o módulo e gere de novo.

## Fluxo do Novo CAGED

### Saldo de vagas formais

- **Coluna nos dados:** `saldo`
- **Onde aparece:** todas as páginas
- **Definição:** Diferença entre admissões e desligamentos com carteira assinada no período.
- **Fórmula:** admissões − desligamentos (soma de `saldomovimentação`, que vale +1 ou −1 por registro)
- **Unidade:** vagas (postos de trabalho formais)
- **Fonte:** Novo CAGED/MTE — microdados de movimentações de SC fornecidos pela organização do Datathon
- **Período:** set/2025 a ago/2026 (competência de declaração do Novo CAGED)
- **Abrangência:** Movimentações em municípios de SC; segue o recorte de setores, região e população mínima quando aplicado
- **Regras de filtragem:** Todos os registros da base (3.397.416); nenhuma exclusão
- **Limitações:** Mede fluxo (admissões e desligamentos), não o estoque de empregos nem vagas abertas; cada linha é uma movimentação, não uma pessoa

### Admissões

- **Coluna nos dados:** `admissoes`
- **Onde aparece:** todas as páginas
- **Definição:** Movimentações de entrada de trabalhadores com carteira assinada.
- **Fórmula:** nº de registros com `saldomovimentação` = +1
- **Unidade:** movimentações
- **Fonte:** Novo CAGED/MTE — microdados de movimentações de SC fornecidos pela organização do Datathon
- **Período:** set/2025 a ago/2026 (competência de declaração do Novo CAGED)
- **Abrangência:** Movimentações em municípios de SC; segue o recorte de setores, região e população mínima quando aplicado
- **Regras de filtragem:** Todos os registros de admissão; nenhuma exclusão
- **Limitações:** Mede fluxo (admissões e desligamentos), não o estoque de empregos nem vagas abertas; cada linha é uma movimentação, não uma pessoa

### Desligamentos

- **Coluna nos dados:** `desligamentos`
- **Onde aparece:** todas as páginas
- **Definição:** Movimentações de saída de trabalhadores com carteira assinada, por qualquer motivo.
- **Fórmula:** nº de registros com `saldomovimentação` = −1
- **Unidade:** movimentações
- **Fonte:** Novo CAGED/MTE — microdados de movimentações de SC fornecidos pela organização do Datathon
- **Período:** set/2025 a ago/2026 (competência de declaração do Novo CAGED)
- **Abrangência:** Movimentações em municípios de SC; segue o recorte de setores, região e população mínima quando aplicado
- **Regras de filtragem:** Todos os registros de desligamento; nenhuma exclusão
- **Limitações:** Mede fluxo (admissões e desligamentos), não o estoque de empregos nem vagas abertas; cada linha é uma movimentação, não uma pessoa

### Giro

- **Coluna nos dados:** `giro`
- **Onde aparece:** pipeline (outputs/), Território, Setores
- **Definição:** Volume total de movimentações (entradas mais saídas) no período.
- **Fórmula:** admissões + desligamentos
- **Unidade:** movimentações
- **Fonte:** Novo CAGED/MTE — microdados de movimentações de SC fornecidos pela organização do Datathon
- **Período:** set/2025 a ago/2026 (competência de declaração do Novo CAGED)
- **Abrangência:** Movimentações em municípios de SC; segue o recorte de setores, região e população mínima quando aplicado
- **Regras de filtragem:** Todos os registros; nenhuma exclusão
- **Limitações:** Mede fluxo (admissões e desligamentos), não o estoque de empregos nem vagas abertas; cada linha é uma movimentação, não uma pessoa. Numericamente igual a "movimentações"

### Movimentações

- **Coluna nos dados:** `movimentacoes`
- **Onde aparece:** todas as páginas
- **Definição:** Quantidade de registros (admissões e desligamentos) do grupo.
- **Fórmula:** nº de registros
- **Unidade:** movimentações
- **Fonte:** Novo CAGED/MTE — microdados de movimentações de SC fornecidos pela organização do Datathon
- **Período:** set/2025 a ago/2026 (competência de declaração do Novo CAGED)
- **Abrangência:** Movimentações em municípios de SC; segue o recorte de setores, região e população mínima quando aplicado
- **Regras de filtragem:** Todos os registros; nenhuma exclusão
- **Limitações:** Mede fluxo (admissões e desligamentos), não o estoque de empregos nem vagas abertas; cada linha é uma movimentação, não uma pessoa. Também é o peso usado nas médias ponderadas de recortes

## Indicadores normalizados

### Saldo por 10 mil habitantes (população do Censo 2022)

- **Coluna nos dados:** `saldo_por_10k`
- **Onde aparece:** Painel executivo, Território, Setores, Renda e escolaridade, Contexto regional (pipeline e services/analytics.py)
- **Definição:** Saldo de vagas proporcional ao tamanho da população, para comparar cidades de portes diferentes (métrica pedida no guia do Datathon).
- **Fórmula:** saldo ÷ população do Censo 2022 × 10.000; em recortes com vários municípios, soma dos saldos ÷ soma das populações × 10.000
- **Unidade:** vagas por 10 mil habitantes
- **Fonte:** Novo CAGED/MTE — microdados de movimentações de SC fornecidos pela organização do Datathon; Base municipal da organização (`Municipios_SC_limpo.csv`), coluna "População no último censo - pessoas [2022]" (IBGE, Censo 2022)
- **Período:** set/2025 a ago/2026 (competência de declaração do Novo CAGED)
- **Abrangência:** Movimentações em municípios de SC; segue o recorte de setores, região e população mínima quando aplicado
- **Regras de filtragem:** Todos os registros; filtro opcional de população mínima do município
- **Limitações:** A população é de 2022, anterior ao período do CAGED; municípios pequenos oscilam muito com poucas vagas. Difere da variante com população estimada 2026 usada no Explorador

### Saldo por 10 mil habitantes (população estimada 2026)

- **Coluna nos dados:** `saldo_10mil`
- **Onde aparece:** Municípios e Exploração estatística (services/queries.py, municipal_metrics)
- **Definição:** Mesma ideia do saldo por 10 mil habitantes, calculada sobre a população estimada de 2026.
- **Fórmula:** saldo ÷ população estimada 2026 × 10.000 (por município)
- **Unidade:** vagas por 10 mil habitantes
- **Fonte:** Novo CAGED/MTE — microdados de movimentações de SC fornecidos pela organização do Datathon; Base municipal da organização (`Municipios_SC_limpo.csv`), coluna "População estimada - pessoas [2026]" (IBGE)
- **Período:** set/2025 a ago/2026 (competência de declaração do Novo CAGED)
- **Abrangência:** Municípios de SC, com os filtros do Explorador aplicados antes de agregar
- **Regras de filtragem:** Filtros do formulário do Explorador (município, período, setor, ocupação etc.)
- **Limitações:** Usa população diferente da variante do painel (Censo 2022): o mesmo município mostra valores diferentes nas duas variantes. A escolha de um padrão está pendente

### Giro por 10 mil habitantes

- **Coluna nos dados:** `giro_por_10k`
- **Onde aparece:** Território (pipeline e services/analytics.py)
- **Definição:** Volume de movimentações proporcional à população; giro alto com saldo baixo indica reposição de trabalhadores.
- **Fórmula:** giro ÷ população do Censo 2022 × 10.000
- **Unidade:** movimentações por 10 mil habitantes
- **Fonte:** Novo CAGED/MTE — microdados de movimentações de SC fornecidos pela organização do Datathon; Base municipal da organização (`Municipios_SC_limpo.csv`), coluna "População no último censo - pessoas [2022]" (IBGE, Censo 2022)
- **Período:** set/2025 a ago/2026 (competência de declaração do Novo CAGED)
- **Abrangência:** Movimentações em municípios de SC; segue o recorte de setores, região e população mínima quando aplicado
- **Regras de filtragem:** Todos os registros; filtro opcional de população mínima do município
- **Limitações:** População de 2022. O Explorador tem a variante "movimentações por 10 mil habitantes" com população estimada 2026 (`mov_10mil`)

## Indicadores sobre o estoque (IBGE)

### Crescimento do emprego formal

- **Coluna nos dados:** `cresc_emprego_pct`
- **Onde aparece:** Painel executivo, Território, Contexto regional
- **Definição:** Quanto o emprego formal cresceu no período em relação ao estoque de assalariados de partida.
- **Fórmula:** saldo ÷ pessoal assalariado do CEMPRE 2024 × 100; em recortes, soma dos saldos ÷ soma dos assalariados × 100
- **Unidade:** % do estoque de assalariados
- **Fonte:** Novo CAGED/MTE — microdados de movimentações de SC fornecidos pela organização do Datathon; IBGE — Cadastro Central de Empresas (CEMPRE) 2024, SIDRA tabela 9509, pessoal ocupado assalariado
- **Período:** set/2025 a ago/2026 (competência de declaração do Novo CAGED)
- **Abrangência:** Municípios, regiões e o estado; indisponível com recorte setorial
- **Regras de filtragem:** Todos os registros; não calculado quando há filtro de setores (o CEMPRE municipal não é aberto por setor)
- **Limitações:** O CEMPRE 2024 antecede o período do CAGED e é uma aproximação do estoque; não substitui a RAIS

### Taxa de rotatividade

- **Coluna nos dados:** `rotatividade_pct`
- **Onde aparece:** Painel executivo, Território, Contexto regional
- **Definição:** Parte do fluxo que é troca de trabalhadores (reposição), e não criação líquida de vagas (conceito do DIEESE).
- **Fórmula:** mín(admissões, desligamentos) ÷ pessoal assalariado do CEMPRE 2024 × 100; em regiões e no estado, o mínimo é tirado dos totais somados
- **Unidade:** % do estoque de assalariados
- **Fonte:** Novo CAGED/MTE — microdados de movimentações de SC fornecidos pela organização do Datathon; IBGE — Cadastro Central de Empresas (CEMPRE) 2024, SIDRA tabela 9509, pessoal ocupado assalariado
- **Período:** set/2025 a ago/2026 (competência de declaração do Novo CAGED)
- **Abrangência:** Municípios, regiões e o estado; indisponível com recorte setorial
- **Regras de filtragem:** Todos os registros; não calculado quando há filtro de setores
- **Limitações:** Mesmo estoque aproximado do crescimento do emprego (CEMPRE 2024)

### Participação da indústria no valor adicionado (2021)

- **Coluna nos dados:** `part_industria_vab_2021`
- **Onde aparece:** Painel executivo (regiões), Contexto regional
- **Definição:** Peso da indústria na economia do município ou da região.
- **Fórmula:** VAB da indústria ÷ VAB total, a preços correntes de 2021; em regiões, soma dos VAB
- **Unidade:** fração (exibida em %)
- **Fonte:** IBGE — PIB dos Municípios, SIDRA tabela 5938 (valor adicionado bruto por atividade, 2021)
- **Período:** 2021
- **Abrangência:** Municípios e regiões de SC; não muda com os filtros
- **Regras de filtragem:** não se aplica
- **Limitações:** 2021 é o último ano com a abertura por atividade publicada para municípios; é anterior ao período do CAGED

## Escolaridade e renda

### Escolaridade média

- **Coluna nos dados:** `grau_medio`
- **Onde aparece:** Renda e escolaridade, Macrofamílias, Tabelas analíticas
- **Definição:** Nível médio de instrução das movimentações, numa escala ordenada.
- **Fórmula:** média da posição ordinal do grau de instrução: 1 (analfabeto) … 9 (superior completo), 10 (pós-graduação, código 80), 11 (mestrado), 12 (doutorado)
- **Unidade:** posição na escala de 1 a 12
- **Fonte:** Novo CAGED/MTE — microdados de movimentações de SC fornecidos pela organização do Datathon; Dicionário de dados oficial do Novo CAGED (`Dicionario_de_dados.xlsx`)
- **Período:** set/2025 a ago/2026 (competência de declaração do Novo CAGED)
- **Abrangência:** Movimentações em municípios de SC; segue o recorte de setores, região e população mínima quando aplicado
- **Regras de filtragem:** Exclui o código 99 (não identificado)
- **Limitações:** Escala ordinal: a distância entre níveis não é uniforme, então a média serve para comparar grupos, não para medir anos de estudo

### Com superior completo ou mais

- **Coluna nos dados:** `pct_superior`
- **Onde aparece:** Painel executivo, Macrofamílias, Tabelas analíticas
- **Definição:** Proporção das movimentações com ensino superior completo, pós-graduação, mestrado ou doutorado.
- **Fórmula:** nº com grau 9, 80, 10 ou 11 ÷ nº com grau identificado
- **Unidade:** fração (exibida em %)
- **Fonte:** Novo CAGED/MTE — microdados de movimentações de SC fornecidos pela organização do Datathon; Dicionário de dados oficial do Novo CAGED (`Dicionario_de_dados.xlsx`)
- **Período:** set/2025 a ago/2026 (competência de declaração do Novo CAGED)
- **Abrangência:** Movimentações em municípios de SC; segue o recorte de setores, região e população mínima quando aplicado
- **Regras de filtragem:** O código 99 (não identificado) fica fora do numerador e do denominador
- **Limitações:** Descreve quem foi admitido ou desligado, não a escolaridade de toda a força de trabalho

### Salário médio nas movimentações

- **Coluna nos dados:** `salario_medio`
- **Onde aparece:** Painel executivo, análises complementares, Tabelas analíticas
- **Definição:** Média do salário mensal declarado nas admissões e desligamentos (definição atual, em revisão na etapa 3.2 do projeto).
- **Fórmula:** média aritmética de `salário` de todos os registros do grupo; em recortes, média dos grupos ponderada pelo nº de movimentações
- **Unidade:** R$ por mês
- **Fonte:** Novo CAGED/MTE — microdados de movimentações de SC fornecidos pela organização do Datathon; Dicionário de dados oficial do Novo CAGED (`Dicionario_de_dados.xlsx`) (`salário` = salário mensal declarado)
- **Período:** set/2025 a ago/2026 (competência de declaração do Novo CAGED)
- **Abrangência:** Movimentações em municípios de SC; segue o recorte de setores, região e população mínima quando aplicado
- **Regras de filtragem:** Nenhuma exclusão: inclui salários zerados e todas as periodicidades de pagamento
- **Limitações:** Inclui 33.912 salários iguais a zero; registros cujo valor não é mensal (parte fixa paga por semana ou por tarefa); e periodicidades quase sempre sem valor (variável, não identificado). 535 valores acima de R$ 50 mil puxam a média

## Classificação

### Macrofamília de ocupações

- **Coluna nos dados:** `cbo_grande_grupo`
- **Onde aparece:** Painel executivo, Macrofamílias, Tabelas analíticas
- **Definição:** Agrupamento analítico do projeto: ocupações reunidas pelo Grande Grupo da CBO-2002.
- **Fórmula:** 1º dígito do código CBO de 6 dígitos; os grupos 7 e 8 formam a macrofamília operacional; nomes atribuídos pelo projeto
- **Unidade:** não se aplica
- **Fonte:** Novo CAGED/MTE — microdados de movimentações de SC fornecidos pela organização do Datathon (`cbo2002ocupação`); estrutura da CBO-2002
- **Período:** set/2025 a ago/2026 (competência de declaração do Novo CAGED)
- **Abrangência:** Santa Catarina inteira; versão só com seções industriais (B, C, D, F)
- **Regras de filtragem:** Todas as ocupações; códigos sem 1º dígito válido ficam como "Não classificado"
- **Limitações:** Não é a nomenclatura oficial da CBO: usa nomes próprios e funde os grupos 7 e 8

## Referência

### Período de referência

- **Definição:** Intervalo de meses coberto pelos dados do Novo CAGED usados no projeto.
- **Fórmula:** não se aplica
- **Unidade:** meses (competência)
- **Fonte:** Novo CAGED/MTE — microdados de movimentações de SC fornecidos pela organização do Datathon
- **Período:** set/2025 a ago/2026 (competência de declaração do Novo CAGED)
- **Abrangência:** Todas as páginas
- **Regras de filtragem:** Competência de declaração; declarações fora do prazo entram pelo mês em que foram declaradas
- **Limitações:** Por competência de movimentação, há registros desde set/2024 (declarações fora do prazo)

## Notas de método exibidas no painel

- **mapa_formulas** (Saldo por 10 mil habitantes (população do Censo 2022), Crescimento do emprego formal): Saldo por 10 mil hab. = (admissões − desligamentos) ÷ população × 10.000. Crescimento do emprego = saldo ÷ assalariados do CEMPRE 2024 × 100 (só sem recorte setorial).
- **limite_fluxo** (Saldo de vagas formais): Limite: o CAGED mede fluxo de admissões e desligamentos, não o estoque de empregos.
- **regioes_formulas** (Crescimento do emprego formal, Taxa de rotatividade): Crescimento = saldo ÷ assalariados do CEMPRE 2024 × 100. Rotatividade = mín(admissões, desligamentos) ÷ assalariados × 100 (conceito DIEESE): a parte do fluxo que é troca de trabalhadores, não vaga nova.
- **regioes_leitura** (Crescimento do emprego formal, Taxa de rotatividade): Leitura: regiões no alto e à esquerda trocam muitos trabalhadores sem crescer — sinal de dificuldade de reter mão de obra. Limite: o CEMPRE 2024 é uma aproximação do estoque.
- **macro_agrupamento** (Macrofamília de ocupações): Agrupamento determinístico pelo 1º dígito do código CBO-2002 (Grande Grupo); os grupos 7 e 8 formam a macrofamília operacional.
- **macro_salario** (Salário médio nas movimentações): Salário médio inclui todos os salários declarados (ver limites no fim da página).
- **salario_relacao** (Salário médio nas movimentações): Relação descritiva: mostra quanto cada grupo recebe em média, não que a escolaridade cause a diferença. Limite: a média inclui salários zerados e não mensais.
- **dispersao_relacao** (Salário médio nas movimentações, Com superior completo ou mais, Saldo por 10 mil habitantes (população do Censo 2022)): Relação descritiva entre três medidas do mesmo município; não indica causa.
- **renda_ressalva** (Salário médio nas movimentações): Ressalva metodológica: as médias incluem salários informados como zero e valores de periodicidade não mensal (sobretudo por hora; também por dia, semana, tarefa ou variável).
