# Dicionário analítico

> Mapeamento entre cada campo das bases, o que ele significa, como está armazenado,
> quais valores foram **observados** e para que serve na análise.
>
> - **Descrição oficial**: copiada da aba `Layout` de `data/reference/Dicionario_de_dados.xlsx`.
> - **Valores observados**: medidos em 10/11/2026 com `src/validation/profile_sources.py`
>   (relatório completo em `reports/perfil_bases.md`).
> - Itens marcados com **(H)** são hipóteses ainda não confirmadas.

Legenda dos eixos: **T** = Territorial/Setorial · **S** = Socioeconômico · **Q** = Qualificação/IA ·
**C** = Controle de qualidade/filtro · **—** = sem uso previsto.

---

## 1. Novo CAGED — `data/raw/Novo_Caged_MOV_Limpo.parquet`

3.397.416 registros · 30 colunas · **todas armazenadas como texto (VARCHAR)** · nenhum valor nulo
(apenas `idade` tem strings vazias). Cada linha é **uma movimentação** (uma admissão ou um
desligamento de um vínculo), não uma pessoa e não uma vaga.

### 1.1 Campos-chave para a análise

| Campo | Descrição oficial | Tipo esperado → tratamento | Valores observados | Uso analítico | Eixo |
|---|---|---|---|---|---|
| `saldomovimentação` | Valor da movimentação em termos de saldo | inteiro | `1` (1.719.449) e `-1` (1.677.967) | **Base de tudo**: admissão = +1, desligamento = −1. Saldo = soma. | T S Q |
| `tipomovimentação` | Tipo de movimentação | código (aba `tipomovimentação`) | 11 códigos. Admissões: `97` Tipo Ignorado (1.718.686), `35` Reintegração (763). Desligamentos: `40` A pedido (789.699), `31` Sem justa causa (557.140), `43` Término de contrato prazo determinado (270.794), `32` Com justa causa (36.881), `90` Acordo (17.419), `60` Morte (4.215), `98` Tipo ignorado (1.515), `50` Aposentadoria (275), `33` Culpa recíproca (29) | Motivo do desligamento (pedido × demissão) é o principal sinal de mercado aquecido. **Admissões não têm subtipo** (primeiro emprego/reemprego ausentes). | T S Q |
| `competênciadec` | Competência da declaração | AAAAMM → data | 12 meses: 202509 a 202608 (232 mil a 326 mil registros/mês) | Define a janela de 12 meses do desafio. | T C |
| `competênciamov` | Competência da movimentação | AAAAMM → data | 24 valores: 202409 a 202608. 98,9% coincidem com `competênciadec`. | Mês em que a movimentação ocorreu. Usar para séries temporais (decisão pendente, ver diagnóstico E). | T C |
| `indicadordeforadoprazo` | Informação declarada fora do prazo | 0/1 | `1` em 36.940 registros (1,09%) — exatamente os casos em que `competênciamov ≠ competênciadec` | Identificar movimentações atrasadas. | C |
| `município` | Código do Município | texto de 6 dígitos (manter como texto) | 295 códigos distintos, todos de SC (420005 a 422000), todos presentes no dicionário | **Chave de junção** com a base municipal (ver seção 3). | T |
| `seção` | Seção da CNAE 2.0 | letra (aba `seção`) | 22 seções. `C` Indústria de Transformação: 836.753 registros | Recorte setorial macro; define o escopo "industrial". | T |
| `subclasse` | Subclasse da CNAE 2.0 | texto de 7 dígitos → `lpad(…, 7, '0')` | 1.149 distintas. 105.072 registros com 6 dígitos (zero à esquerda perdido); 1 código fora do dicionário (`8630505`, 13 registros) | Os 2 primeiros dígitos dão a **divisão CNAE** (ex.: 10 Alimentos, 13 Têxteis, 14 Vestuário, 28 Máquinas), que é o recorte setorial industrial mais útil. | T |
| `cbo2002ocupação` | Ocupação (CBO 2002) | texto de 6 dígitos → `lpad(…, 6, '0')` | 2.207 distintas (1.467 na seção C). 8 registros com 5 dígitos; `999999` Não identificado em 146; 28 códigos (2.117 registros) **não constam** do dicionário | Base do agrupamento em macrofamílias. A estrutura hierárquica da CBO (1º dígito = grande grupo; 4 dígitos = família) **(H: confirmar na documentação oficial do MTE)** ajuda a classificar de forma rastreável. | Q |
| `graudeinstrução` | Grau de instrução | código ordinal (aba `graudeinstrução`) | 12 códigos: 1 a 11 e `80` Pós-Graduação completa (33.303). Moda: `7` Médio Completo (2.032.882 = 59,8%). Não há `99`. | Perfil educacional de admitidos × desligados. **Atenção**: `80` não segue a ordem numérica; criar ordem explícita (… 9 Superior completo < 80 Pós < 10 Mestrado < 11 Doutorado). | S Q |
| `salário` | Salário mensal declarado | decimal com vírgula → `replace(',', '.')::DOUBLE` | Mediana R$ 2.155; média R$ 2.478,58; 33.912 zeros; máximo R$ 3.471.600; 535 acima de R$ 50 mil | Renda de admitidos × desligados, por setor, município e escolaridade. Usar **mediana**; tratar zeros e extremos. | S Q |
| `unidadesaláriocódigo` | Unidade de pagamento da parte fixa | código (aba `unidadesaláriocódigo`) | `5` Mês 3.005.066 (88,5%); `1` Hora 339.833; `7` Variável 22.319 (todos com salário 0); `99` 6.391; `6` Tarefa 4.040; `2` Dia 15.888; `3` Semana 3.848; `4` Quinzena 31 | Filtro de qualidade do salário. A mediana do salário para unidade "Hora" é R$ 2.160, indicando que `salário` já é mensal mesmo nessa unidade **(H)**. | C S |
| `valorsaláriofixo` | Salário base (parte fixa) | decimal com vírgula | Igual a `salário` em 3.039.139 registros (89,5%) | Checagem de consistência; uso secundário. | C |
| `categoria` | Categoria de trabalhador | código | 7 categorias. `101` Geral = 92,8%; `106` Temporário 88.494; `103` Aprendiz 74.892; `111` Intermitente 61.774; `999` 510 | Possível filtro (ex.: separar aprendizes e temporários do emprego típico). | C S |
| `tamestabjan` | Faixa de emprego do estabelecimento em janeiro | código ordinal | 1 a 10 e `99` Ignorado. **Todos os 272.463 registros de 202608 têm `99`** | Porte da empresa (análise opcional). Inutilizável no último mês. | T |

### 1.2 Campos de perfil (uso secundário)

| Campo | Descrição oficial | Valores observados | Uso analítico | Eixo |
|---|---|---|---|---|
| `idade` | Idade do trabalhador | 14 a 100, mediana 30; armazenada como `"40.0"`; 2.202 vazios | Perfil etário; faixas (jovem aprendiz, 50+). | S |
| `sexo` | Sexo do trabalhador | `1` Homem, `3` Mulher | Recorte de gênero (opcional). | S |
| `raçacor` | Raça ou cor | 7 códigos | Recorte de diversidade (opcional). | S |
| `tipodedeficiência` | Tipo de deficiência | 7 códigos | Opcional. | S |
| `horascontratuais` | Horas contratuais semanais | 0 a 60, mediana 44; vírgula decimal; 510 zeros | Normalização salário/hora (opcional); identificar parcial. | S C |
| `indtrabintermitente` | Indicador intermitente | 0, 1, 9 | Filtro/recorte de contrato atípico. | C |
| `indtrabparcial` | Indicador parcial | 0, 1, 9 | Idem. | C |
| `indicadoraprendiz` | Indicador aprendiz | 0, 1 | Idem. | C |
| `tipoempregador` | Tipo de empregador | `0` CNPJ raiz, `2` CPF | Opcional. | C |
| `tipoestabelecimento` | Tipo de estabelecimento | `1` CNPJ, `3` CAEPF, `4` CNO | Opcional (CNO = obras, construção). | C |
| `origemdainformação` | Origem da informação | `1` eSocial (3.396.906), `3` EmpregadoWEB (510) | Controle de qualidade. Os 510 registros "EmpregadoWEB" coincidem em quantidade com `categoria=999`, `horascontratuais=0` e `indtrabintermitente=9` **(H: mesmos registros; verificar)**. | C |

### 1.3 Campos constantes ou sem uso

| Campo | Situação |
|---|---|
| `região` | Constante `4` (Sul). Sem valor analítico. |
| `uf` | Constante `42` (Santa Catarina). Sem valor analítico. |
| `Unnamed: 0.1` | Índice sequencial (único por linha). Artefato de exportação — descartar. |
| `Unnamed: 0` | Índice com repetições (2.434.896 distintos), provavelmente índice dos arquivos mensais originais **(H)**. Descartar. |

### 1.4 Campos do dicionário que **não existem** na base

| Campo | Descrição oficial | Consequência |
|---|---|---|
| `competênciaexc` | Competência da exclusão | Não é possível identificar exclusões nesta base. |
| `indicadordeexclusão` | Indicador de exclusão | Idem. A etapa "filtrar exclusões (EX)" do guia precisa ser esclarecida com a organização. |

---

## 2. Municípios — `data/reference/Municipios_SC_limpo.csv`

296 linhas (295 municípios + 1 linha de rodapé em HTML) · 15 colunas · separador `,` · decimal `.` ·
ausência representada por `-`. Rótulos de colunas trazem o ano entre colchetes.

| Coluna | Tipo → tratamento | Valores observados | Uso analítico |
|---|---|---|---|
| `Município [-]` | texto | 295 nomes únicos | Rótulo no dashboard. |
| `Código [-]` | texto de 7 dígitos (IBGE) | 295 únicos; dígito verificador válido em todos | **Chave**: `substr(código, 1, 6)` = `município` do CAGED. |
| `Gentílico [-]` | texto | — | Sem uso. |
| `Prefeito [2025]` | texto | — | Sem uso (dado pessoal; não exibir). |
| `Área Territorial - km² [2025]` | decimal | sem ausentes | Opcional. |
| `População no último censo - pessoas [2022]` | inteiro | sem ausentes | Denominador alternativo. |
| `Densidade demográfica - hab/km² [2022]` | decimal | sem ausentes | Classificar municípios (urbano/rural). |
| `População estimada - pessoas [2026]` | inteiro | sem ausentes | **Denominador do "saldo por 10 mil habitantes"** (escolha a confirmar; ver diagnóstico E). |
| `Escolarização 6 a 14 anos - % [2022]` | decimal | sem ausentes | Contexto educacional do município. |
| `IDHM [2010]` | decimal | 2 ausentes (`-`), incluindo Balneário Rincão | Contexto de desenvolvimento (dado antigo, 2010). |
| `Mortalidade infantil [2025]` | decimal | **123 ausentes** (`-`) | Pouco útil para a pergunta; muitos ausentes. |
| `Total de receitas brutas realizadas - R$ [2025]` | decimal | sem ausentes | Opcional. |
| `Total de despesas brutas empenhadas - R$ [2025]` | decimal | sem ausentes | Opcional. |
| `PIB per capita - R$ [2023]` | decimal | sem ausentes | Contexto econômico; dispersão com saldo/salário. |
| `Unnamed: 14` | — | vazia (vírgula sobrando no fim das linhas) | Descartar. |

> **Inconsistência nos rótulos**: o rodapé diz que a "população estimada" tem data de referência
> 1º/07/2024 e que a escolarização vem do Censo 2010, enquanto os cabeçalhos indicam [2026] e [2022].
> Registrar como limitação e citar o ano com cautela.

**Ausente nesta base**: não há mesorregião, microrregião, região geográfica imediata/intermediária
nem associação regional. O agrupamento regional pedido no guia exigirá uma tabela externa
(ver diagnóstico, seção D).

---

## 3. Relacionamento entre as bases

| Aspecto | CAGED | Municípios | Validação |
|---|---|---|---|
| Nome da chave | `município` | `Código [-]` | O guia chama de `municipio_codigo`; **esse nome não existe** em nenhuma das bases. |
| Formato | 6 dígitos, texto | 7 dígitos (IBGE com dígito verificador), texto | Converter: `cod6 = Código[:6]`. |
| Cardinalidade | N registros por município | 1 linha por município | **N:1**, sem duplicatas no lado municipal. |
| Cobertura | 295 municípios | 295 municípios (+1 rodapé) | **295/295 casam** — nenhum órfão em nenhum dos lados. |

```sql
-- junção recomendada (DuckDB)
SELECT ...
FROM caged c
LEFT JOIN municipios m ON c.município = substr(m."Código [-]", 1, 6)
```

As tabelas de códigos do dicionário (`seção`, `subclasse`, `cbo2002ocupação`, `graudeinstrução` etc.)
se relacionam com o CAGED pelo código, sempre como texto e com o zero à esquerda restaurado.

---

## 4. Campos necessários por eixo

| Eixo | Campos do CAGED | Campos da base municipal | Referência externa |
|---|---|---|---|
| 1 — Territorial e setorial | `saldomovimentação`, `município`, `seção`, `subclasse` (divisão CNAE), `competênciadec`/`competênciamov`, `tipomovimentação` | código, nome, população estimada, PIB per capita | Agrupamento regional (IBGE) e malha para mapas — opcionais |
| 2 — Perfil socioeconômico | `salário`, `unidadesaláriocódigo`, `graudeinstrução`, `saldomovimentação`, `tipomovimentação`, `idade`, `sexo`, `categoria` | IDHM, escolarização | — |
| 3 — Qualificação e IA | `cbo2002ocupação`, `graudeinstrução`, `salário`, `saldomovimentação`, `seção`/`subclasse` | — | Descrições da CBO (aba `cbo2002ocupação`), estrutura hierárquica da CBO (MTE) |
