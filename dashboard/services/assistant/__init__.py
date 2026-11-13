"""Assistente inteligente do Pulso Industry (Assistente Pulso) — camada conversacional sobre os dados reais.

PRÉVIA (Etapa 4, modo simulação): toda a arquitetura é funcional — ferramentas controladas que
reutilizam os serviços oficiais (`queries.py`, `analytics.py`) e o glossário único —, mas o "cérebro"
de linguagem natural é um provedor **determinístico local** (`SimulatedProvider`), sem custo e sem
chamada a nenhuma API. A interface `Provider` fica pronta para plugar um LLM real depois, sem reescrever
ferramentas, contexto, contratos ou interface.

Princípio central: o assistente NUNCA inventa número, fonte, consulta ou conclusão. Todo valor vem de
uma ferramenta controlada que reutiliza o cálculo oficial do projeto; quando não há dado ou a pergunta
não é reconhecida, o assistente admite que não sabe.

Camadas (ver docs/assistente.md):
  tools/      ferramentas controladas (glossário, indicadores, metadados) — parâmetros tipados
  context     recorte/página atuais, a partir do estado da aplicação
  provider    abstração do "cérebro"; SimulatedProvider (prévia) / LLM (futuro)
  orchestrator coordena intenção -> ferramenta -> resposta
  response    estrutura da resposta (texto + evidência: fonte, período, unidade, recorte)
  validation  valida parâmetros e protege contra entradas maliciosas
"""
