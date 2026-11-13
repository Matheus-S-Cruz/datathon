# Assistente Inteligente — Etapa 4 (prévia / simulação)

> **Identidade:** o assistente se chama **Assistente Pulso**, da **Pulso Industry**. O avatar circular
> (`dashboard/assets/assistant_avatar.svg`) é a marca simplificada — coração (propósito), pulso
> (monitoramento) e barras de dados (indústria e interpretação) — em disco roxo-escuro, legível nos temas
> claro e escuro. Ele aparece no botão flutuante, no cabeçalho da janela, ao lado de cada resposta e no
> indicador de processamento.

> **Versão prévia, sem custo.** Toda a arquitetura é funcional — ferramentas controladas que reutilizam
> os serviços oficiais e o glossário —, mas o "cérebro" de linguagem natural é um **provedor
> determinístico local** (`SimulatedProvider`), sem chamada a nenhuma API de IA. A arquitetura está
> pronta para plugar um LLM real depois, sem reescrever interface, ferramentas, contexto ou contratos.
>
> **Princípio central:** o assistente nunca inventa número, fonte, consulta ou conclusão. Todo valor vem
> de uma ferramenta que reutiliza o cálculo oficial do projeto; quando não há dado ou a pergunta não é
> reconhecida, ele admite que não sabe.

---

## 1. Arquitetura

```
 usuário ─► dashboard/components/assistant.py        (interface: botão flutuante + chat)
                     │ (pergunta, pagina_id, session_state)
                     ▼
            services/assistant/orchestrator.py        (sanitiza ─► injeção ─► intenção ─► ferramenta ─► resposta)
             │                 │                 │
             ▼                 ▼                 ▼
        validation.py      provider.py        context.py
      (limites, injeção)  (SimulatedProvider; (página atual + Scope do recorte)
                           LLM no futuro)
                     │
                     ▼
            services/assistant/tools/                 (ferramentas controladas, parâmetros validados)
              glossary.py    → src/glossario.py        (definições, fórmulas, fontes, limitações)
              indicators.py  → dashboard/services/analytics.py  (kpis, municipal, salario_estado, setores)
              metadata.py    → municípios/regiões válidos; distinções Censo×estimativa, CBO oficial×analítica
                     │
                     ▼
            services/assistant/response.py             (Resposta + Evidência: fonte/período/unidade/recorte)
```

### Separação de responsabilidades
- **Interface** (`components/assistant.py`): botão flutuante (`st.popover`), janela de conversa
  (`st.chat_message`/`st.chat_input`), histórico de sessão, sugestões, botão limpar, estado de
  carregamento. **Não consulta dados** — delega ao orquestrador.
- **Orquestração** (`orchestrator.py`): sanitiza a pergunta, checa injeção, resolve o contexto,
  classifica a intenção (provedor) e executa a ferramenta, montando a `Resposta`.
- **Contexto** (`context.py`): identifica a página (estrutura controlada, não o título visual) e o
  recorte global (`Scope`) a partir do `session_state`. Páginas com filtros próprios **não** assumem o
  recorte global.
- **Ferramentas** (`tools/`): reutilizam os serviços oficiais; parâmetros validados; nunca SQL/código livre.
- **Provedor** (`provider.py`): abstrai o "cérebro". Prévia = `SimulatedProvider` (intenção por
  palavras-chave). Futuro = `LLMProvider` com a mesma interface.
- **Validação** (`validation.py`): limite de tamanho, proteção contra injeção, listas brancas.

## 2. Fluxo de uma mensagem
1. A pessoa escreve a pergunta na janela do assistente.
2. `validation.sanitiza_pergunta` normaliza e limita o tamanho (máx. 500 caracteres).
3. `validation.parece_injecao` detecta tentativas de manipulação → resposta de recusa padrão.
4. `context.resolve` monta página + `Scope` atuais.
5. O provedor classifica a **intenção** (ex.: `kpis_painel`, `explicar_indicador`, `top_municipios`).
6. O orquestrador executa a **ferramenta** correspondente (reusando `queries.py`/`analytics.py`).
7. A `Resposta` volta com texto + **evidência** (fonte, período, unidade, recorte, limitações).

## 3. Ferramentas disponíveis
| Ferramenta | Reusa | O que responde |
|---|---|---|
| `glossary.explicar` | `src/glossario.py` | definição, fórmula, unidade, fonte, período, limitações de um indicador |
| `indicators.kpis_do_recorte` | `analytics.kpis(scope)` | saldo, admissões, desligamentos, saldo/10k do recorte |
| `indicators.salario_estado` | `analytics.salario_estado` | salário mediano (principal) e médio (complemento) de SC |
| `indicators.top_municipios` | `analytics.municipal(scope)` | ranking de municípios por indicador, no recorte |
| `indicators.salario_por_escolaridade` | `analytics.table` | salário mediano/médio por grau de instrução |
| `indicators.saldo_por_setor` | `analytics.sectors_in_scope` | saldo por seção CNAE no recorte |
| `metadata` | `analytics` + textos | validação de municípios/regiões; distinções metodológicas |

## 4. Contexto e filtros
- **Página atual**: derivada do `url_path` no `app.py` e mapeada em `context.PAGINAS`.
- **Recorte global** (`Scope`: `secoes`, `min_pop`, `regiao`): lido do `session_state` (`an_ind`,
  `an_secoes`, `an_regiao`, `an_pop`) apenas em páginas que o desenham. Valores inválidos são ignorados.
- **Filtros próprios**: páginas como Explorador, Macrofamílias, Estatística, Relações e Contexto IBGE
  têm controles independentes; o assistente **não** aplica o recorte global nelas.
- Respostas quantitativas declaram o recorte aplicado (ou "Santa Catarina inteira").

## 5. Conhecimento metodológico
- Fonte única: `src/glossario.py` (17 indicadores, 9 notas). O assistente não duplica definições.
- Distinções que ele diferencia explicitamente: **média × mediana** salarial; **população Censo 2022 ×
  estimativa 2026**; **CBO oficial × 9 macrofamílias analíticas**. Nunca apresenta classificação
  experimental como oficial.
- Salário: segue a metodologia da etapa 3.2 (mediana sem zeros como principal). Não afirma causalidade
  entre escolaridade e renda; não converte valores por conta própria.

## 6. Segurança
- Permissões no **código**, não no prompt: a interface não consulta dados; o provedor não executa código.
- Sem SQL/Python/caminho de arquivo livres; ferramentas com parâmetros validados por lista branca.
- Perguntas são tratadas como **dados**, nunca como instruções; injeção é detectada e recusada.
- Limite de tamanho da pergunta (500 caracteres). Erros são controlados — nunca vazam stack/caminho.
- Nenhuma credencial no código. `.gitignore` já ignora `.env`/`*.key`/`secrets.toml`. Ver `.env.example`.

## 7. Memória e histórico
- Histórico vive só no `st.session_state` da sessão (chave `assist_historico`), máximo de 40 mensagens.
- Botão "Limpar" apaga a conversa. Não há memória permanente nem compartilhada entre usuários/sessões.

## 8. Provedor de IA (futuro) e custos
- A prévia **não tem custo**: provedor determinístico local.
- Para um LLM real: implementar um `LLMProvider` com a mesma interface `classifica_intencao`
  (idealmente function-calling restrito às mesmas ferramentas). A chave viria de variável de ambiente
  (`.env`, nunca versionada). A estimativa de custo e a escolha do provedor permanecem **pendentes de
  decisão/autorização** (ver `docs/auditoria_prontidao_etapa4.md`).

## 9. Variáveis de ambiente
Ver `.env.example`. Na prévia, **nenhuma variável é necessária** — o assistente funciona sem chave.
Quando um LLM for plugado, a chave será lida de variável de ambiente e nunca registrada em log ou commit.

## 10. Limitações conhecidas da prévia
- O provedor é por **palavras-chave**, não compreende linguagem aberta: perguntas fora das intenções
  reconhecidas recebem "não sei responder isso ainda" (comportamento desejado, não um bug).
- Referências conversacionais complexas (ex.: "e entre esses?") ainda não resolvem anáfora — a prévia
  prioriza respostas atômicas e corretas em vez de diálogo encadeado.
- A classificação CBO experimental (3.5c) não existe; o assistente usa só a oficial e as macrofamílias.

## 11. Testes
`tests/test_assistant.py` cobre: contexto (recorte global × filtros próprios), ferramentas (indicador/
município válido e inválido, recorte), metodologia (saldo, populações, CBO, causalidade, salário),
segurança (injeção, tamanho, vazamento) e confiabilidade (evidência obrigatória, números batem com o
serviço oficial, admite incerteza). As páginas com o assistente são renderizadas por `test_app_pages.py`.

## 12. Exemplos de perguntas que o assistente responde
- "Quais são os principais indicadores do painel?" → KPIs reais do recorte.
- "O que significa saldo de movimentações?" → definição do glossário.
- "Como interpretar a taxa de rotatividade?" → conceito DIEESE do glossário.
- "Quais municípios têm maior saldo de empregos?" → ranking real (respeita o recorte).
- "Qual o salário mediano por escolaridade?" → tabela real (mediana e média).
- "Qual a diferença entre as medidas de população?" → Censo 2022 × estimativa 2026.
- "O que significa a classificação das ocupações?" → CBO oficial × macrofamílias.
- "A escolaridade causou o aumento da renda?" → explica associação ≠ causa.
