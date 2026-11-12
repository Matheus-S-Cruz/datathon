"""Constatações da auditoria, recalculadas a partir dos arquivos reais.

Cada `Finding` responde às seis perguntas da página de auditoria:
o que foi encontrado, como foi calculado (com o SQL), quantos registros,
por que importa, o que recomendamos e qual a situação.

`natureza` separa explicitamente constatação de hipótese:
- "Constatação verificada": número medido agora nos arquivos;
- "Hipótese": interpretação plausível, ainda não comprovada;
- "Limitação": característica da base que restringe a análise;
- "Resultado exploratório": descrição de distribuição, sem juízo de qualidade.

`documentado` guarda o valor publicado em docs/diagnostico_inicial.md (ou em
docs/dicionario_analitico.md) para conferir se a auditoria é reproduzível.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from dashboard import formatting as fmt
from dashboard.services import queries as Q
from dashboard.services.catalog import CAGED_COLUMNS, MONEY, QUANT, SIGN, q
from dashboard.services.dictionary import layout_table, load_sheets
from dashboard.services.municipalities import load_municipalities
from src.config import CAGED_PARQUET, MUNICIPIOS_CSV, ROOT

VERIFIED = "Constatação verificada"
HYPOTHESIS = "Hipótese"
LIMITATION = "Limitação"
EXPLORATORY = "Resultado exploratório"

RESOLVED = "Resolvido"
HANDLED = "Tratado no app; falta no pipeline"
PENDING = "Pendente"
EXTERNAL = "Exige validação externa"
NO_ACTION = "Sem ação necessária"

DOC = "docs/diagnostico_inicial.md"
DOC_DIC = "docs/dicionario_analitico.md"

CATEGORIES = ["A. Integridade", "B. Distribuição", "C. Remuneração", "D. Relacionamentos"]


@dataclass
class Finding:
    id: str
    categoria: str
    titulo: str
    natureza: str
    situacao: str
    o_que: str
    como: str
    registros: int | None
    porque: str
    recomendacao: str
    sql: str | None = None
    documentado: str | None = None     # valor publicado na auditoria inicial
    confere: bool | None = None        # o valor recalculado bate com o documentado?
    detalhe: pd.DataFrame | None = None
    extras: dict = field(default_factory=dict)

    def __post_init__(self):
        # comparações com pandas/numpy devolvem numpy.bool_; normaliza para bool nativo
        if self.confere is not None:
            self.confere = bool(self.confere)
        if self.registros is not None:
            self.registros = int(self.registros)


def _n(sql: str, params=()) -> int:
    value = Q.run(sql, params).iloc[0, 0]
    return int(value) if pd.notna(value) else 0


def _fmt(n) -> str:
    return fmt.integer(n)


# ===================================================================== A. Integridade


def integrity() -> list[Finding]:
    out: list[Finding] = []
    total = _n("SELECT count(*) FROM caged_raw")

    # A1 — ausentes / vazios
    exprs = ", ".join(
        f"count(*) FILTER (WHERE {q(c.name)} IS NULL) AS {q(c.name + '|nulos')}, "
        f"count(*) FILTER (WHERE trim({q(c.name)}) = '') AS {q(c.name + '|vazios')}"
        for c in CAGED_COLUMNS)
    sql = f"SELECT {exprs} FROM caged_raw"
    row = Q.run(sql).iloc[0]
    det = pd.DataFrame([{"coluna": c.name, "nulos": int(row[c.name + "|nulos"]),
                         "vazios": int(row[c.name + "|vazios"])} for c in CAGED_COLUMNS])
    det["% do total"] = (det["nulos"] + det["vazios"]) / total
    affected = det[(det["nulos"] + det["vazios"]) > 0]
    n_idade = int(det.loc[det.coluna == "idade", "vazios"].iloc[0])
    out.append(Finding(
        "A1", CATEGORIES[0], "Valores ausentes no Novo CAGED", VERIFIED, PENDING,
        f"{len(affected)} coluna(s) com valores nulos ou vazios: "
        + (", ".join(f"`{r.coluna}` ({_fmt(r.nulos + r.vazios)})" for r in affected.itertuples()) or "nenhuma")
        + ". Nenhuma coluna tem NULL de fato; a ausência aparece como texto vazio.",
        "Contagem, coluna a coluna, de valores NULL e de textos vazios (após remover espaços).",
        int((det["nulos"] + det["vazios"]).sum()),
        "Idade vazia não pode entrar em médias nem em faixas etárias; é preciso decidir se esses "
        "registros saem só das análises de idade ou de todas.",
        "Excluir os vazios apenas das estatísticas de idade e informar o n utilizado.",
        sql=sql, documentado=f"idade: 2.202 vazios ({DOC_DIC})", confere=(n_idade == 2202),
        detalhe=det))

    # A2 — tipos inadequados (tudo texto) e falhas de conversão
    types = Q.run("SELECT column_name, column_type FROM (DESCRIBE caged_raw) WHERE column_name <> 'linha'")
    n_varchar = int((types["column_type"] == "VARCHAR").sum())
    conv_cols = [c for c in CAGED_COLUMNS if c.kind in (MONEY, QUANT, SIGN)]
    # As colunas originais também estão na view `caged`; uma única varredura basta.
    sql_conv = "SELECT " + ", ".join(
        f"count(*) FILTER (WHERE trim({q(c.name)}) <> '' AND {c.typed} IS NULL) AS {c.typed}"
        for c in conv_cols) + ", count(*) FILTER (WHERE idade_anos IS NOT NULL AND idade_anos <> floor(idade_anos)) AS idade_fracionaria FROM caged"
    conv = Q.run(sql_conv).iloc[0]
    det_conv = pd.DataFrame([{"coluna": c.name, "convertida para": c.typed,
                              "tipo": c.kind, "valores que não converteram": int(conv[c.typed])}
                             for c in conv_cols])
    fails = int(det_conv["valores que não converteram"].sum())
    out.append(Finding(
        "A2", CATEGORIES[0], "Todas as colunas armazenadas como texto", VERIFIED, HANDLED,
        f"{n_varchar} de {len(types)} colunas do Parquet são VARCHAR. Decimais usam vírgula "
        f"(`2018,00`) e a idade vem como `40.0`. Na conversão feita por esta aplicação, "
        f"{_fmt(fails)} valor(es) não vazio(s) falharam; {_fmt(int(conv['idade_fracionaria']))} idade(s) "
        f"têm parte fracionária.",
        "DESCRIBE do Parquet + tentativa de conversão (TRY_CAST) de cada coluna quantitativa, "
        "contando os valores preenchidos que viraram NULL.",
        fails,
        "Somar ou ordenar texto dá resultado errado (ex.: '900' > '1000'). Uma falha de conversão "
        "silenciosa removeria registros das estatísticas sem ninguém perceber.",
        "Manter a etapa de tipagem explícita do pipeline (plano, etapa 1) e conferir esta contagem a cada carga.",
        sql=sql_conv, documentado=f"30 colunas VARCHAR ({DOC}, Q3)", confere=(n_varchar == 30),
        detalhe=det_conv))

    # A3 — linhas idênticas
    cols = ", ".join(q(c.name) for c in CAGED_COLUMNS if not c.name.startswith("Unnamed"))
    sql_dup = f"""
        SELECT sum(n) - count(*) AS linhas_repetidas, count(*) AS grupos, max(n) AS maior_grupo
        FROM (SELECT count(*) AS n FROM caged_raw GROUP BY {cols} HAVING count(*) > 1)"""
    dup = Q.run(sql_dup).iloc[0]
    rep = int(dup["linhas_repetidas"] or 0)
    out.append(Finding(
        "A3", CATEGORIES[0], "Linhas idênticas em todas as colunas", VERIFIED, PENDING,
        f"{_fmt(rep)} linhas ({fmt.pct(rep / total, 2)}) repetem exatamente outra linha em todas as colunas "
        f"(exceto os índices de exportação). Elas formam {_fmt(dup['grupos'])} grupos; o maior tem "
        f"{_fmt(dup['maior_grupo'])} linhas iguais.",
        "Agrupamento por todas as 28 colunas de conteúdo; linhas repetidas = soma dos grupos − nº de grupos.",
        rep,
        "**Não é possível afirmar que sejam duplicidades indevidas.** O microdado não identifica o "
        "trabalhador nem a empresa: duas contratações para o mesmo cargo, no mesmo mês, com o mesmo "
        "salário e perfil geram linhas idênticas legítimas (contratações em lote).",
        "Não remover. Documentar e, se necessário, testar a sensibilidade dos indicadores com e sem essas linhas.",
        sql=sql_dup, documentado=f"97.635 linhas ({DOC}, Q9)", confere=(rep == 97635),
        extras={"hipotese": "Parte das linhas pode ser duplicidade de envio, hipótese não verificável com estes dados."}))

    # A4 — zeros à esquerda perdidos
    sql_pad = """SELECT count(*) FILTER (WHERE length(trim(subclasse)) = 6) AS subclasse_6,
                        count(*) FILTER (WHERE length(trim(cbo2002ocupação)) = 5) AS cbo_5,
                        count(*) FILTER (WHERE length(trim(município)) <> 6) AS municipio_fora_6,
                        count(*) FILTER (WHERE length(trim(subclasse)) NOT IN (6, 7)) AS subclasse_outro,
                        count(*) FILTER (WHERE length(trim(cbo2002ocupação)) NOT IN (5, 6)) AS cbo_outro
                 FROM caged_raw"""
    pad = Q.run(sql_pad).iloc[0]
    out.append(Finding(
        "A4", CATEGORIES[0], "Códigos sem zero à esquerda", VERIFIED, HANDLED,
        f"{_fmt(pad['subclasse_6'])} subclasses CNAE têm 6 dígitos (o padrão é 7) e "
        f"{_fmt(pad['cbo_5'])} CBOs têm 5 dígitos (padrão 6). Outros comprimentos: "
        f"subclasse {_fmt(pad['subclasse_outro'])}, CBO {_fmt(pad['cbo_outro'])}, município {_fmt(pad['municipio_fora_6'])}.",
        "Comprimento do texto de cada código.",
        int(pad["subclasse_6"] + pad["cbo_5"]),
        "Sem o zero, a junção com o dicionário falha e a divisão CNAE (2 primeiros dígitos) sai errada "
        "(ex.: '111301' viraria divisão 11 em vez de 01).",
        "Restaurar com lpad (subclasse 7, CBO 6). Esta aplicação já faz isso na view tipada.",
        sql=sql_pad, documentado=f"105.072 subclasses e 8 CBOs ({DOC}, Q6)",
        confere=(int(pad["subclasse_6"]) == 105072 and int(pad["cbo_5"]) == 8)))

    # A5 — coerência saldo × tipo de movimentação
    sql_tm = """SELECT tipo_mov, saldo, count(*) AS n FROM caged GROUP BY ALL ORDER BY tipo_mov, saldo"""
    tm = Q.run(sql_tm)
    tm["descricao"] = tm["tipo_mov"].map(lambda c: Q.describe("tipomovimentação", c))
    adm_types = {"10", "20", "25", "35", "70", "97"}
    tm["esperado"] = tm["tipo_mov"].map(lambda t: 1 if t in adm_types else -1)
    incoh = int(tm.loc[tm["saldo"] != tm["esperado"], "n"].sum())
    out.append(Finding(
        "A5", CATEGORIES[0], "Coerência entre saldo e tipo de movimentação", VERIFIED,
        NO_ACTION if incoh == 0 else PENDING,
        f"{_fmt(incoh)} registro(s) com saldo incompatível com o tipo (ex.: tipo de admissão com saldo −1).",
        "Cruzamento `tipomovimentação` × `saldomovimentação`. Tipos de admissão (dicionário): 10, 20, 25, 35, 70, 97; demais = desligamento.",
        incoh,
        "Admissões e desligamentos são contados pelo saldo. Se o saldo contradissesse o tipo, os volumes estariam errados.",
        "Nenhuma ação se o resultado for zero; caso contrário, investigar os registros.",
        sql=sql_tm, detalhe=tm))

    # A6 — fora do prazo × competências
    sql_fp = """SELECT count(*) FILTER (WHERE fora_prazo = '1') AS fora_prazo,
                       count(*) FILTER (WHERE competencia_mov <> competencia_dec) AS meses_diferentes,
                       count(*) FILTER (WHERE (fora_prazo = '1') <> (competencia_mov <> competencia_dec)) AS divergentes
                FROM caged"""
    fp = Q.run(sql_fp).iloc[0]
    out.append(Finding(
        "A6", CATEGORIES[0], "Movimentações declaradas fora do prazo", VERIFIED, PENDING,
        f"{_fmt(fp['fora_prazo'])} registros ({fmt.pct(fp['fora_prazo'] / total, 2)}) têm indicador de fora do prazo = 1; "
        f"{_fmt(fp['meses_diferentes'])} têm competência da movimentação ≠ da declaração. "
        f"Registros em que as duas condições divergem: {_fmt(fp['divergentes'])}.",
        "Comparação de `indicadordeforadoprazo` com a igualdade entre `competênciamov` e `competênciadec`.",
        int(fp["fora_prazo"]),
        "Define qual mês usar: a declaração cobre exatamente 12 meses; a movimentação inclui meses anteriores.",
        "Decisão da equipe (diagnóstico, E3): totais por competência da declaração; séries mensais por movimentação dentro da janela.",
        sql=sql_fp, documentado=f"36.940 (1,09%), coincidentes ({DOC})",
        confere=(int(fp["fora_prazo"]) == 36940 and int(fp["divergentes"]) == 0)))

    # A7 — admissões sem subtipo
    sql_adm = """SELECT count(*) FILTER (WHERE saldo = 1) AS admissoes,
                        count(*) FILTER (WHERE saldo = 1 AND tipo_mov = '97') AS tipo_ignorado,
                        count(*) FILTER (WHERE tipo_mov IN ('10', '20', '25', '70')) AS com_subtipo
                 FROM caged"""
    adm = Q.run(sql_adm).iloc[0]
    out.append(Finding(
        "A7", CATEGORIES[0], "Admissões sem subtipo", LIMITATION, PENDING,
        f"{_fmt(adm['tipo_ignorado'])} das {_fmt(adm['admissoes'])} admissões são `97` (Admissão de Tipo Ignorado). "
        f"Códigos 10, 20, 25 e 70 aparecem em {_fmt(adm['com_subtipo'])} registros.",
        "Contagem de `tipomovimentação` entre os registros com saldo +1.",
        int(adm["tipo_ignorado"]),
        "Não é possível separar primeiro emprego de reemprego, nem contratos por prazo determinado na entrada.",
        "Tratar admissão como categoria única e registrar a limitação no pitch.",
        sql=sql_adm, documentado=f"1.718.686 de 1.719.449 ({DOC}, Q2)",
        confere=(int(adm["tipo_ignorado"]) == 1718686)))

    # A8 — porte ausente no último mês
    sql_tam = """SELECT competencia_dec, count(*) AS n, count(*) FILTER (WHERE tam_estab = '99') AS ignorado
                 FROM caged GROUP BY 1 ORDER BY 1"""
    tam = Q.run(sql_tam)
    last = tam.iloc[-1]
    out.append(Finding(
        "A8", CATEGORIES[0], "Porte do estabelecimento ausente no último mês", VERIFIED, PENDING,
        f"Em {Q.competencia_label(last['competencia_dec'])}, {_fmt(last['ignorado'])} de {_fmt(last['n'])} registros "
        f"têm `tamestabjan = 99` (Ignorado). Nos demais meses: {_fmt(tam.iloc[:-1]['ignorado'].sum())}.",
        "Contagem de `tamestabjan = 99` por competência da declaração.",
        int(last["ignorado"]),
        "Qualquer análise por porte perde o último mês inteiro.",
        "Excluir o último mês das análises por porte ou não usar o campo.",
        sql=sql_tam, documentado=f"272.463 em 202608 ({DOC}, Q8)",
        confere=(int(last["ignorado"]) == 272463 and last["ignorado"] == last["n"]), detalhe=tam))

    # A9 — exclusões ausentes
    layout = layout_table(load_sheets())
    raw_cols = set(types["column_name"])
    only_dic = [v for v in layout["variavel"] if v not in raw_cols]
    out.append(Finding(
        "A9", CATEGORIES[0], "Campos de exclusão ausentes na base", VERIFIED, EXTERNAL,
        f"O dicionário descreve {len(layout)} variáveis; {len(only_dic)} não existem no Parquet: "
        + ", ".join(f"`{v}`" for v in only_dic) + ".",
        "Comparação entre a aba `Layout` do dicionário e as colunas do Parquet.",
        None,
        "O guia pede para 'aplicar a filtragem das exclusões (MOV × EX)', mas não há como identificar exclusões.",
        "Perguntar à organização (diagnóstico, E1). Hipótese: o sufixo 'Limpo' indica que as exclusões já foram removidas.",
        documentado=f"competênciaexc e indicadordeexclusão ({DOC}, Q1)",
        confere=(set(only_dic) == {"competênciaexc", "indicadordeexclusão"}),
        extras={"hipotese": "A base 'Limpo' já teria as exclusões removidas, mas isso não foi confirmado pela organização."}))

    # A10 — escolaridade 80 fora de ordem
    n80 = _n("SELECT count(*) FROM caged WHERE escolaridade = '80'")
    out.append(Finding(
        "A10", CATEGORIES[0], "Grau de instrução 80 fora da ordem numérica", VERIFIED, HANDLED,
        f"O código `80` (Pós-Graduação completa, {_fmt(n80)} registros) fica numericamente depois de "
        "`11` (Doutorado), embora represente nível entre Superior completo e Mestrado.",
        "Contagem de `graudeinstrução = 80` e leitura da aba `graudeinstrução` do dicionário.",
        n80,
        "Ordenar ou calcular médias pelo código numérico distorce a escala de escolaridade.",
        "Usar ordem explícita (… 9 < 80 < 10 < 11). Esta aplicação já ordena assim.",
        sql="SELECT count(*) FROM caged WHERE escolaridade = '80'",
        documentado=f"33.303 ({DOC}, Q5)", confere=(n80 == 33303)))

    # A11 — colunas constantes e índices
    sql_const = """SELECT count(DISTINCT região) AS regiao, count(DISTINCT uf) AS uf,
                          count(DISTINCT "Unnamed: 0.1") AS idx1, count(DISTINCT "Unnamed: 0") AS idx2
                   FROM caged_raw"""
    cst = Q.run(sql_const).iloc[0]
    out.append(Finding(
        "A11", CATEGORIES[0], "Colunas constantes e índices de exportação", VERIFIED, PENDING,
        f"`região` tem {cst['regiao']} valor distinto e `uf` tem {cst['uf']}. `Unnamed: 0.1` tem "
        f"{_fmt(cst['idx1'])} valores distintos (único por linha) e `Unnamed: 0` tem {_fmt(cst['idx2'])}.",
        "Contagem de valores distintos.",
        total,
        "Colunas sem variação ou artefatos de exportação só ocupam espaço e confundem quem explora a base.",
        "Descartar no pipeline. Nesta aplicação, a linha física do arquivo (`linha`) é o identificador do registro.",
        sql=sql_const, documentado=f"região/uf constantes; Unnamed: 0 com 2.434.896 distintos ({DOC_DIC})",
        confere=(int(cst["idx2"]) == 2434896 and cst["regiao"] == 1 and cst["uf"] == 1)))

    # A12 — EmpregadoWEB (teste de uma hipótese da auditoria)
    sql_web = """SELECT count(*) FILTER (WHERE origem = '3') AS empregadoweb,
                        count(*) FILTER (WHERE categoria_cod = '999') AS categoria_999,
                        count(*) FILTER (WHERE horas = 0) AS horas_zero,
                        count(*) FILTER (WHERE intermitente = '9') AS intermitente_9,
                        count(*) FILTER (WHERE origem = '3' AND categoria_cod = '999' AND horas = 0
                                         AND intermitente = '9') AS todos_juntos
                 FROM caged"""
    web = Q.run(sql_web).iloc[0]
    same = len({int(web[k]) for k in ["empregadoweb", "categoria_999", "horas_zero", "intermitente_9", "todos_juntos"]}) == 1
    out.append(Finding(
        "A12", CATEGORIES[0], "Registros de origem EmpregadoWEB", VERIFIED, NO_ACTION if same else PENDING,
        f"{_fmt(web['empregadoweb'])} registros com origem = 3 (EmpregadoWEB). Categoria 999: {_fmt(web['categoria_999'])}; "
        f"horas = 0: {_fmt(web['horas_zero'])}; intermitente = 9: {_fmt(web['intermitente_9'])}; "
        f"as quatro condições ao mesmo tempo: {_fmt(web['todos_juntos'])}. "
        + ("**A hipótese da auditoria inicial (são os mesmos registros) está confirmada.**" if same
           else "**A hipótese da auditoria inicial (são os mesmos registros) NÃO se confirma.**"),
        "Contagem de cada condição e da interseção das quatro.",
        int(web["empregadoweb"]),
        "Esses registros têm campos de jornada e categoria não informados; volume desprezível.",
        "Manter; excluir apenas de análises de jornada.",
        sql=sql_web, documentado=f"hipótese: mesmos 510 registros ({DOC}, Q11)", confere=same))

    # A13 — base de municípios: estrutura
    mun = load_municipalities()
    miss = {k: v for k, v in mun.missing_dash.items() if v}
    invalid = sum(mun.invalid.values())
    out.append(Finding(
        "A13", CATEGORIES[0], "Problemas de estrutura na base de municípios", VERIFIED, HANDLED,
        f"O arquivo tem {mun.total_rows_in_file} linhas: {len(mun.data)} municípios e {mun.footer_rows} linha(s) "
        f"de rodapé em HTML. Colunas vazias: {', '.join(mun.empty_columns) or 'nenhuma'}. Cabeçalhos com HTML (`<span>`). "
        f"Ausentes marcados com '-': " + (", ".join(f"{mun.labels[k]} ({v})" for k, v in miss.items()) or "nenhum")
        + f". Valores não numéricos além de '-': {invalid}.",
        "Leitura do CSV como texto; município = código com 7 dígitos; contagem de '-' por coluna.",
        sum(miss.values()) + mun.footer_rows,
        "Uma leitura ingênua cria um 'município' falso (o rodapé) e trata '-' como texto, quebrando as contas.",
        "Filtrar códigos de 7 dígitos, descartar a coluna vazia, converter '-' em ausente. Esta aplicação já faz isso. "
        "Mortalidade infantil tem muitos ausentes: evitar.",
        documentado=f"IDHM: 2; mortalidade: 123 ({DOC}, Q12/Q14)",
        confere=(miss.get("idhm") == 2 and miss.get("mortalidade_infantil") == 123 and mun.footer_rows == 1)))

    # A14 — rótulos de ano inconsistentes
    footer = MUNICIPIOS_CSV.read_text(encoding="utf-8").splitlines()[-1]
    flags = {"Rodapé cita 'julho de 2024' para a população estimada": "julho de 2024" in footer,
             "Cabeçalho da população estimada diz [2026]": "[2026]" in mun.labels["pop_estimada"],
             "Rodapé cita 'Censo Demográfico 2010' para a escolarização": "Censo Demográfico 2010" in footer,
             "Cabeçalho da escolarização diz [2022]": "[2022]" in mun.labels["escolarizacao"]}
    out.append(Finding(
        "A14", CATEGORIES[0], "Anos de referência inconsistentes nos rótulos municipais", LIMITATION, EXTERNAL,
        "; ".join(f"{k}: {'sim' if v else 'não'}" for k, v in flags.items()) + ".",
        "Busca de texto no rodapé e nos cabeçalhos do CSV.",
        None,
        "Citar o ano errado no pitch compromete a credibilidade.",
        "Citar a fonte descrita no rodapé ou dizer 'estimativa mais recente fornecida pela organização'.",
        documentado=f"{DOC}, Q13", confere=all(flags.values())))
    return out


# ===================================================================== B. Distribuição


def distribution() -> list[Finding]:
    out: list[Finding] = []
    k = Q.overview_kpis()
    out.append(Finding(
        "B1", CATEGORIES[1], "Admissões e desligamentos", VERIFIED, NO_ACTION,
        f"{_fmt(k['admissoes'])} admissões, {_fmt(k['desligamentos'])} desligamentos, saldo "
        f"{fmt.signed(k['saldo'])}. Registros com saldo diferente de ±1: {_fmt(k['saldo_invalido'])}.",
        "Contagem de `saldomovimentação = 1` e `= -1`; saldo = soma.",
        int(k["registros"]),
        "É a base de todos os indicadores de movimentação.",
        "Sem ação. Lembrar que o CAGED mede fluxo, não estoque nem vagas.",
        sql="SELECT count(*) FILTER (WHERE saldo = 1), count(*) FILTER (WHERE saldo = -1), sum(saldo) FROM caged",
        documentado=f"1.719.449 / 1.677.967 / +41.482 ({DOC})",
        confere=(k["admissoes"] == 1719449 and k["desligamentos"] == 1677967 and int(k["saldo"]) == 41482)))

    dec = Q.flow_by("competencia_dec")
    mov = Q.flow_by("competencia_mov")
    mov_in = mov[mov["competencia_mov"] >= k["dec_min"]]   # só a janela de 12 meses
    out.append(Finding(
        "B2", CATEGORIES[1], "Distribuição por competência", EXPLORATORY, PENDING,
        f"Declaração: {len(dec)} meses ({Q.competencia_label(k['dec_min'])} a {Q.competencia_label(k['dec_max'])}), "
        f"de {_fmt(dec['movimentacoes'].min())} a {_fmt(dec['movimentacoes'].max())} registros por mês. "
        f"Movimentação: {len(mov)} meses ({Q.competencia_label(k['mov_min'])} a {Q.competencia_label(k['mov_max'])}). "
        f"Menor saldo mensal (declaração): {Q.competencia_label(dec.loc[dec['saldo'].idxmin(), 'competencia_dec'])} "
        f"({fmt.signed(dec['saldo'].min())}); por movimentação: "
        f"{Q.competencia_label(mov_in.loc[mov_in['saldo'].idxmin(), 'competencia_mov'])} "
        f"({fmt.signed(mov_in['saldo'].min())}).",
        "Agregação por `competênciadec` e por `competênciamov`.",
        int(k["registros"]),
        "Sazonalidade (fim de ano, safras) muda o saldo mês a mês; comparar meses isolados engana.",
        "Mostrar a série mensal e comparar janelas completas de 12 meses.",
        documentado=f"12 meses (declaração), 24 valores (movimentação); 202512 com saldo −48.616 ({DOC}, M3)",
        confere=(len(dec) == 12 and len(mov) == 24
                 and int(mov.loc[mov["competencia_mov"] == "202512", "saldo"].sum()) == -48616),
        detalhe=dec, extras={"mov": mov}))

    mun = Q.flow_by("municipio").sort_values("movimentacoes", ascending=False)
    top5 = mun["movimentacoes"].head(5).sum() / mun["movimentacoes"].sum()
    out.append(Finding(
        "B3", CATEGORIES[1], "Distribuição por município", EXPLORATORY, NO_ACTION,
        f"{len(mun)} municípios com movimentação. Os 5 maiores concentram {fmt.pct(top5, 1)} dos registros; "
        f"o menor tem {_fmt(mun['movimentacoes'].min())} movimentações.",
        "Agregação por `município`, com nome vindo da base municipal.",
        int(mun["movimentacoes"].sum()),
        "Municípios pequenos geram taxas instáveis (poucos casos viram números grandes por habitante).",
        "Definir volume mínimo antes de ranquear municípios por taxas.",
        detalhe=mun))

    sec = Q.flow_by("secao").sort_values("movimentacoes", ascending=False)
    n_c = int(sec.loc[sec["secao"] == "C", "movimentacoes"].sum())
    out.append(Finding(
        "B4", CATEGORIES[1], "Distribuição por seção CNAE", EXPLORATORY, PENDING,
        f"{len(sec)} seções. Indústria de Transformação (C): {_fmt(n_c)} registros "
        f"({fmt.pct(n_c / k['registros'], 1)}).",
        "Agregação por `seção`.",
        n_c,
        "O escopo 'industrial' ainda não foi decidido: só C, ou B a F (inclui construção)?",
        "Decisão da equipe (diagnóstico, E2).",
        documentado=f"22 seções; C = 836.753 ({DOC})", confere=(len(sec) == 22 and n_c == 836753),
        detalhe=sec))

    cbo = Q.flow_by("cbo").sort_values("movimentacoes", ascending=False)
    out.append(Finding(
        "B5", CATEGORIES[1], "Distribuição por ocupação (CBO)", EXPLORATORY, NO_ACTION,
        f"{_fmt(len(cbo))} CBOs distintos. Os 20 mais frequentes somam "
        f"{fmt.pct(cbo['movimentacoes'].head(20).sum() / cbo['movimentacoes'].sum(), 1)} das movimentações.",
        "Agregação por CBO (6 dígitos, com zero à esquerda restaurado).",
        int(cbo["movimentacoes"].sum()),
        "A cauda longa de ocupações é o que motiva o agrupamento em macrofamílias.",
        "Agrupamento será discutido em etapa posterior.",
        documentado=f"2.207 CBOs ({DOC_DIC})", confere=(len(cbo) == 2207), detalhe=cbo))

    edu = Q.flow_by("escolaridade")
    top = edu.loc[edu["movimentacoes"].idxmax()]
    out.append(Finding(
        "B6", CATEGORIES[1], "Distribuição por escolaridade", EXPLORATORY, NO_ACTION,
        f"{len(edu)} níveis presentes. Moda: `{top['escolaridade']}` {top['escolaridade_descricao']} "
        f"({_fmt(top['movimentacoes'])}, {fmt.pct(top['movimentacoes'] / k['registros'], 1)}).",
        "Agregação por `graudeinstrução`, em ordem ordinal explícita.",
        int(k["registros"]),
        "É a escolaridade declarada do trabalhador, não a exigida pela vaga.",
        "Comparar perfis de admitidos × desligados dentro do mesmo setor.",
        documentado=f"moda 7 = 2.032.882 (59,8%) ({DOC_DIC})",
        confere=(top["escolaridade"] == "7" and int(top["movimentacoes"]) == 2032882), detalhe=edu))
    return out


# ===================================================================== C. Remuneração


def remuneration() -> list[Finding]:
    out: list[Finding] = []
    sql = """SELECT count(*) AS n, count(salario) AS validos,
                    count(*) FILTER (WHERE salario = 0) AS zeros,
                    count(*) FILTER (WHERE salario > 50000) AS acima_50mil,
                    min(salario) AS minimo, quantile_cont(salario, 0.25) AS q1, median(salario) AS mediana,
                    quantile_cont(salario, 0.75) AS q3, quantile_cont(salario, 0.99) AS p99,
                    max(salario) AS maximo, avg(salario) AS media
             FROM caged"""
    s = Q.run(sql).iloc[0]
    out.append(Finding(
        "C1", CATEGORIES[2], "Salários zerados", VERIFIED, PENDING,
        f"{_fmt(s['zeros'])} registros ({fmt.pct(s['zeros'] / s['n'], 2)}) com salário = 0.",
        "Contagem de `salário = 0` após conversão para decimal.",
        int(s["zeros"]),
        "Zeros puxam a média para baixo e não representam remuneração real.",
        "Excluir zeros das estatísticas de salário (proposta E5, a confirmar pela equipe).",
        sql=sql, documentado=f"33.912 ({DOC}, Q4)", confere=(int(s["zeros"]) == 33912)))
    out.append(Finding(
        "C2", CATEGORIES[2], "Valores extremos", VERIFIED, PENDING,
        f"{_fmt(s['acima_50mil'])} registros acima de R$ 50 mil; máximo {fmt.brl(s['maximo'])}; "
        f"percentil 99 = {fmt.brl(s['p99'])}.",
        "Contagem acima de R$ 50 mil, máximo e percentil 99.",
        int(s["acima_50mil"]),
        "Poucos valores extremos distorcem a média (média ≫ mediana). Podem ser erros de digitação "
        "ou remunerações reais; não é possível distinguir com esta base.",
        "Usar mediana como medida principal; definir regra para extremos (diagnóstico, E5).",
        sql=sql, documentado=f"535 acima de R$ 50 mil; máximo R$ 3.471.600 ({DOC}, Q4)",
        confere=(int(s["acima_50mil"]) == 535 and float(s["maximo"]) == 3471600.0),
        extras={"hipotese": "Parte dos extremos pode ser erro de digitação (ex.: centavos sem vírgula), não verificado."}))
    out.append(Finding(
        "C3", CATEGORIES[2], "Mediana e quartis", VERIFIED, NO_ACTION,
        f"Mínimo {fmt.brl(s['minimo'])}; Q1 {fmt.brl(s['q1'])}; mediana {fmt.brl(s['mediana'])}; "
        f"Q3 {fmt.brl(s['q3'])}; média {fmt.brl(s['media'])}.",
        "Quantis contínuos (interpolação linear) sobre todos os registros, incluindo zeros.",
        int(s["validos"]),
        "A metade central dos salários fica entre Q1 e Q3; a média está acima da mediana por causa dos extremos.",
        "Reportar mediana e intervalo interquartil.",
        sql=sql, documentado=f"mediana R$ 2.155; média R$ 2.478,58 ({DOC_DIC})",
        confere=(float(s["mediana"]) == 2155.0 and round(float(s["media"]), 2) == 2478.58)))

    sql_un = """SELECT unidade_salario, count(*) AS n, count(*) FILTER (WHERE salario = 0) AS zeros,
                       CAST(median(salario) AS DOUBLE) AS mediana FROM caged GROUP BY 1 ORDER BY n DESC"""
    un = Q.run(sql_un)
    un["descricao"] = un["unidade_salario"].map(lambda c: Q.describe("unidadesaláriocódigo", c))
    var = un[un["unidade_salario"] == "7"]
    out.append(Finding(
        "C4", CATEGORIES[2], "Salário por unidade de pagamento", VERIFIED, PENDING,
        f"Unidade 7 (Variável): {_fmt(var['n'].sum())} registros, {_fmt(var['zeros'].sum())} com salário zero. "
        f"A mediana da unidade 'Hora' é parecida com a de 'Mês'.",
        "Agregação por `unidadesaláriocódigo`.",
        int(var["n"].sum()),
        "Se a unidade 'Hora' trouxesse valor por hora, misturá-la com 'Mês' distorceria tudo.",
        "Hipótese: `salário` já está em base mensal para todas as unidades; confirmar na documentação do MTE.",
        sql=sql_un, documentado=f"22.319, todos com salário 0 ({DOC_DIC})",
        confere=(int(var["n"].sum()) == 22319 and int(var["zeros"].sum()) == 22319), detalhe=un,
        extras={"hipotese": "`salário` é mensal mesmo para unidade Hora (mediana semelhante), não confirmado."}))

    sql_ad = """SELECT movimento, count(*) AS n, CAST(median(salario) AS DOUBLE) AS mediana,
                       CAST(quantile_cont(salario, 0.25) AS DOUBLE) AS q1,
                       CAST(quantile_cont(salario, 0.75) AS DOUBLE) AS q3, CAST(avg(salario) AS DOUBLE) AS media
                FROM caged WHERE unidade_salario = '5' AND salario > 0 GROUP BY 1 ORDER BY 1"""
    ad = Q.run(sql_ad)
    out.append(Finding(
        "C5", CATEGORIES[2], "Salário de admitidos × desligados", EXPLORATORY, NO_ACTION,
        "; ".join(f"{r.movimento}: mediana {fmt.brl(r.mediana)} (n = {_fmt(r.n)})" for r in ad.itertuples()) + ".",
        "Mediana do salário por tipo de movimento, só unidade Mês e salário > 0.",
        int(ad["n"].sum()),
        "A diferença pode refletir composição (ocupações e meses diferentes) e o reajuste anual do "
        "salário mínimo, e não indica, sozinha, 'pagar menos' ou 'pagar mais'.",
        "Comparar dentro do mesmo setor, ocupação e mês.",
        sql=sql_ad, detalhe=ad))

    eq = _n("SELECT count(*) FROM caged WHERE salario = salario_fixo")
    out.append(Finding(
        "C6", CATEGORIES[2], "Salário igual ao salário fixo", VERIFIED, NO_ACTION,
        f"{_fmt(eq)} registros ({fmt.pct(eq / s['n'], 1)}) têm `salário` = `valorsaláriofixo`.",
        "Comparação dos dois valores decimais.",
        eq,
        "Indica que `valorsaláriofixo` traz pouca informação adicional.",
        "Usar `salário` como medida principal.",
        sql="SELECT count(*) FROM caged WHERE salario = salario_fixo",
        documentado=f"3.039.139 (89,5%) ({DOC_DIC})", confere=(eq == 3039139)))
    return out


# ===================================================================== D. Relacionamentos


def relationships() -> list[Finding]:
    out: list[Finding] = []
    mun = load_municipalities()
    sql_join = """SELECT (SELECT count(DISTINCT municipio) FROM caged) AS caged,
                         (SELECT count(*) FROM municipios) AS base,
                         (SELECT count(DISTINCT municipio) FROM caged WHERE municipio IN (SELECT cod6 FROM municipios)) AS caged_com_par,
                         (SELECT count(*) FROM municipios WHERE cod6 NOT IN (SELECT DISTINCT municipio FROM caged)) AS base_sem_movimento,
                         (SELECT count(*) - count(DISTINCT cod6) FROM municipios) AS duplicados,
                         (SELECT count(*) FROM caged WHERE municipio NOT IN (SELECT cod6 FROM municipios)) AS registros_orfaos"""
    j = Q.run(sql_join).iloc[0]
    bad_dv = int((~mun.data["dv_valido"]).sum())
    out.append(Finding(
        "D1", CATEGORIES[3], "Compatibilidade dos códigos municipais", VERIFIED, HANDLED,
        f"CAGED usa 6 dígitos; a base municipal usa o código IBGE de 7 dígitos (com dígito verificador). "
        f"Dígitos verificadores inválidos: {bad_dv} de {len(mun.data)}.",
        "Comprimento dos códigos e cálculo do dígito verificador do IBGE.",
        len(mun.data),
        "Juntar 6 com 7 dígitos diretamente não casa nenhum registro.",
        "Juntar por `município` = 6 primeiros dígitos do código IBGE. Esta aplicação já faz isso.",
        documentado=f"295 códigos com DV válido ({DOC_DIC})", confere=(bad_dv == 0 and len(mun.data) == 295)))
    out.append(Finding(
        "D2", CATEGORIES[3], "Correspondência CAGED × municípios", VERIFIED, NO_ACTION,
        f"{j['caged_com_par']} de {j['caged']} municípios do CAGED têm par na base municipal; "
        f"{j['base_sem_movimento']} município(s) da base sem movimentação; {j['duplicados']} código(s) duplicado(s); "
        f"{_fmt(j['registros_orfaos'])} registro(s) do CAGED sem município correspondente.",
        "Comparação dos conjuntos de códigos (6 dígitos) e checagem de duplicidade no lado municipal.",
        int(j["registros_orfaos"]),
        "Garante que nenhum registro se perde ao calcular taxas por habitante.",
        "Sem ação. Repetir a checagem se as bases forem atualizadas.",
        sql=sql_join, documentado=f"295/295, sem órfãos, N:1 ({DOC}, D.4)",
        confere=(j["caged_com_par"] == 295 and j["base_sem_movimento"] == 0 and j["duplicados"] == 0)))

    cov = Q.dictionary_coverage()
    affected = cov[cov["códigos fora do dicionário"] > 0]
    cbo_row = cov[cov["coluna"] == "cbo2002ocupação"].iloc[0]
    sub_row = cov[cov["coluna"] == "subclasse"].iloc[0]
    out.append(Finding(
        "D3", CATEGORIES[3], "Códigos do CAGED sem descrição no dicionário", VERIFIED, PENDING,
        "; ".join(f"`{r['coluna']}`: {r['códigos fora do dicionário']} código(s), "
                  f"{_fmt(r['registros afetados'])} registro(s)" for _, r in affected.iterrows())
        + ". Demais colunas codificadas: cobertura completa.",
        "Para cada coluna codificada, códigos (normalizados com zeros à esquerda) que não aparecem na aba correspondente.",
        int(cov["registros afetados"].sum()),
        "Esses registros aparecem como '(sem descrição no dicionário)'. Não inventamos significados.",
        "Manter os registros com o rótulo 'sem descrição'; buscar a descrição na CBO/CNAE oficial, se necessário.",
        documentado=f"28 CBOs (2.117 registros) e 1 subclasse (13 registros) ({DOC}, Q7)",
        confere=(cbo_row["códigos fora do dicionário"] == 28 and cbo_row["registros afetados"] == 2117
                 and sub_row["códigos fora do dicionário"] == 1 and sub_row["registros afetados"] == 13),
        detalhe=cov))

    layout = layout_table(load_sheets())
    types = Q.run("SELECT column_name FROM (DESCRIBE caged_raw) WHERE column_name <> 'linha'")
    raw_cols = list(types["column_name"])
    no_dic = [c for c in raw_cols if c not in set(layout["variavel"])]
    no_col = [v for v in layout["variavel"] if v not in set(raw_cols)]
    out.append(Finding(
        "D4", CATEGORIES[3], "Colunas × variáveis do dicionário", VERIFIED, PENDING,
        f"Colunas do Parquet sem variável no dicionário: {', '.join(f'`{c}`' for c in no_dic) or 'nenhuma'}. "
        f"Variáveis do dicionário sem coluna no Parquet: {', '.join(f'`{c}`' for c in no_col) or 'nenhuma'}.",
        "Comparação nominal entre as colunas do Parquet e a aba `Layout`.",
        None,
        "Colunas sem descrição oficial não devem ser interpretadas além do que se observa nelas.",
        "Descartar os índices de exportação; esclarecer as exclusões com a organização (ver A9).",
        confere=(set(no_dic) == {"Unnamed: 0.1", "Unnamed: 0"})))

    guide = ROOT / "context" / "Guia do Participante.md"
    cites = guide.exists() and "municipio_codigo" in guide.read_text(encoding="utf-8")
    exists = "municipio_codigo" in raw_cols or "municipio_codigo" in mun.labels.values()
    out.append(Finding(
        "D5", CATEGORIES[3], "Nome da chave citado no guia", VERIFIED, NO_ACTION,
        f"O guia {'cita' if cites else 'não cita'} `municipio_codigo`; esse nome "
        f"{'existe' if exists else 'não existe'} em nenhuma das bases. A chave real é `município` (CAGED) ↔ `Código [-]` (municípios).",
        "Busca do texto no guia e nos nomes de colunas.",
        None,
        "Evita que alguém procure uma coluna inexistente ou crie uma junção errada.",
        "Usar a chave real documentada em D1.",
        confere=(cites and not exists)))
    return out


def all_findings() -> list[Finding]:
    return integrity() + distribution() + remuneration() + relationships()


def file_info() -> pd.DataFrame:
    """Data de modificação e tamanho de cada arquivo de dados."""
    from dashboard.services.database import DATA_FILES
    rows = []
    for name, path in DATA_FILES.items():
        if path.exists():
            st = path.stat()
            rows.append({"base": name, "arquivo": str(path.relative_to(ROOT)).replace("\\", "/"),
                         "tamanho_mb": st.st_size / 1024 / 1024,
                         "modificado_em": pd.Timestamp(st.st_mtime, unit="s", tz="UTC")
                         .tz_convert("America/Sao_Paulo")})
        else:
            rows.append({"base": name, "arquivo": str(path), "tamanho_mb": None, "modificado_em": None})
    return pd.DataFrame(rows)


def validation_checks() -> pd.DataFrame:
    """Checagens rápidas para a página inicial (não dependem do cálculo das constatações)."""
    k = Q.overview_kpis()
    sheets = load_sheets()
    mun = load_municipalities()
    orphan = _n("SELECT count(*) FROM caged WHERE municipio NOT IN (SELECT cod6 FROM municipios)")
    checks = [
        ("Novo CAGED: arquivo lido", CAGED_PARQUET.exists(), f"{_fmt(k['registros'])} registros"),
        ("Novo CAGED: nº de registros = auditoria (3.397.416)", k["registros"] == 3397416, _fmt(k["registros"])),
        ("Novo CAGED: nº de colunas = auditoria (30)", k["colunas_arquivo"] == 30, str(k["colunas_arquivo"])),
        ("Novo CAGED: todo saldo é +1 ou −1", k["saldo_invalido"] == 0, f"{_fmt(k['saldo_invalido'])} inválidos"),
        ("Novo CAGED: 12 competências de declaração", k["dec_meses"] == 12, f"{k['dec_meses']} meses"),
        ("Municípios: 295 municípios após limpeza", len(mun.data) == 295, f"{len(mun.data)} municípios"),
        ("Municípios: todos os registros do CAGED têm município correspondente", orphan == 0,
         f"{_fmt(orphan)} registros sem par"),
        ("Dicionário: 23 abas", len(sheets) == 23, f"{len(sheets)} abas"),
    ]
    return pd.DataFrame(checks, columns=["checagem", "aprovada", "resultado"])
