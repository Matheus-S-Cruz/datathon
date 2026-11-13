# Classificação de ocupações (CBO) — hierarquia oficial e apoio por IA

> Etapas 3.5a (hierarquia oficial) e 3.5b (preparação do piloto de IA). **Nenhuma chamada paga de
> IA foi feita.** A classificação oficial é e continua sendo a referência principal; a IA é uma
> ferramenta experimental de apoio, nunca substitui os códigos oficiais (§7 do plano).

---

## 1. Duas estruturas que coexistem

O projeto usa **duas** classificações de ocupações, com finalidades diferentes e claramente separadas.
Nenhuma substitui a outra.

### 1.1. Hierarquia oficial da CBO-2002 (referência principal)

Classificação Brasileira de Ocupações 2002, do Ministério do Trabalho e Emprego. Cinco níveis, lidos
pelos primeiros dígitos do código de 6 dígitos:

| Dígitos | Nível | Quantidade na base | Exemplo |
|---:|---|---:|---|
| 1 | Grande Grupo | **10** | `7` · Trabalhadores da produção de bens e serviços industriais |
| 2 | Subgrupo Principal | **48** | `72` |
| 3 | Subgrupo | **194** | `723` |
| 4 | Família | **627** | `7234` |
| 6 | Ocupação | **2.778** | `723410` |

Gerada por `src/cbo/hierarquia.py` → `data/reference/cbo_hierarquia.parquet`. Os títulos das ocupações
vêm do dicionário oficial dos microdados (`Dicionario_de_dados.xlsx`, aba `cbo2002ocupação`); os nomes
dos Grandes Grupos são os dez títulos oficiais da CBO-2002.

**Os dez Grandes Grupos oficiais:**

| Código | Grande Grupo |
|---:|---|
| 0 | Membros das Forças Armadas, Policiais e Bombeiros Militares |
| 1 | Membros superiores do poder público, dirigentes de organizações de interesse público e de empresas e gerentes |
| 2 | Profissionais das ciências e das artes |
| 3 | Técnicos de nível médio |
| 4 | Trabalhadores de serviços administrativos |
| 5 | Trabalhadores dos serviços, vendedores do comércio em lojas e mercados |
| 6 | Trabalhadores agropecuários, florestais, da caça e pesca |
| 7 | Trabalhadores da produção de bens e serviços industriais |
| 8 | Trabalhadores da produção de bens e serviços industriais |
| 9 | Trabalhadores de manutenção e reparação |

> Fonte: MTE — CBO-2002 (https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/cbo). A estrutura é
> estável desde 2002. O download direto dos CSV oficiais (Família, Subgrupo etc.) foi bloqueado no
> ambiente de execução (HTTP 403); por isso os nomes de família/subgrupo não são preenchidos ainda —
> os CSV do MTE podem ser anexados em `data/reference/` depois, sem mudar a estrutura.

### 1.2. Macrofamílias analíticas do projeto (9) — não substituídas

O pipeline agrupa as ocupações em **9 macrofamílias** pelo 1º dígito do CBO, **fundindo os Grandes
Grupos 7 e 8** numa única macrofamília operacional ("Produção de bens e serviços industriais
(Operacional)"). Servem à narrativa do projeto (gargalo operacional × técnico) e estão em
`outputs/macrofamilias_cbo.parquet` e `outputs/macrofamilias_industria.parquet`.

**Diferença-chave para o assistente (Etapa 4) entender:** a macrofamília operacional do projeto = Grande
Grupo 7 **＋** Grande Grupo 8 da CBO oficial. São nomes próprios do projeto, não a nomenclatura oficial.
As duas visões são compatíveis (a analítica é um reagrupamento determinístico da oficial), mas **não
devem ser apresentadas como se fossem a mesma coisa**.

| Projeto (9 macrofamílias analíticas) | CBO oficial (Grande Grupo) |
|---|---|
| Dirigentes e Gerentes | 1 |
| Profissionais de nível superior (Técnico/Engenharia) | 2 |
| Técnicos de nível médio | 3 |
| Trabalhadores de apoio administrativo | 4 |
| Serviços, vendas e comércio | 5 |
| Agropecuários e florestais | 6 |
| **Produção de bens e serviços industriais (Operacional)** | **7 + 8 (fundidos)** |
| Manutenção e reparação | 9 |
| Forças Armadas / Segurança | 0 |

---

## 2. Piloto de IA (3.5b) — preparação, sem gasto

Objetivo: avaliar se um LLM ajuda a **classificar/nomear** ocupações de forma útil para a indústria,
**sem substituir** a classificação oficial. Esta seção define o processo; **nenhuma chamada paga foi
executada** (§7.5).

### 2.1. Fluxo atual de classificação (revisado)

No pipeline (`notebooks/01_pipeline_caged_sc.ipynb`, seção 8) existem duas camadas:
1. **Baseline determinístico** (sempre roda, sem rede): macrofamília = 1º dígito do CBO (grupos 7/8
   fundidos). É o que alimenta os `outputs/macrofamilias_*.parquet`.
2. **Refino opcional por LLM** (`refinar_macrofamilias_llm`): só roda se `OPENAI_API_KEY` estiver
   definida; na ausência, é pulado e o baseline prevalece. Hoje imprime a resposta do modelo, mas
   **não grava nada** nem altera os outputs.

Decisão (§7.2): **não manter dois processos de IA independentes.** O piloto abaixo substitui o
`refinar_macrofamilias_llm` por uma arquitetura desacoplada do provedor (§2.3), com entradas/saídas em
arquivo e revisão humana. O baseline determinístico continua sendo o padrão quando não há IA.

### 2.2. Escopo da amostra do piloto

- **Universo:** ocupações com movimentação na seção industrial C (Transformação), que concentram o
  interesse do projeto.
- **Amostra representativa:** as ocupações mais frequentes que cobrem ~95% do volume da seção C
  (as 200 mais frequentes já cobrem ~90%), **mais** uma amostra aleatória da cauda — para o piloto
  não ver só os casos fáceis.
- **Tamanho do piloto:** ~100–150 ocupações (lotes de ~50), suficiente para avaliar qualidade antes de
  qualquer rodada completa.

### 2.3. Arquitetura desacoplada do provedor

```
entrada (CSV/parquet)  ──►  classificador (interface Provider)  ──►  saída (CSV, 1 linha por ocupação)
  cbo, ocupacao,                   │                                    cbo, ocupacao_original,
  grande_grupo_oficial,            ├── BaselineProvider  (sem rede, sem custo; já existe)
  volume                           ├── OpenAIProvider    (futuro; só com chave e autorização)
                                   └── OutroProvider     (substituível sem reescrever o resto)
```

- A camada de aplicação **nunca** chama o provedor direto: usa a interface `Provider.classificar(lote)`.
- Trocar de provedor (OpenAI → outro) não muda o resto do código.
- Entradas e saídas ficam em arquivo, versionadas (`reports/ia/`), com `modelo`, `data`, `versao_prompt`.

### 2.4. Entrada e saída exigidas

**Entrada** (uma linha por ocupação): `cbo`, `ocupacao` (título oficial), `grande_grupo_oficial`
(e seu nome), `volume` (movimentações na seção C).

**Saída** (uma linha por ocupação):

| Campo | Significado |
|---|---|
| `cbo` | código oficial (chave) |
| `ocupacao_original` | título oficial do dicionário |
| `codigo_original` | o próprio CBO (preservado) |
| `grupo_oficial_sugerido` | Grande Grupo/macrofamília sugerido pela IA |
| `justificativa` | por que a IA sugeriu esse grupo |
| `confianca` | alta / média / baixa |
| `decisao_humana` | aprovado / ajustado / rejeitado (preenchido na revisão) |
| `resultado_final` | o grupo após a decisão humana |
| `revisado_por` | responsável |

A IA **só pode escolher categorias da taxonomia fechada** (os Grandes Grupos oficiais ou as 9
macrofamílias do projeto); **proibido criar categoria nova**.

### 2.5. Critérios de qualidade

- **Concordância com o baseline determinístico:** a sugestão da IA é comparada com o Grande Grupo do
  próprio código. Divergências são o ponto de interesse — e **todas** vão para revisão humana.
- **Confiança baixa/média:** 100% revisadas por humano.
- **Confiança alta:** amostra aleatória de 10% revisada.
- O piloto é **aprovado** se a concordância com o oficial for alta e as divergências forem explicáveis
  (ocupações genuinamente ambíguas), não erros grosseiros.

### 2.6. Fluxo de revisão humana (§7.4)

1. A saída do piloto é gravada em `reports/ia/piloto_saida.csv` (um arquivo editável).
2. Um revisor preenche `decisao_humana` e `resultado_final` por linha (aprovar / ajustar / rejeitar).
3. Divergências entre IA e oficial são registradas com motivo.
4. **Nenhuma** classificação experimental sobrescreve o código oficial automaticamente: o
   `resultado_final` só vale para análises marcadas como experimentais.
5. Priorização: primeiro as ocupações de maior volume e as de maior divergência.

### 2.7. Controle de custos (§7.5) — pendente de autorização

**Nada será chamado em API sem autorização explícita.** A proposta de modelo, estimativa de tokens,
estimativa de custo, tamanho de amostra, limites de orçamento e plano de interrupção serão apresentados
**antes** da etapa 3.5c, em documento próprio, para aprovação. O orçamento de US$ 2–4,50 discutido antes
é só estimativa, **não é autorização**.

### 2.8. Integração ao dashboard (§7.6) — não automática

Se e quando a classificação experimental for exibida no app, será **identificada como experimental**,
diferenciada da oficial, com metodologia e limitações, permitindo comparação — nunca confundida com a
classificação oficial.

---

## 3. O que foi entregue nestas etapas

- **3.5a:** `src/cbo/hierarquia.py` + `data/reference/cbo_hierarquia.parquet` (hierarquia oficial dos 5
  níveis) + este documento. As 9 macrofamílias analíticas foram **preservadas** e mapeadas contra a
  estrutura oficial.
- **3.5b:** este documento define a arquitetura desacoplada, entradas/saídas, critérios de qualidade e
  o fluxo de revisão humana. **Nenhuma chamada paga executada.**
- **Pendente de sua autorização:** 3.5c (rodada com API), que só ocorre após aprovação de modelo,
  custo e amostra.
