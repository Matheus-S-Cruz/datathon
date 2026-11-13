"""Orquestração do assistente (§4.1 do prompt).

Fluxo: sanitiza a pergunta → checa injeção → classifica a intenção (provedor) → executa a ferramenta
controlada → monta a Resposta com evidência. A interface NUNCA consulta dados direto; o provedor NUNCA
executa código. Todo número vem de uma ferramenta que reutiliza o serviço oficial.
"""

from __future__ import annotations

from dashboard import formatting as fmt
from dashboard.services import analytics as A
from dashboard.services.assistant import context as ctx
from dashboard.services.assistant import validation as val
from dashboard.services.assistant.provider import Provider, SimulatedProvider
from dashboard.services.assistant.response import Evidencia, Kind, Resposta
from dashboard.services.assistant.tools import glossary as gloss
from dashboard.services.assistant.tools import indicators as ind
from dashboard.services.assistant.tools import metadata as meta
from src import glossario as G

RECUSA_INJECAO = (
    "Só posso responder sobre os dados, indicadores e a metodologia do Pulso Industry (mercado de "
    "trabalho industrial de Santa Catarina). Não executo comandos, não acesso arquivos e não compartilho configurações internas.")

SUGESTOES_INICIAIS = (
    "Quais são os principais indicadores do painel?",
    "O que significa saldo de movimentações?",
    "Como interpretar a taxa de rotatividade?",
    "Quais municípios têm maior saldo de empregos?",
    "Qual é a diferença entre as medidas de população utilizadas?",
    "O que significa a classificação das ocupações?",
    "Quais são as limitações dos dados do Novo CAGED?",
)


class Orchestrator:
    """Coordena uma pergunta. Recebe um provedor (injetável para testes)."""

    def __init__(self, provider: Provider | None = None):
        self.provider = provider or SimulatedProvider()

    def responde(self, pergunta: str, pagina_id: str = "", state=None) -> Resposta:
        # 1) sanitização + limite de tamanho
        try:
            texto = val.sanitiza_pergunta(pergunta)
        except val.EntradaInvalida as e:
            return Resposta(Kind.ERRO, str(e), sugestoes=SUGESTOES_INICIAIS)

        # 2) proteção contra injeção/abuso (aplicada no código, não no prompt)
        if val.parece_injecao(texto):
            return Resposta(Kind.CONCEITO, RECUSA_INJECAO, sugestoes=SUGESTOES_INICIAIS)

        # 3) contexto da página/recorte
        contexto = ctx.resolve(pagina_id, state)

        # 4) intenção (provedor) + 5) ferramenta controlada
        intent = self.provider.classifica_intencao(texto, contexto)
        try:
            return self._executa(intent, texto, contexto)
        except A.MissingOutputs:
            return Resposta(Kind.ERRO, "Os dados do dashboard não estão disponíveis no momento. "
                            "Tente novamente após o carregamento das tabelas.")
        except Exception:
            # falha controlada: nunca vaza stack/caminho interno
            return Resposta(Kind.ERRO, "Não consegui completar a consulta agora. Tente reformular a pergunta.")

    # ------------------------------------------------------------------ intenções

    def _executa(self, intent, texto: str, contexto: ctx.Contexto) -> Resposta:
        nome = intent.nome
        if nome == "ajuda":
            return self._ajuda()
        if nome == "causalidade":
            return self._causalidade()
        if nome == "distincao_populacao":
            return Resposta(Kind.CONCEITO, meta.DISTINCAO_POPULACAO, sugestoes=SUGESTOES_INICIAIS[:3])
        if nome == "distincao_cbo":
            return Resposta(Kind.CONCEITO, meta.DISTINCAO_CBO, sugestoes=SUGESTOES_INICIAIS[:3])
        if nome == "limitacoes_caged":
            return self._limitacoes()
        if nome == "explicar_indicador":
            return self._explicar(intent.parametros.get("termo", texto))
        if nome == "kpis_painel":
            return self._kpis(contexto)
        if nome == "salario_estado":
            return self._salario_estado(contexto)
        if nome == "salario_escolaridade":
            return self._salario_escolaridade()
        if nome == "top_municipios":
            return self._top_municipios(contexto, intent.parametros)
        if nome == "saldo_setores":
            return self._saldo_setores(contexto)
        return self._nao_sei()

    def _ajuda(self) -> Resposta:
        texto = ("Sou o Assistente Pulso, da Pulso Industry. Respondo com base nos dados e "
                 "na metodologia do próprio dashboard. Posso **explicar indicadores** (saldo, rotatividade, "
                 "salário, escolaridade), mostrar **KPIs do recorte atual**, **rankings de municípios**, o "
                 "**saldo por setor** e esclarecer **limitações e diferenças metodológicas**. Não estimo "
                 "valores que o dashboard não calculou.")
        return Resposta(Kind.CONCEITO, texto, sugestoes=SUGESTOES_INICIAIS)

    def _causalidade(self) -> Resposta:
        texto = ("Os dados mostram **associações descritivas**, não relações de causa. Por exemplo, grupos "
                 "com mais escolaridade podem ter salário mediano maior, mas isso **não comprova** que a "
                 "escolaridade causou a diferença — há outros fatores (ocupação, setor, porte da empresa, "
                 "região). Posso explicar o indicador e suas limitações, sem afirmar causalidade.")
        return Resposta(Kind.CONCEITO, texto)

    def _limitacoes(self) -> Resposta:
        texto = ("Principais limitações do Novo CAGED neste projeto:\n\n"
                 f"- {G.nota('limite_fluxo')}\n"
                 "- O salário usa a **mediana sem zeros** como medida principal; a média é complemento e é "
                 "puxada por valores extremos.\n"
                 "- Taxas por 10 mil habitantes dependem da medida de população (Censo 2022 × estimativa 2026).\n"
                 "- As macrofamílias de ocupações são um agrupamento analítico do projeto, não a nomenclatura "
                 "oficial da CBO.")
        return Resposta(Kind.CONCEITO, texto)

    def _explicar(self, termo: str) -> Resposta:
        id_ = gloss.resolve_id(termo)
        if not id_:
            return Resposta(Kind.SEM_DADOS,
                            "Não encontrei esse indicador no glossário documentado. Posso explicar, por "
                            "exemplo: saldo, rotatividade, crescimento do emprego, escolaridade média, "
                            "salário mediano ou macrofamílias de ocupações.",
                            sugestoes=SUGESTOES_INICIAIS[1:4])
        d = gloss.explicar(id_)
        texto = (f"**{d['nome']}**\n\n{d['definicao']}\n\n"
                 f"- **Fórmula:** {d['formula']}\n- **Unidade:** {d['unidade']}\n"
                 f"- **Fonte:** {d['fonte']}\n- **Período:** {d['periodo']}\n"
                 f"- **Abrangência:** {d['abrangencia']}\n- **Limitações:** {d['limitacoes']}")
        return Resposta(Kind.CONCEITO, texto)

    def _kpis(self, contexto: ctx.Contexto) -> Resposta:
        r = ind.kpis_do_recorte(contexto.scope)
        k = r["valores"]
        linhas = [f"- **Saldo de vagas:** {fmt.signed(k['saldo'])} "
                  f"({fmt.integer(k['admissoes'])} admissões − {fmt.integer(k['desligamentos'])} desligamentos)",
                  f"- **Saldo por 10 mil hab.:** {fmt.num(k['saldo_por_10k'], 1)}",
                  f"- **Salário mediano (SC):** {fmt.brl(A.salario_estado()['salario_mediano_s0'], 0)}"]
        texto = "Principais indicadores" + (f" no recorte atual ({', '.join(r['scope_desc'])})"
                                            if r["scope_desc"] else " (Santa Catarina inteira)") + ":\n\n" + "\n".join(linhas)
        ev = Evidencia(ferramenta="analytics.kpis", fonte=G.FONTE_CAGED, periodo=G.PERIODO,
                       unidade="vagas / R$ por mês", abrangencia="Municípios de SC no recorte",
                       recorte=tuple(r["scope_desc"]))
        return Resposta(Kind.DADO, texto, evidencia=ev, sugestoes=(
            "Quais municípios têm maior saldo de empregos?", "Qual o saldo por setor?"))

    def _salario_estado(self, contexto: ctx.Contexto) -> Resposta:
        s = ind.salario_estado()
        v = s["valores"]
        texto = (f"O **salário mediano** em Santa Catarina é {fmt.brl(v['salario_mediano_s0'], 0)} por mês "
                 f"(medida principal, exclui zeros). A **média** é {fmt.brl(v['salario_medio'], 0)} — maior "
                 "porque é puxada por valores extremos. A mediana é descritiva do fluxo de contratações, "
                 "não do estoque de empregos.")
        e = s["evidencia"]
        ev = Evidencia(ferramenta="analytics.salario_estado", indicador="salario_mediano",
                       fonte=e["fonte"], periodo=e["periodo"], unidade=e["unidade"],
                       abrangencia="Santa Catarina inteira", limitacoes=e["limitacoes"])
        return Resposta(Kind.DADO, texto, evidencia=ev, sugestoes=(
            "Qual o salário mediano por escolaridade?",))

    def _salario_escolaridade(self) -> Resposta:
        r = ind.salario_por_escolaridade()
        tab = r["tabela"].rename(columns={"grau": "Grau de instrução",
                                          "salario_mediano_s0": "Mediano (R$)", "salario_medio": "Médio (R$)"})
        texto = ("Salário **mediano** (sem zeros) por grau de instrução, em R$ por mês. A relação é "
                 "**descritiva**: mais escolaridade costuma vir com salário maior, mas isso não indica causa.")
        e = r["evidencia"]
        ev = Evidencia(ferramenta="analytics.table(salario_por_grau)", indicador="salario_mediano",
                       fonte=e["fonte"], periodo=e["periodo"], unidade=e["unidade"],
                       abrangencia="Santa Catarina inteira", limitacoes=e["limitacoes"])
        return Resposta(Kind.DADO, texto, evidencia=ev, tabela=tab)

    def _top_municipios(self, contexto: ctx.Contexto, params: dict) -> Resposta:
        indicador = params.get("indicador", "saldo")
        maiores = params.get("maiores", True)
        r = ind.top_municipios(contexto.scope, indicador=indicador, n=5, maiores=maiores)
        if not r.get("ok"):
            return self._nao_sei()
        nome_ind = gloss.explicar(gloss.resolve_id(indicador) or "saldo").get("nome", indicador)
        tab = r["tabela"].rename(columns={"municipio": "Município", indicador: nome_ind})
        ordem = "maiores" if maiores else "menores"
        texto = (f"Municípios com os **{ordem}** valores de **{nome_ind.lower()}**"
                 + (f" no recorte atual ({', '.join(r['scope_desc'])})" if r["scope_desc"]
                    else " (Santa Catarina inteira)") + ":")
        ev = Evidencia(ferramenta="analytics.municipal", indicador=indicador, fonte=G.FONTE_CAGED,
                       periodo=G.PERIODO, abrangencia="Municípios de SC no recorte",
                       recorte=tuple(r["scope_desc"]))
        return Resposta(Kind.DADO, texto, evidencia=ev, tabela=tab)

    def _saldo_setores(self, contexto: ctx.Contexto) -> Resposta:
        r = ind.saldo_por_setor(contexto.scope, n=8)
        tab = r["tabela"].rename(columns={"setor": "Setor", "saldo": "Saldo"})
        texto = ("Saldo de vagas (admissões − desligamentos) por seção CNAE"
                 + (f" no recorte atual ({', '.join(r['scope_desc'])})" if r["scope_desc"]
                    else " (Santa Catarina inteira)") + ":")
        ev = Evidencia(ferramenta="analytics.sectors_in_scope", indicador="saldo", fonte=G.FONTE_CAGED,
                       periodo=G.PERIODO, unidade="vagas", abrangencia="Seções CNAE no recorte",
                       recorte=tuple(r["scope_desc"]))
        return Resposta(Kind.DADO, texto, evidencia=ev, tabela=tab)

    def _nao_sei(self) -> Resposta:
        texto = ("Não encontrei dados suficientes para responder com segurança a essa pergunta. Posso "
                 "explicar a metodologia disponível ou mostrar indicadores calculados pelo dashboard, mas "
                 "não vou estimar um valor que não foi calculado.")
        return Resposta(Kind.SEM_DADOS, texto, sugestoes=SUGESTOES_INICIAIS[:4])
