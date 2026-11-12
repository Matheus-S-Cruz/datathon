"""Catálogo das colunas do Novo CAGED: nome original, tipo identificado e conversão.

Este módulo é a fonte única de metadados usada por todas as páginas:
- quais colunas são códigos categóricos (e em qual aba do dicionário estão descritos);
- quais são quantitativas (e podem entrar em médias e correlações);
- como cada coluna de texto é convertida para o tipo correto no SQL.

As descrições de "Utilização" resumem `docs/dicionario_analitico.md` (decisões da equipe).
As descrições oficiais dos campos NÃO ficam aqui: são lidas do próprio dicionário (.xlsx).
"""

from __future__ import annotations

from dataclasses import dataclass

# Tipos identificados
CODE = "código categórico"
ORDINAL = "código ordinal"
PERIOD = "período AAAAMM"
MONEY = "valor monetário (decimal com vírgula)"
QUANT = "quantitativo"
SIGN = "sinal +1/−1"
INDEX = "índice técnico"
FLAG = "indicador 0/1"


@dataclass(frozen=True)
class Column:
    name: str              # nome original no Parquet
    typed: str             # nome da coluna convertida na view `caged`
    label: str             # rótulo amigável
    kind: str              # tipo identificado (constantes acima)
    sheet: str | None = None   # aba do dicionário com os códigos
    pad: int | None = None     # largura com zeros à esquerda
    usage: str = ""

    @property
    def quantitative(self) -> bool:
        return self.kind in (MONEY, QUANT)


CAGED_COLUMNS: list[Column] = [
    Column("Unnamed: 0.1", "indice_exportacao_1", "Índice de exportação 1", INDEX,
           usage="Artefato da exportação do CSV (único por linha, não contíguo). Sem uso analítico."),
    Column("Unnamed: 0", "indice_exportacao_2", "Índice de exportação 2", INDEX,
           usage="Artefato da exportação (com repetições). Sem uso analítico."),
    Column("competênciamov", "competencia_mov", "Competência da movimentação", PERIOD,
           usage="Mês em que a movimentação ocorreu; séries temporais."),
    Column("região", "regiao", "Região", CODE, "região",
           usage="Constante (4 = Sul). Sem valor analítico."),
    Column("uf", "uf_cod", "UF", CODE, "uf", usage="Constante (42 = SC). Sem valor analítico."),
    Column("município", "municipio", "Município", CODE, "município", pad=6,
           usage="Recorte territorial e chave de junção com a base de municípios (6 dígitos)."),
    Column("seção", "secao", "Seção CNAE", CODE, "seção",
           usage="Recorte setorial macro; define o escopo 'industrial' (seção C)."),
    Column("subclasse", "subclasse7", "Subclasse CNAE", CODE, "subclasse", pad=7,
           usage="Setor detalhado; os 2 primeiros dígitos formam a divisão CNAE."),
    Column("saldomovimentação", "saldo", "Saldo da movimentação", SIGN,
           usage="+1 = admissão, −1 = desligamento. Somar = saldo; contar = volumes."),
    Column("cbo2002ocupação", "cbo", "Ocupação (CBO 2002)", CODE, "cbo2002ocupação", pad=6,
           usage="Ocupação; base do futuro agrupamento em macrofamílias."),
    Column("categoria", "categoria_cod", "Categoria do trabalhador", CODE, "categoria",
           usage="Separar aprendizes, temporários e intermitentes do emprego típico."),
    Column("graudeinstrução", "escolaridade", "Grau de instrução", ORDINAL, "graudeinstrução",
           usage="Perfil educacional de admitidos × desligados. Código 80 fora da ordem numérica."),
    Column("idade", "idade_anos", "Idade", QUANT,
           usage="Perfil etário. Armazenada como '40.0'; há valores vazios."),
    Column("horascontratuais", "horas", "Horas contratuais semanais", QUANT,
           usage="Jornada; normalização salário/hora (opcional)."),
    Column("raçacor", "racacor", "Raça/cor", CODE, "raçacor", usage="Recorte de diversidade (opcional)."),
    Column("sexo", "sexo_cod", "Sexo", CODE, "sexo", usage="Recorte de gênero (opcional)."),
    Column("tipoempregador", "tipo_empregador", "Tipo de empregador", CODE, "tipoempregador",
           usage="Controle (CNPJ raiz × CPF)."),
    Column("tipoestabelecimento", "tipo_estabelecimento", "Tipo de estabelecimento", CODE,
           "tipoestabelecimento", usage="Controle (CNPJ, CAEPF, CNO)."),
    Column("tipomovimentação", "tipo_mov", "Tipo de movimentação", CODE, "tipomovimentação",
           usage="Motivo da movimentação; distingue desligamento a pedido, demissão e fim de contrato."),
    Column("tipodedeficiência", "deficiencia", "Tipo de deficiência", CODE, "tipodedeficiência",
           usage="Recorte opcional."),
    Column("indtrabintermitente", "intermitente", "Trabalho intermitente", CODE, "indtrabintermitente",
           usage="Filtro de contrato atípico."),
    Column("indtrabparcial", "parcial", "Trabalho parcial", CODE, "indtrabparcial",
           usage="Filtro de contrato atípico."),
    Column("salário", "salario", "Salário mensal declarado", MONEY,
           usage="Renda de admitidos × desligados. Usar mediana; tratar zeros e extremos."),
    Column("tamestabjan", "tam_estab", "Faixa de emprego do estabelecimento (jan.)", ORDINAL,
           "tamestabjan", usage="Porte do estabelecimento; inutilizável em 202608 (todo 99)."),
    Column("indicadoraprendiz", "aprendiz", "Indicador de aprendiz", CODE, "indicadoraprendiz",
           usage="Filtro de contrato atípico."),
    Column("origemdainformação", "origem", "Origem da informação", CODE, "origemdainformação",
           usage="Controle de qualidade (eSocial × EmpregadoWEB)."),
    Column("competênciadec", "competencia_dec", "Competência da declaração", PERIOD,
           usage="Define a janela de 12 meses do desafio."),
    Column("indicadordeforadoprazo", "fora_prazo", "Declarado fora do prazo", FLAG,
           "indicadordeforadoprazo", usage="Identifica movimentações declaradas com atraso."),
    Column("unidadesaláriocódigo", "unidade_salario", "Unidade do salário", CODE,
           "unidadesaláriocódigo", usage="Filtro de qualidade do salário (5 = Mês)."),
    Column("valorsaláriofixo", "salario_fixo", "Salário fixo", MONEY,
           usage="Checagem de consistência com o salário; uso secundário."),
]

BY_NAME = {c.name: c for c in CAGED_COLUMNS}
BY_TYPED = {c.typed: c for c in CAGED_COLUMNS}

# Campos que constam no dicionário mas não na base (verificado na auditoria e
# recalculado na página de auditoria a partir dos arquivos).
DICTIONARY_ONLY_HINT = ("competênciaexc", "indicadordeexclusão")

# Ordem ordinal explícita da escolaridade: 80 (Pós-graduação) fica entre 9 e 10.
EDUCATION_ORDER = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "80", "10", "11", "99"]

ADMISSION_TYPES = ("10", "20", "25", "35", "70", "97")


def q(name: str) -> str:
    """Identificador SQL entre aspas (os nomes têm acentos e espaços)."""
    return '"' + name.replace('"', '""') + '"'


def typed_expr(col: Column) -> str:
    """Expressão SQL que converte a coluna de texto para o tipo identificado.

    Usa TRY_CAST: valor inválido vira NULL. Essas falhas NÃO são silenciosas —
    a página de auditoria conta, coluna a coluna, quantos valores não converteram.
    """
    src = q(col.name)
    if col.kind == MONEY:
        return f"TRY_CAST(replace(trim({src}), ',', '.') AS DECIMAL(18,2))"
    if col.name == "horascontratuais":
        return f"TRY_CAST(replace(trim({src}), ',', '.') AS DECIMAL(8,2))"
    if col.name == "idade":
        return f"TRY_CAST(nullif(trim({src}), '') AS DOUBLE)"
    if col.kind == SIGN:
        return f"TRY_CAST(trim({src}) AS INTEGER)"
    if col.kind == INDEX:
        return f"TRY_CAST({src} AS BIGINT)"
    if col.pad:
        return f"lpad(trim({src}), {col.pad}, '0')"
    return f"trim({src})"


def typed_view_sql(source: str = "caged_raw") -> str:
    """View `caged`: colunas originais + colunas convertidas + campos derivados."""
    typed = ",\n  ".join(f"{typed_expr(c)} AS {c.typed}" for c in CAGED_COLUMNS)
    return f"""
CREATE OR REPLACE VIEW caged AS
SELECT
  r.*,
  {typed},
  substr(lpad(trim("subclasse"), 7, '0'), 1, 2) AS divisao_cnae,
  substr(lpad(trim("cbo2002ocupação"), 6, '0'), 1, 1) AS grande_grupo_cbo,
  CASE TRY_CAST(trim("saldomovimentação") AS INTEGER)
       WHEN 1 THEN 'Admissão' WHEN -1 THEN 'Desligamento' END AS movimento
FROM {source} AS r
"""
