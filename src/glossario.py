"""Glossário único dos indicadores do Raio-X Industrial SC.

Fonte única das DEFINIÇÕES e dos TEXTOS sobre os indicadores. Não contém cálculos nem consultas:
as fórmulas aqui descrevem o que o pipeline (`notebooks/_build_notebook.py`) e os serviços
(`dashboard/services/analytics.py`, `queries.py`) já fazem.

- `INDICADORES`: um registro por indicador, com os campos de documentação.
- `textos` de cada indicador: frases exibidas na interface, copiadas literalmente do texto que
  já estava nas páginas (não reescrever aqui sem decidir mudar o que aparece na tela).
- `NOTAS`: notas de método que combinam mais de um indicador, exibidas em "Ver dados e método".

Gerar a versão legível (`docs/glossario.md`):

    python -m src.glossario
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

NA = "não se aplica"

# Período de referência dos dados do Novo CAGED (texto exibido no painel).
PERIODO = "set/2025 a ago/2026 (competência de declaração do Novo CAGED)"

FONTE_CAGED = "Novo CAGED/MTE — microdados de movimentações de SC fornecidos pela organização do Datathon"
FONTE_POP_CENSO = ("Base municipal da organização (`Municipios_SC_limpo.csv`), coluna "
                   "\"População no último censo - pessoas [2022]\" (IBGE, Censo 2022)")
FONTE_POP_ESTIMADA = ("Base municipal da organização (`Municipios_SC_limpo.csv`), coluna "
                      "\"População estimada - pessoas [2026]\" (IBGE)")
FONTE_CEMPRE = "IBGE — Cadastro Central de Empresas (CEMPRE) 2024, SIDRA tabela 9509, pessoal ocupado assalariado"
FONTE_PIB = "IBGE — PIB dos Municípios, SIDRA tabela 5938 (valor adicionado bruto por atividade, 2021)"
FONTE_DICIONARIO = "Dicionário de dados oficial do Novo CAGED (`Dicionario_de_dados.xlsx`)"
ABRANGENCIA_RECORTE = ("Movimentações em municípios de SC; segue o recorte de setores, região e população "
                       "mínima quando aplicado")
LIMITE_FLUXO = ("Mede fluxo (admissões e desligamentos), não o estoque de empregos nem vagas abertas; "
                "cada linha é uma movimentação, não uma pessoa")


@dataclass(frozen=True)
class Indicador:
    id: str
    nome: str
    grupo: str
    definicao: str
    formula: str
    unidade: str
    fonte: str
    periodo: str
    abrangencia: str
    filtragem: str
    limitacoes: str
    colunas: tuple[str, ...] = ()            # nomes da coluna nos dados (outputs/ ou consultas)
    onde: str = ""                           # páginas/serviços que usam esta variante
    textos: dict[str, str] = field(default_factory=dict)   # textos exibidos, literais

    CAMPOS = ("nome", "definicao", "formula", "unidade", "fonte", "periodo", "abrangencia", "filtragem",
              "limitacoes")


@dataclass(frozen=True)
class Nota:
    texto: str
    indicadores: tuple[str, ...]


INDICADORES: tuple[Indicador, ...] = (
    # ------------------------------------------------------------------ fluxo
    Indicador(
        id="saldo", nome="Saldo de vagas formais", grupo="Fluxo do Novo CAGED",
        definicao="Diferença entre admissões e desligamentos com carteira assinada no período.",
        formula="admissões − desligamentos (soma de `saldomovimentação`, que vale +1 ou −1 por registro)",
        unidade="vagas (postos de trabalho formais)", fonte=FONTE_CAGED, periodo=PERIODO,
        abrangencia=ABRANGENCIA_RECORTE,
        filtragem="Todos os registros da base (3.397.416); nenhuma exclusão",
        limitacoes=LIMITE_FLUXO,
        colunas=("saldo",), onde="todas as páginas",
        textos={"kpi_ajuda": "Admissões − desligamentos no Novo CAGED, set/2025 a ago/2026.",
                "tabelas_ajuda": "Admissões − desligamentos."}),
    Indicador(
        id="admissoes", nome="Admissões", grupo="Fluxo do Novo CAGED",
        definicao="Movimentações de entrada de trabalhadores com carteira assinada.",
        formula="nº de registros com `saldomovimentação` = +1",
        unidade="movimentações", fonte=FONTE_CAGED, periodo=PERIODO, abrangencia=ABRANGENCIA_RECORTE,
        filtragem="Todos os registros de admissão; nenhuma exclusão", limitacoes=LIMITE_FLUXO,
        colunas=("admissoes",), onde="todas as páginas"),
    Indicador(
        id="desligamentos", nome="Desligamentos", grupo="Fluxo do Novo CAGED",
        definicao="Movimentações de saída de trabalhadores com carteira assinada, por qualquer motivo.",
        formula="nº de registros com `saldomovimentação` = −1",
        unidade="movimentações", fonte=FONTE_CAGED, periodo=PERIODO, abrangencia=ABRANGENCIA_RECORTE,
        filtragem="Todos os registros de desligamento; nenhuma exclusão", limitacoes=LIMITE_FLUXO,
        colunas=("desligamentos",), onde="todas as páginas"),
    Indicador(
        id="giro", nome="Giro", grupo="Fluxo do Novo CAGED",
        definicao="Volume total de movimentações (entradas mais saídas) no período.",
        formula="admissões + desligamentos",
        unidade="movimentações", fonte=FONTE_CAGED, periodo=PERIODO, abrangencia=ABRANGENCIA_RECORTE,
        filtragem="Todos os registros; nenhuma exclusão",
        limitacoes=LIMITE_FLUXO + ". Numericamente igual a \"movimentações\"",
        colunas=("giro",), onde="pipeline (outputs/), Território, Setores",
        textos={"tabelas_ajuda": "Admissões + desligamentos."}),
    Indicador(
        id="movimentacoes", nome="Movimentações", grupo="Fluxo do Novo CAGED",
        definicao="Quantidade de registros (admissões e desligamentos) do grupo.",
        formula="nº de registros",
        unidade="movimentações", fonte=FONTE_CAGED, periodo=PERIODO, abrangencia=ABRANGENCIA_RECORTE,
        filtragem="Todos os registros; nenhuma exclusão",
        limitacoes=LIMITE_FLUXO + ". Também é o peso usado nas médias ponderadas de recortes",
        colunas=("movimentacoes",), onde="todas as páginas"),
    # ------------------------------------------------------------ normalizados
    Indicador(
        id="saldo_por_10k_censo", nome="Saldo por 10 mil habitantes (população do Censo 2022)",
        grupo="Indicadores normalizados",
        definicao="Saldo de vagas proporcional ao tamanho da população, para comparar cidades de portes "
                  "diferentes (métrica pedida no guia do Datathon).",
        formula="saldo ÷ população do Censo 2022 × 10.000; em recortes com vários municípios, "
                "soma dos saldos ÷ soma das populações × 10.000",
        unidade="vagas por 10 mil habitantes", fonte=f"{FONTE_CAGED}; {FONTE_POP_CENSO}", periodo=PERIODO,
        abrangencia=ABRANGENCIA_RECORTE,
        filtragem="Todos os registros; filtro opcional de população mínima do município",
        limitacoes="A população é de 2022, anterior ao período do CAGED; municípios pequenos oscilam muito "
                   "com poucas vagas. Difere da variante com população estimada 2026 usada no Explorador",
        colunas=("saldo_por_10k",),
        onde="Painel executivo, Território, Setores, Renda e escolaridade, Contexto regional (pipeline e "
             "services/analytics.py)",
        textos={"kpi_ajuda": "Métrica do guia do Datathon: normaliza a comparação entre cidades de portes "
                             "diferentes.",
                "tabelas_ajuda": "Saldo ÷ população × 10.000."}),
    Indicador(
        id="saldo_por_10k_estimativa", nome="Saldo por 10 mil habitantes (população estimada 2026)",
        grupo="Indicadores normalizados",
        definicao="Mesma ideia do saldo por 10 mil habitantes, calculada sobre a população estimada de 2026.",
        formula="saldo ÷ população estimada 2026 × 10.000 (por município)",
        unidade="vagas por 10 mil habitantes", fonte=f"{FONTE_CAGED}; {FONTE_POP_ESTIMADA}", periodo=PERIODO,
        abrangencia="Municípios de SC, com os filtros do Explorador aplicados antes de agregar",
        filtragem="Filtros do formulário do Explorador (município, período, setor, ocupação etc.)",
        limitacoes="Usa população diferente da variante do painel (Censo 2022): o mesmo município mostra "
                   "valores diferentes nas duas variantes. A escolha de um padrão está pendente",
        colunas=("saldo_10mil",),
        onde="Municípios e Exploração estatística (services/queries.py, municipal_metrics)"),
    Indicador(
        id="giro_por_10k", nome="Giro por 10 mil habitantes", grupo="Indicadores normalizados",
        definicao="Volume de movimentações proporcional à população; giro alto com saldo baixo indica "
                  "reposição de trabalhadores.",
        formula="giro ÷ população do Censo 2022 × 10.000",
        unidade="movimentações por 10 mil habitantes", fonte=f"{FONTE_CAGED}; {FONTE_POP_CENSO}",
        periodo=PERIODO, abrangencia=ABRANGENCIA_RECORTE,
        filtragem="Todos os registros; filtro opcional de população mínima do município",
        limitacoes="População de 2022. O Explorador tem a variante \"movimentações por 10 mil habitantes\" "
                   "com população estimada 2026 (`mov_10mil`)",
        colunas=("giro_por_10k",), onde="Território (pipeline e services/analytics.py)",
        textos={"tabelas_ajuda": "Giro ÷ população × 10.000."}),
    # ------------------------------------------------------------ estoque IBGE
    Indicador(
        id="cresc_emprego_pct", nome="Crescimento do emprego formal", grupo="Indicadores sobre o estoque (IBGE)",
        definicao="Quanto o emprego formal cresceu no período em relação ao estoque de assalariados de partida.",
        formula="saldo ÷ pessoal assalariado do CEMPRE 2024 × 100; em recortes, soma dos saldos ÷ soma dos "
                "assalariados × 100",
        unidade="% do estoque de assalariados", fonte=f"{FONTE_CAGED}; {FONTE_CEMPRE}", periodo=PERIODO,
        abrangencia="Municípios, regiões e o estado; indisponível com recorte setorial",
        filtragem="Todos os registros; não calculado quando há filtro de setores (o CEMPRE municipal não é "
                  "aberto por setor)",
        limitacoes="O CEMPRE 2024 antecede o período do CAGED e é uma aproximação do estoque; não substitui "
                   "a RAIS",
        colunas=("cresc_emprego_pct",), onde="Painel executivo, Território, Contexto regional",
        textos={"kpi_ajuda": "Saldo do CAGED ÷ pessoal assalariado do CEMPRE 2024 × 100.",
                "tabelas_ajuda": "Saldo ÷ assalariados CEMPRE 2024 × 100."}),
    Indicador(
        id="rotatividade_pct", nome="Taxa de rotatividade", grupo="Indicadores sobre o estoque (IBGE)",
        definicao="Parte do fluxo que é troca de trabalhadores (reposição), e não criação líquida de vagas "
                  "(conceito do DIEESE).",
        formula="mín(admissões, desligamentos) ÷ pessoal assalariado do CEMPRE 2024 × 100; em regiões e no "
                "estado, o mínimo é tirado dos totais somados",
        unidade="% do estoque de assalariados", fonte=f"{FONTE_CAGED}; {FONTE_CEMPRE}", periodo=PERIODO,
        abrangencia="Municípios, regiões e o estado; indisponível com recorte setorial",
        filtragem="Todos os registros; não calculado quando há filtro de setores",
        limitacoes="Mesmo estoque aproximado do crescimento do emprego (CEMPRE 2024)",
        colunas=("rotatividade_pct",), onde="Painel executivo, Território, Contexto regional",
        textos={"kpi_ajuda": "Conceito DIEESE: parte do fluxo que é troca de trabalhadores, não vaga nova.",
                "kpi_nota": "reposição: mín(adm., desl.) ÷ estoque",
                "tabelas_ajuda": "Mín(admissões, desligamentos) ÷ assalariados CEMPRE 2024 × 100 (conceito DIEESE)."}),
    Indicador(
        id="part_industria_vab_2021", nome="Participação da indústria no valor adicionado (2021)",
        grupo="Indicadores sobre o estoque (IBGE)",
        definicao="Peso da indústria na economia do município ou da região.",
        formula="VAB da indústria ÷ VAB total, a preços correntes de 2021; em regiões, soma dos VAB",
        unidade="fração (exibida em %)", fonte=FONTE_PIB, periodo="2021",
        abrangencia="Municípios e regiões de SC; não muda com os filtros",
        filtragem=NA,
        limitacoes="2021 é o último ano com a abertura por atividade publicada para municípios; é anterior "
                   "ao período do CAGED",
        colunas=("part_industria_vab_2021",), onde="Painel executivo (regiões), Contexto regional",
        textos={"tabelas_ajuda": "VAB da indústria ÷ VAB total, 2021."}),
    # ---------------------------------------------------- escolaridade e renda
    Indicador(
        id="grau_medio", nome="Escolaridade média", grupo="Escolaridade e renda",
        definicao="Nível médio de instrução das movimentações, numa escala ordenada.",
        formula="média da posição ordinal do grau de instrução: 1 (analfabeto) … 9 (superior completo), "
                "10 (pós-graduação, código 80), 11 (mestrado), 12 (doutorado)",
        unidade="posição na escala de 1 a 12", fonte=f"{FONTE_CAGED}; {FONTE_DICIONARIO}", periodo=PERIODO,
        abrangencia=ABRANGENCIA_RECORTE,
        filtragem="Exclui o código 99 (não identificado)",
        limitacoes="Escala ordinal: a distância entre níveis não é uniforme, então a média serve para "
                   "comparar grupos, não para medir anos de estudo",
        colunas=("grau_medio",), onde="Renda e escolaridade, Macrofamílias, Tabelas analíticas",
        textos={"tabelas_ajuda": "Escolaridade média na escala ordinal 1 (analfabeto) a 12 (doutorado); "
                                 "'não identificado' fora."}),
    Indicador(
        id="pct_superior", nome="Com superior completo ou mais", grupo="Escolaridade e renda",
        definicao="Proporção das movimentações com ensino superior completo, pós-graduação, mestrado ou "
                  "doutorado.",
        formula="nº com grau 9, 80, 10 ou 11 ÷ nº com grau identificado",
        unidade="fração (exibida em %)", fonte=f"{FONTE_CAGED}; {FONTE_DICIONARIO}", periodo=PERIODO,
        abrangencia=ABRANGENCIA_RECORTE,
        filtragem="O código 99 (não identificado) fica fora do numerador e do denominador",
        limitacoes="Descreve quem foi admitido ou desligado, não a escolaridade de toda a força de trabalho",
        colunas=("pct_superior",), onde="Painel executivo, Macrofamílias, Tabelas analíticas",
        textos={"tabelas_ajuda": "Fração das movimentações com superior completo, pós, mestrado ou doutorado."}),
    Indicador(
        id="salario_medio", nome="Salário médio nas movimentações", grupo="Escolaridade e renda",
        definicao="Média do salário mensal declarado nas admissões e desligamentos (definição atual, em "
                  "revisão na etapa 3.2 do projeto).",
        formula="média aritmética de `salário` de todos os registros do grupo; em recortes, média dos grupos "
                "ponderada pelo nº de movimentações",
        unidade="R$ por mês", fonte=f"{FONTE_CAGED}; {FONTE_DICIONARIO} (`salário` = salário mensal declarado)",
        periodo=PERIODO, abrangencia=ABRANGENCIA_RECORTE,
        filtragem="Nenhuma exclusão: inclui salários zerados e todas as periodicidades de pagamento",
        limitacoes="Inclui 33.912 salários iguais a zero; registros cujo valor não é mensal (parte fixa paga "
                   "por semana ou por tarefa); e periodicidades quase sempre sem valor (variável, não "
                   "identificado). 535 valores acima de R$ 50 mil puxam a média",
        colunas=("salario_medio",), onde="Painel executivo, análises complementares, Tabelas analíticas",
        textos={"kpi_ajuda": "Média do salário declarado em admissões e desligamentos, ponderada pelo nº de "
                             "movimentações."}),
    # ------------------------------------------------------------ classificação
    Indicador(
        id="macrofamilia", nome="Macrofamília de ocupações", grupo="Classificação",
        definicao="Agrupamento analítico do projeto: ocupações reunidas pelo Grande Grupo da CBO-2002.",
        formula="1º dígito do código CBO de 6 dígitos; os grupos 7 e 8 formam a macrofamília operacional; "
                "nomes atribuídos pelo projeto",
        unidade=NA, fonte=f"{FONTE_CAGED} (`cbo2002ocupação`); estrutura da CBO-2002", periodo=PERIODO,
        abrangencia="Santa Catarina inteira; versão só com seções industriais (B, C, D, F)",
        filtragem="Todas as ocupações; códigos sem 1º dígito válido ficam como \"Não classificado\"",
        limitacoes="Não é a nomenclatura oficial da CBO: usa nomes próprios e funde os grupos 7 e 8",
        colunas=("cbo_grande_grupo",), onde="Painel executivo, Macrofamílias, Tabelas analíticas"),
    Indicador(
        id="periodo", nome="Período de referência", grupo="Referência",
        definicao="Intervalo de meses coberto pelos dados do Novo CAGED usados no projeto.",
        formula=NA, unidade="meses (competência)", fonte=FONTE_CAGED, periodo=PERIODO,
        abrangencia="Todas as páginas",
        filtragem="Competência de declaração; declarações fora do prazo entram pelo mês em que foram declaradas",
        limitacoes="Por competência de movimentação, há registros desde set/2024 (declarações fora do prazo)",
        textos={"painel": PERIODO}),
)

NOTAS: dict[str, Nota] = {
    "mapa_formulas": Nota(
        "Saldo por 10 mil hab. = (admissões − desligamentos) ÷ população × 10.000. "
        "Crescimento do emprego = saldo ÷ assalariados do CEMPRE 2024 × 100 (só sem recorte setorial).",
        ("saldo_por_10k_censo", "cresc_emprego_pct")),
    "limite_fluxo": Nota(
        "Limite: o CAGED mede fluxo de admissões e desligamentos, não o estoque de empregos.", ("saldo",)),
    "regioes_formulas": Nota(
        "Crescimento = saldo ÷ assalariados do CEMPRE 2024 × 100. Rotatividade = mín(admissões, "
        "desligamentos) ÷ assalariados × 100 (conceito DIEESE): a parte do fluxo que é troca de "
        "trabalhadores, não vaga nova.",
        ("cresc_emprego_pct", "rotatividade_pct")),
    "regioes_leitura": Nota(
        "Leitura: regiões no alto e à esquerda trocam muitos trabalhadores sem crescer — sinal de "
        "dificuldade de reter mão de obra. Limite: o CEMPRE 2024 é uma aproximação do estoque.",
        ("cresc_emprego_pct", "rotatividade_pct")),
    "macro_agrupamento": Nota(
        "Agrupamento determinístico pelo 1º dígito do código CBO-2002 (Grande Grupo); os grupos 7 e 8 "
        "formam a macrofamília operacional.",
        ("macrofamilia",)),
    "macro_salario": Nota(
        "Salário médio inclui todos os salários declarados (ver limites no fim da página).", ("salario_medio",)),
    "salario_relacao": Nota(
        "Relação descritiva: mostra quanto cada grupo recebe em média, não que a escolaridade cause "
        "a diferença. Limite: a média inclui salários zerados e não mensais.",
        ("salario_medio",)),
    "dispersao_relacao": Nota(
        "Relação descritiva entre três medidas do mesmo município; não indica causa.",
        ("salario_medio", "pct_superior", "saldo_por_10k_censo")),
    "renda_ressalva": Nota(
        "Ressalva metodológica: as médias incluem salários informados como zero e valores "
        "de periodicidade não mensal (sobretudo por hora; também por dia, semana, tarefa "
        "ou variável).",
        ("salario_medio",)),
}

_BY_ID = {i.id: i for i in INDICADORES}


def indicador(id_: str) -> Indicador:
    return _BY_ID[id_]


def texto(id_: str, chave: str) -> str:
    """Texto de exibição literal de um indicador (ex.: texto("saldo", "kpi_ajuda"))."""
    return _BY_ID[id_].textos[chave]


def nota(id_: str) -> str:
    return NOTAS[id_].texto


def ajuda_colunas() -> dict[str, str]:
    """Coluna -> texto de ajuda da página Tabelas analíticas, na ordem em que era exibido."""
    ordem = ["saldo", "giro", "saldo_por_10k_censo", "giro_por_10k", "grau_medio", "pct_superior",
             "cresc_emprego_pct", "rotatividade_pct", "part_industria_vab_2021"]
    return {_BY_ID[i].colunas[0]: _BY_ID[i].textos["tabelas_ajuda"] for i in ordem}


# ------------------------------------------------------------- documento legível

ROTULOS = {"definicao": "Definição", "formula": "Fórmula", "unidade": "Unidade", "fonte": "Fonte",
           "periodo": "Período", "abrangencia": "Abrangência", "filtragem": "Regras de filtragem",
           "limitacoes": "Limitações"}


def markdown() -> str:
    """Versão legível do glossário (é o conteúdo de docs/glossario.md)."""
    out = ["# Glossário de indicadores — Raio-X Industrial SC", "",
           "> Arquivo gerado por `python -m src.glossario` a partir de `src/glossario.py`. "
           "Não edite à mão: edite o módulo e gere de novo.", ""]
    grupos: dict[str, list[Indicador]] = {}
    for ind in INDICADORES:
        grupos.setdefault(ind.grupo, []).append(ind)
    for grupo, inds in grupos.items():
        out += [f"## {grupo}", ""]
        for ind in inds:
            out += [f"### {ind.nome}", ""]
            if ind.colunas:
                out.append(f"- **Coluna nos dados:** {', '.join(f'`{c}`' for c in ind.colunas)}")
            if ind.onde:
                out.append(f"- **Onde aparece:** {ind.onde}")
            for campo, rot in ROTULOS.items():
                out.append(f"- **{rot}:** {getattr(ind, campo)}")
            out.append("")
    out += ["## Notas de método exibidas no painel", ""]
    for nid, nt in NOTAS.items():
        nomes = ", ".join(_BY_ID[i].nome for i in nt.indicadores)
        out.append(f"- **{nid}** ({nomes}): {nt.texto}")
    return "\n".join(out) + "\n"


DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "glossario.md"

if __name__ == "__main__":
    DOC_PATH.write_text(markdown(), encoding="utf-8")
    print(f"gerado: {DOC_PATH} ({len(INDICADORES)} indicadores, {len(NOTAS)} notas)")
