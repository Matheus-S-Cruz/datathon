1

## DATATHON 2026 GUIA DO PARTICIPANTE —

Raio-X do Mercado de Trabalho e Vagas Industriais

em Santa Catarina

Como parte das atividades da Semana Acadêmica (10 a 13 de novembro), o Datathon: Raio-X do Mercado de Trabalho e Vagas Industriais em SC é um desafio prático de análise de dados e inteligência artificial.

O mercado de trabalho do estado de Santa Catarina apresenta dinâmicas econômicas intensas e dados públicos ricos. Este desafio propõe transformar microdados públicos brutos em um Painel de Inteligência Operacional e Territorial de Pessoas para o setor industrial, unindo as turmas de 2ª e 4ª fase do Bacharelado em Ciência de Dados e Inteligência Artificial em uma experiência de colaboração multidisciplinar.

Cada equipe atuará como uma consultoria de dados especializada, contratada por uma entidade de classe (como a Federação das Indústrias) ou por um grande grupo empresarial privado.

A atuação da consultoria deve responder com clareza à seguinte Pergunta Central de Negócio:

“Quais regiões e setores industriais de Santa Catarina estão enfrentando apagão de mão de obra ou expansão acelerada, e como os indicadores de renda e escolaridade explicam esses gargalos?”

Para responder a essa pergunta, a equipe deverá consumir, tratar, enriquecer e visualizar os microdados do Novo CAGED referentes ao estado de Santa Catarina, gerando diagnósticos precisos e recomendações acionáveis.

## 1. Apresentação e Contexto

## 2. Desafio e Pergunta Central de Negócio

## 2.1. O Cenário de Negócio

Santa Catarina possui uma das menores taxas de desemprego do país e um parque industrial altamente diversificado — desde o polo têxtil do Vale do Itajaí e o setor metalmecânico do Norte, até a agroindústria do Oeste e o setor eletroeletrônico/tecnológico da Grande Florianópolis e Sul. Esse dinamismo gera dois cenários opostos e igualmente críticos para a tomada de decisão:

- Sinais de Apagão de Mão de Obra: Regiões ou setores com alta demanda por trabalhadores, mas que enfrentam escassez de profissionais qualificados ou forte rotatividade (turnover).


- Polos de Expansão Acelerada: Regiões que concentram um saldo vertiginoso de novas vagas, pressionando a infraestrutura local, as exigências de qualificação e as faixas salariais regionais.

O papel da sua equipe não é apenas listar números, mas conectar os pontos: entender se a escassez se deve à falta de qualificação (escolaridade), à desatratividade financeira (faixa salarial) ou a transformações estruturais de determinado setor.

## 2.2. Eixos de Investigação (Ponto de Partida)

Para estruturar a análise sem se perder na imensidão dos microdados, a equipe pode orientar seus trabalhos a partir de três eixos fundamentais:

- Eixo Territorial e Setorial: Como as movimentações trabalhistas estão distribuídas pelo mapa catarinense? Existem municípios ou regiões concentrando o saldo positivo do estado enquanto outros encolhem? Quais setores industriais lideram esses movimentos?

- Eixo de Perfil Socioeconômico: Qual é o perfil do profissional que está sendo admitido versus o que está sendo desligado? O mercado está contratando profissionais mais instruídos e pagando mais, ou há uma compressão salarial em cargos que exigem maior escolaridade?

- Eixo de Qualificação e IA (Agrupamento de CBOs): Os cargos em escassez exigem formação técnica/engenharia ou referem-se a funções operacionais de base? A aplicação de IA para agrupar as centenas de CBOs em macrofamílias será crucial para revelar padrões que dados brutos não mostram.

## 2.3. O Resultado Esperado (Visão do Entregável)

Ao final do desafio, a banca avaliadora não busca apenas um código funcional ou um gráfico isolado, mas uma solução analítica integrada (Data Storytelling).

A solução ideal deve permitir que um diretor ou gestor público abra o dashboard da equipe e consiga:

- 1. Localizar o problema rapidamente: Identificar intuitivamente no painel visual quais microrregiões e setores industriais demandam atenção urgente.

- 2. Entender a causa raiz: Navegar pelos indicadores para compreender se o gargalo é motivado por desparidade salarial, exigência de escolaridade não atendida ou alta rotatividade.

- 3. Tomar uma decisão: Ler recomendações práticas no pitch executivo que indiquem caminhos concretos (ex.: ações de formação profissional direcionadas, revisão de faixas salariais ou incentivos para atração de talentos regionais).

A organização do evento disponibilizará três arquivos principais:

## 3. Insumos e Bases de Dados Fornecidas


- 1. Novo_Caged_MOV_Limpo.csv: Contém os relatórios do Novo CAGED dos últimos 12 meses no estado de Santa Catarina. Inclui dados de município, CBO, salário, grau de instrução, setor econômico (CNAE) e o saldo da movimentação (admissão ou demissão).

- 2. Municipios_SC_limpo.csv: Dados demográficos dos municípios do estado de Santa Catarina. Devem ser cruzados com os dados do Novo Caged para obter insights sobre a empregabilidade local.

- 3. Dicionario_dados: Arquivo de referência contendo a definição e os metadados de cada campo presente nas bases.

## 4. Dinâmica do Evento e Divisão de Papéis

As equipes serão formadas obrigatoriamente por uma composição mista de estudantes da 2ª fase e da 4ª fase. Cada equipe deverá ser formada por 5 integrantes, sendo 2 estudantes de 4ª fase e 3 estudantes de 2ª fase.

O líder do grupo deve fazer a inscrição no formulário a seguir:

[https://forms.gle/z1JtegGp9KoKKgza8](https://forms.gle/z1JtegGp9KoKKgza8)

| Etapa | Papel Técnico / Dados | Papel IA & Negócios |
| --- | --- | --- |
| Ingestão e | Carregar arquivos em Python | Entender a estrutura das |
| Validação | (Pandas/Polars), verificar | tabelas, consultar |
|   | schemas, tratar inconsistências | dicionários de dados e |
|   | e aplicar a filtragem das | validar o escopo da |
|   | exclusões (MOV x EX). | pergunta de negócio. |
| Cruzamento | Realizar o merge/join entre a | Modelar a métrica de |
| Relacional | base do CAGED e os dados | "Saldo de Vagas por |
|   | territoriais/IBGE via chave | 10.000 Habitantes" |
|   | municipio_codigo. | para normalizar a |
|   |   | comparação entre |
|   |   | cidades. |
| Enriquecimento | Estruturar scripts para | Desenvolver e testar |
| com IA | chamadas de API de IA | prompts em LLMs para |
|   | Generativa ou | agrupar mais de 200 |
|   | exportação/importação de | CBOs em macrofamílias. |
|   | amostras textuais. |   |


| Análise e | Gerar agregações de dados por | Desenhar o layout do |
| --- | --- | --- |
| Visualização | região/setor e criar gráficos | dashboard (Power BI / |
|   | analíticos base em Python | Streamlit) focando no |
|   | (Seaborn/Plotly). | storytelling dos |
|   |   | resultados. |
| Pitch Executivo | Explicar a metodologia de | Apresentar o diagnóstico |
|   | dados, volumetria, tratamento e | final, os gargalos |
|   | limites da análise. | encontrados e as |
|   |   | recomendações práticas |
|   |   | para a indústria. |

Nota: É permitida e incentivada a utilização de ferramentas de IA Generativa em todas as etapas do desenvolvimento.

## 5. Cronograma de Execução

O Datathon ocorrerá em dois dias durante a Semana Acadêmica:

- 08:30 – 09:00 | Alinhamento geral do desafio e formação oficial das equipes

- 09:00 – 10:00 | Limpeza, aplicação de filtros (EX), tratamento e junção das bases de dados

- 10:00 – 11:00 | Enriquecimento e categorização de CBOs via IA Generativa

- 11:00 – 11:40 | Construção das visualizações de dados

- 08:30 – 09:30| Construção das visualizações de dados e consolidação do Dashboard

- 09:30 – 10:00| Estruturação da narrativa e preparação do Pitch

- 10:00 - 10:30 | Intervalo e deslocamento para o auditório

- 10:30– 11:30 | Apresentações executivas (Pitches) de 3 minutos e avaliação pela banca de especialistas

Ao final do segundo dia, cada equipe deverá submeter formalmente, no formato de um repositório Git público (GitHub, GitLab, Bitbucket, etc.):

- 1. Jupyter Notebook / Script (.ipynb ou .py): Código-fonte documentado contendo todo o pipeline de tratamento de dados, desde a carga inicial e exclusão de registros inválidos até a comunicação com a API de IA/prompts e exportação final.

- 2. Dashboard Analítico (Python): Painel visual interativo contendo, no mínimo, 3 indicadores chave essenciais para a tomada de decisão da indústria.

## Dia 1

## Dia 2

## 6. Entregáveis Obrigatórios


- 3. Pitch Executivo (3 minutos): Apresentação oral e visual objetiva direcionada à banca avaliadora.

A entrega dos projetos será feita exclusivamente pelo formulário

[https://forms.gle/BPtrKNwuPEc5Zr1k7.](https://forms.gle/BPtrKNwuPEc5Zr1k7)

## 7. Critérios de Avaliação

A avaliação final das equipes considerará cinco dimensões estratégicas:

- Escopo: Avalia o entendimento do contexto industrial de Santa Catarina e a capacidade de responder com precisão à pergunta central de negócio.

- Pontos de Observação para os Participantes:

- Demonstrem domínio sobre o cenário econômico e a dinâmica do parque industrial catarinense;

- Alinhem o diagnóstico diretamente à Pergunta Central de Negócio e às necessidades do setor contratante;

- Evidenciem a coerência da solução proposta frente à estrutura e granularidade dos dados do Novo CAGED.

- Escopo: Avalia a profundidade técnica e a consistência metodológica das evidências extraídas dos dados.

- Pontos de Observação para os Participantes:

- Relacionem de forma consistente os indicadores de renda e escolaridade com o cenário de escassez (apagão) ou expansão de mão de obra;

- Apresentem de forma transparente as premissas adotadas e os limites da análise realizada.

- Escopo: Avalia a qualidade, a funcionalidade e o apelo visual das interfaces analíticas construídas.

- Pontos de Observação para os Participantes:

- Destaquem visualmente no painel os KPIs essenciais para a tomada de decisão;

- Utilizem representações gráficas adequadas (mapas, barras, dispersão) para ilustrar os recortes territoriais e setoriais;

- Conduzam uma narrativa visual fluida, permitindo que a banca acompanhe o diagnóstico diretamente pela interface.

- Escopo: Avalia a capacidade de converter análises técnicas em estratégias aplicáveis ao mercado industrial.

## 1. Compreensão do Problema e Contexto Industrial

## 2. Embasamento Analítico e Diagnóstico

## 3. Dashboard e Storytelling

## 4. Recomendações e Valor de Negócio


- Pontos de Observação para os Participantes:

- Demonstrem a originalidade, a viabilidade e o valor de mercado das soluções sugeridas;

- Estabeleçam uma conexão lógica direta entre as recomendações finais e os agrupamentos de CBOs/macrofamílias gerados por IA.

## 5. Comunicação e Pitch

- Escopo: Avalia o desempenho performático da equipe durante a apresentação executiva.

- Pontos de Observação para os Participantes:

- Comuniquem-se com clareza, objetividade e poder de síntese, mantendo tom executivo;

- Gerenciem o tempo de forma rigorosa, respeitando o limite de apresentação de 3 minutos;
