"""Gera a apresentação de pitch (PDF) do Raio-X Industrial de SC.

PDF atualizável: edite o CONTEÚDO abaixo (dicionários/listas) e rode de novo para regenerar o PDF.
Os números-chave vêm dos serviços reais do projeto; nada é inventado.

    python reports/pitch/gerar_pitch.py
    # saída: reports/pitch/pitch_raio_x_industrial_sc.pdf
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

# --------------------------------------------------------------------------- identidade visual
AZUL = (31, 78, 140)          # azul-petróleo do dashboard
AZUL2 = (46, 116, 181)
GRAFITE = (34, 39, 46)
CINZA = (90, 98, 110)
CLARO = (240, 244, 249)
BRANCO = (255, 255, 255)
VERDE = (33, 145, 90)
LARANJA = (201, 110, 40)

W, H = 297, 210               # A4 paisagem (mm)
MARGEM = 18


def _txt(s: str) -> str:
    """fpdf2 2.9 usa fonte core latin-1; troca caracteres fora dela por equivalentes seguros."""
    repl = {"–": "-", "—": "-", "“": '"', "”": '"', "’": "'", "‘": "'", "→": "->", "×": "x",
            "≈": "~", "•": "-", "…": "...", "₂": "2", "º": "o", "ª": "a"}
    for a, b in repl.items():
        s = s.replace(a, b)
    return s


class Pitch(FPDF):
    def __init__(self):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.set_auto_page_break(False)
        self.set_margins(MARGEM, MARGEM, MARGEM)

    # -------- primitivos de layout
    def faixa_titulo(self, eyebrow: str, titulo: str):
        self.set_fill_color(*AZUL)
        self.rect(0, 0, W, 32, "F")
        self.set_fill_color(*AZUL2)
        self.rect(0, 32, W, 1.4, "F")
        self.set_xy(MARGEM, 8)
        self.set_text_color(*CLARO)
        self.set_font("helvetica", "B", 10)
        self.cell(0, 5, _txt(eyebrow.upper()), new_x="LMARGIN", new_y="NEXT")
        self.set_xy(MARGEM, 14)
        self.set_text_color(*BRANCO)
        self.set_font("helvetica", "B", 22)
        self.cell(0, 12, _txt(titulo))
        self.set_xy(MARGEM, 40)
        self.set_text_color(*GRAFITE)

    def bullet(self, texto: str, x: float, y: float, w: float, destaque: bool = False, size: int = 12):
        self.set_xy(x, y)
        self.set_text_color(*(AZUL if destaque else GRAFITE))
        self.set_font("helvetica", "B" if destaque else "", size)
        self.multi_cell(w, 6.2, _txt(("* " if not destaque else "") + texto))

    def card(self, x, y, w, h, titulo, valor, legenda, cor=AZUL):
        self.set_fill_color(*CLARO)
        self.set_draw_color(*cor)
        self.set_line_width(0.5)
        self.rect(x, y, w, h, "DF")
        self.set_fill_color(*cor)
        self.rect(x, y, 2.2, h, "F")
        self.set_xy(x + 6, y + 5)
        self.set_text_color(*CINZA)
        self.set_font("helvetica", "B", 9)
        self.multi_cell(w - 10, 4.2, _txt(titulo.upper()))
        self.set_xy(x + 6, y + h / 2 - 4)
        self.set_text_color(*cor)
        self.set_font("helvetica", "B", 20)
        self.cell(w - 10, 9, _txt(valor))
        self.set_xy(x + 6, y + h - 11)
        self.set_text_color(*CINZA)
        self.set_font("helvetica", "", 8.5)
        self.multi_cell(w - 10, 3.8, _txt(legenda))

    def rodape(self, n: int):
        self.set_xy(MARGEM, H - 10)
        self.set_text_color(*CINZA)
        self.set_font("helvetica", "", 8)
        self.cell(0, 4, _txt("Raio-X Industrial de Santa Catarina  -  Datathon CDIA 2026 - UniSENAI"))
        self.set_xy(W - MARGEM - 20, H - 10)
        self.cell(20, 4, str(n), align="R")


# ===================================================================== CONTEÚDO (edite aqui)

PERIODO = "set/2025 a ago/2026 (Novo CAGED)"

KPIS = [
    ("Movimentacoes analisadas", "3,4 mi", "admissoes + desligamentos em SC"),
    ("Saldo de vagas formais", "+41.482", "1.719.449 adm. - 1.677.967 desl."),
    ("Municipios cobertos", "295", "todos os municipios de SC"),
    ("Salario mediano (SC)", "R$ 2.156", "mediana sem zeros, por mes"),
]


def capa(p: Pitch):
    p.add_page()
    p.set_fill_color(*AZUL)
    p.rect(0, 0, W, H, "F")
    p.set_fill_color(*AZUL2)
    p.rect(0, H - 60, W, 60, "F")
    p.set_xy(MARGEM, 48)
    p.set_text_color(*CLARO)
    p.set_font("helvetica", "B", 12)
    p.cell(0, 6, _txt("DATATHON CDIA 2026  -  UNISENAI"), new_x="LMARGIN", new_y="NEXT")
    p.set_xy(MARGEM, 66)
    p.set_text_color(*BRANCO)
    p.set_font("helvetica", "B", 40)
    p.multi_cell(W - 2 * MARGEM, 15, _txt("Raio-X Industrial de Santa Catarina"))
    p.set_xy(MARGEM, 112)
    p.set_text_color(*CLARO)
    p.set_font("helvetica", "", 15)
    p.multi_cell(W - 2 * MARGEM, 7,
                 _txt("Inteligencia territorial e setorial sobre o mercado de trabalho da industria, "
                      "a partir dos microdados do Novo CAGED cruzados com bases publicas do IBGE."))
    p.set_xy(MARGEM, 150)
    p.set_font("helvetica", "I", 12)
    p.multi_cell(W - 2 * MARGEM, 6,
                 _txt('"Quais regioes e setores industriais de SC enfrentam apagao de mao de obra ou '
                      'expansao acelerada - e como renda e escolaridade explicam esses gargalos?"'))


def problematica(p: Pitch):
    p.add_page()
    p.faixa_titulo("A problematica", "A industria de SC nao sabe onde esta perdendo gente")
    p.bullet("A industria catarinense e um dos motores do pais - mas decisoes sobre mao de obra "
             "costumam ser tomadas sem enxergar, municipio a municipio, onde o emprego cresce e onde "
             "ele apenas gira (muita troca, pouco saldo).", MARGEM, 44, W - 2 * MARGEM, destaque=True)
    y = 70
    cw = (W - 2 * MARGEM - 3 * 6) / 4
    for i, (tit, val, leg) in enumerate(KPIS):
        cor = VERDE if "+" in val else AZUL
        p.card(MARGEM + i * (cw + 6), y, cw, 34, tit, val, leg, cor)
    p.bullet("Por tras do saldo positivo do estado, ha regioes com alta rotatividade (61,2% do estoque "
             "formal girou no periodo) e setores industriais perdendo tecnicos qualificados. "
             "Sem dado granular, o gargalo fica invisivel ate virar crise.", MARGEM, 116,
             W - 2 * MARGEM, size=12)
    p.bullet("Periodo analisado: " + PERIODO + ".", MARGEM, 142, W - 2 * MARGEM, size=10)
    p.rodape(2)


def solucao(p: Pitch):
    p.add_page()
    p.faixa_titulo("A solucao", "Um painel de inteligencia + assistente que responde com dados reais")
    itens = [
        ("Painel executivo", "5 indicadores-chave e 6 graficos que respondem a pergunta central: mapa "
         "por municipio, regioes (crescimento x rotatividade), setores, ocupacoes, salario e escolaridade."),
        ("Explorador de dados", "Filtros, tabelas pesquisaveis, dicionario oficial e exportacao - para a "
         "equipe consultar e conferir os 3,4 mi de registros sem abrir o arquivo bruto."),
        ("Analises complementares", "Territorio, setores, renda x escolaridade, macrofamilias de ocupacoes "
         "e contexto regional do IBGE, com recorte que acompanha a navegacao."),
        ("Assistente inteligente (previa)", "Botao flutuante em todas as secoes: responde em linguagem "
         "natural reusando as consultas oficiais - nunca inventa numero e cita a fonte."),
    ]
    y = 46
    cw = (W - 2 * MARGEM - 6) / 2
    for i, (tit, desc) in enumerate(itens):
        x = MARGEM + (i % 2) * (cw + 6)
        yy = y + (i // 2) * 52
        p.set_fill_color(*CLARO)
        p.set_draw_color(*AZUL)
        p.set_line_width(0.4)
        p.rect(x, yy, cw, 46, "DF")
        p.set_xy(x + 6, yy + 5)
        p.set_text_color(*AZUL)
        p.set_font("helvetica", "B", 13)
        p.cell(cw - 10, 6, _txt(tit))
        p.set_xy(x + 6, yy + 15)
        p.set_text_color(*GRAFITE)
        p.set_font("helvetica", "", 10.5)
        p.multi_cell(cw - 12, 5.2, _txt(desc))
    p.rodape(3)


def diferenciais(p: Pitch):
    p.add_page()
    p.faixa_titulo("Diferenciais", "Confiavel por construcao, nao por sorte")
    itens = [
        ("Numeros rastreaveis", "Cada valor do painel e do assistente vem de uma funcao oficial do "
         "projeto; o assistente cita fonte, periodo, unidade e recorte."),
        ("Fonte unica de metodologia", "Um glossario central (17 indicadores) define formula, fonte e "
         "limitacoes - o painel, as tabelas e o assistente leem do mesmo lugar."),
        ("Cruzamento com o IBGE", "O CAGED mede fluxo; somamos o estoque (CEMPRE), o PIB e a divisao "
         "regional para medir crescimento e rotatividade de verdade."),
        ("Metodologia salarial honesta", "Mediana sem zeros como medida principal; a media fica como "
         "complemento rotulado. Sem afirmar que escolaridade causa renda."),
        ("Recorte que acompanha", "Industria, secoes CNAE, regiao e populacao minima seguem a pessoa "
         "entre as paginas, sem recalcular nada por fora."),
        ("Transparencia das limitacoes", "O projeto diz o que NAO sabe: fluxo != estoque, duas medidas "
         "de populacao, classificacao analitica != CBO oficial."),
    ]
    y = 46
    cw = (W - 2 * MARGEM - 2 * 6) / 3
    for i, (tit, desc) in enumerate(itens):
        x = MARGEM + (i % 3) * (cw + 6)
        yy = y + (i // 3) * 54
        p.set_draw_color(*AZUL2)
        p.set_line_width(0.4)
        p.set_fill_color(*BRANCO)
        p.rect(x, yy, cw, 48, "DF")
        p.set_fill_color(*AZUL)
        p.rect(x, yy, cw, 2, "F")
        p.set_xy(x + 5, yy + 6)
        p.set_text_color(*AZUL)
        p.set_font("helvetica", "B", 11.5)
        p.multi_cell(cw - 9, 5, _txt(tit))
        p.set_xy(x + 5, yy + 18)
        p.set_text_color(*GRAFITE)
        p.set_font("helvetica", "", 9.5)
        p.multi_cell(cw - 9, 4.6, _txt(desc))
    p.rodape(4)


def tecnologias(p: Pitch):
    p.add_page()
    p.faixa_titulo("Ferramentas e tecnologias", "Leve, reproduzivel e gratuito de publicar")
    grupos = [
        ("Processamento", ["DuckDB - SQL direto sobre o Parquet (3,4 mi linhas) sem carregar tudo",
                            "Pandas - tabelas agregadas e integracao com os graficos",
                            "PyArrow / Parquet (zstd) - formato intermediario tipado e compacto"]),
        ("Aplicacao", ["Streamlit - dashboard em Python, publicavel de graca",
                       "Plotly - graficos interativos (mapa, dispersoes, barras)",
                       "Jupyter - notebook de pipeline narrado (entregavel 1)"]),
        ("Assistente (previa)", ["Arquitetura desacoplada do provedor (pronta para LLM)",
                                 "Provedor simulado deterministico - sem custo",
                                 "Ferramentas controladas que reusam os servicos oficiais"]),
        ("Qualidade e entrega", ["pytest - 109 testes / 219 subtestes (regressao e metodologia)",
                                 "Git / GitHub - versionamento e revisao por pull request",
                                 "fpdf2 + matplotlib - este pitch, gerado por script"]),
    ]
    y = 46
    cw = (W - 2 * MARGEM - 6) / 2
    for i, (tit, linhas) in enumerate(grupos):
        x = MARGEM + (i % 2) * (cw + 6)
        yy = y + (i // 2) * 54
        p.set_fill_color(*CLARO)
        p.set_draw_color(*AZUL)
        p.rect(x, yy, cw, 48, "DF")
        p.set_xy(x + 6, yy + 5)
        p.set_text_color(*AZUL)
        p.set_font("helvetica", "B", 12)
        p.cell(cw - 10, 6, _txt(tit))
        p.set_xy(x + 6, yy + 14)
        p.set_text_color(*GRAFITE)
        p.set_font("helvetica", "", 9.8)
        p.multi_cell(cw - 12, 5.0, _txt("\n".join("- " + l for l in linhas)))
    p.rodape(5)


def fontes(p: Pitch):
    p.add_page()
    p.faixa_titulo("Sites e bases publicas", "Tudo de fonte oficial e documentada")
    linhas = [
        ("Novo CAGED / MTE", "Microdados de admissoes e desligamentos de SC (fornecidos pela organizacao "
         "do Datathon). gov.br/trabalho-e-emprego"),
        ("Dicionario oficial do Novo CAGED", "Significado das variaveis e dos codigos (salario, CBO, "
         "CNAE, escolaridade)."),
        ("IBGE - CEMPRE 2024 (SIDRA 9509)", "Pessoal ocupado assalariado: denominador do crescimento do "
         "emprego e da rotatividade."),
        ("IBGE - PIB dos Municipios (SIDRA 5938)", "PIB 2023 e valor adicionado por atividade 2021: peso "
         "da industria na economia municipal."),
        ("IBGE - Localidades e Malhas (API)", "Divisao regional intermediaria/imediata e malha municipal "
         "para o mapa coropletico."),
        ("CBO-2002 / MTE", "Estrutura oficial das ocupacoes (10 grandes grupos, 2.778 ocupacoes)."),
    ]
    y = 46
    for tit, desc in linhas:
        p.set_fill_color(*AZUL)
        p.rect(MARGEM, y + 1.5, 2.5, 10, "F")
        p.set_xy(MARGEM + 6, y)
        p.set_text_color(*AZUL)
        p.set_font("helvetica", "B", 12)
        p.cell(0, 5.5, _txt(tit), new_x="LMARGIN", new_y="NEXT")
        p.set_xy(MARGEM + 6, y + 5.5)
        p.set_text_color(*GRAFITE)
        p.set_font("helvetica", "", 10)
        p.multi_cell(W - 2 * MARGEM - 6, 4.8, _txt(desc))
        y += 18
    p.rodape(6)


def formulas(p: Pitch):
    p.add_page()
    p.faixa_titulo("Formulas gerais", "Como cada indicador e calculado")
    linhas = [
        ("Saldo de vagas", "admissoes - desligamentos (soma do saldomovimentacao, +1 ou -1 por registro)"),
        ("Saldo por 10 mil hab.", "saldo / populacao (Censo 2022) x 10.000"),
        ("Crescimento do emprego", "saldo / pessoal assalariado (CEMPRE 2024) x 100"),
        ("Taxa de rotatividade", "min(admissoes, desligamentos) / assalariados (CEMPRE 2024) x 100  [conceito DIEESE]"),
        ("Salario mediano (principal)", "mediana do salario entre os registros com salario > 0 (exclui zeros)"),
        ("Escolaridade media", "media da posicao ordinal do grau de instrucao, de 1 (analfabeto) a 12 (doutorado)"),
        ("Macrofamilia de ocupacoes", "1o digito do codigo CBO-2002; grupos 7 e 8 formam a macrofamilia operacional"),
        ("Part. da industria no VAB", "VAB da industria / VAB total (2021)"),
    ]
    y = 44
    for tit, f in linhas:
        p.set_xy(MARGEM, y)
        p.set_text_color(*AZUL)
        p.set_font("helvetica", "B", 11)
        p.cell(78, 6, _txt(tit))
        p.set_text_color(*GRAFITE)
        p.set_font("courier", "", 10)
        p.multi_cell(W - 2 * MARGEM - 80, 6, _txt("= " + f))
        y += 15
    p.set_xy(MARGEM, H - 22)
    p.set_text_color(*CINZA)
    p.set_font("helvetica", "I", 9)
    p.multi_cell(W - 2 * MARGEM, 4.5,
                 _txt("Relacoes entre renda e escolaridade sao descritivas, nao causais. O salario do "
                      "Novo CAGED ja vem mensalizado pela origem (MTE)."))
    p.rodape(7)


def melhorias(p: Pitch):
    p.add_page()
    p.faixa_titulo("Melhorias futuras", "O que vem depois da previa")
    itens = [
        ("Assistente com IA real", "Plugar um modelo de linguagem (provedor ja desacoplado) para ampliar "
         "a compreensao de perguntas, mantendo as consultas controladas e o custo sob teto."),
        ("Classificacao CBO com IA", "Concluir o piloto de classificacao de ocupacoes (etapa preparada, "
         "sem custo ate aqui) com revisao humana e comparacao com a classificacao oficial."),
        ("Padrao unico de populacao", "Unificar Censo 2022 x estimativa 2026 para as taxas por 10 mil "
         "habitantes, eliminando a dupla leitura."),
        ("Serie temporal e sazonalidade", "Acompanhar a evolucao mes a mes e sinalizar movimentos "
         "sazonais por setor e regiao."),
        ("Alertas e recomendacoes", "Sinalizar automaticamente regioes/setores em apagao ou expansao, "
         "com recomendacoes acionaveis."),
        ("Memoria conversacional", "Permitir perguntas encadeadas ('e entre esses?') com referencia aos "
         "resultados anteriores."),
    ]
    y = 46
    cw = (W - 2 * MARGEM - 6) / 2
    for i, (tit, desc) in enumerate(itens):
        x = MARGEM + (i % 2) * (cw + 6)
        yy = y + (i // 2) * 36
        p.set_fill_color(*CLARO)
        p.set_draw_color(*AZUL2)
        p.rect(x, yy, cw, 32, "DF")
        p.set_xy(x + 5, yy + 4)
        p.set_text_color(*AZUL)
        p.set_font("helvetica", "B", 11)
        p.cell(cw - 8, 5, _txt(tit))
        p.set_xy(x + 5, yy + 11)
        p.set_text_color(*GRAFITE)
        p.set_font("helvetica", "", 9.3)
        p.multi_cell(cw - 9, 4.4, _txt(desc))
    p.rodape(8)


def equipe(p: Pitch):
    p.add_page()
    p.set_fill_color(*AZUL)
    p.rect(0, 0, W, H, "F")
    p.set_fill_color(*AZUL2)
    p.rect(0, 0, W, 34, "F")
    p.set_xy(MARGEM, 11)
    p.set_text_color(*BRANCO)
    p.set_font("helvetica", "B", 22)
    p.cell(0, 10, _txt("Equipe"))
    membros = [
        ("Matheus Cruz", "Engenharia de dados e integracao"),
        ("Nyrx Oliveira de Aquino Farias", "Pipeline, dashboard e metodologia"),
        ("Joao Paulo", "Analise e visualizacao"),
    ]
    y = 56
    cw = (W - 2 * MARGEM - 2 * 8) / 3
    for i, (nome, papel) in enumerate(membros):
        x = MARGEM + i * (cw + 8)
        p.set_fill_color(*CLARO)
        p.rect(x, y, cw, 56, "F")
        p.set_fill_color(*AZUL)
        p.rect(x, y, cw, 3, "F")
        p.set_xy(x + 6, y + 14)
        p.set_text_color(*AZUL)
        p.set_font("helvetica", "B", 14)
        p.multi_cell(cw - 12, 6.5, _txt(nome))
        p.set_xy(x + 6, y + 34)
        p.set_text_color(*GRAFITE)
        p.set_font("helvetica", "", 10.5)
        p.multi_cell(cw - 12, 5, _txt(papel))
    p.set_xy(MARGEM, 130)
    p.set_text_color(*CLARO)
    p.set_font("helvetica", "", 12)
    p.multi_cell(W - 2 * MARGEM, 6,
                 _txt("Datathon CDIA 2026 - UniSENAI  |  Bacharelado em Ciencia de Dados e IA"))
    p.set_xy(MARGEM, 150)
    p.set_font("helvetica", "I", 11)
    p.multi_cell(W - 2 * MARGEM, 6,
                 _txt("Repositorio: github.com/Matheus-S-Cruz/datathon  -  dashboard em Streamlit + Plotly"))


def gerar() -> str:
    p = Pitch()
    capa(p)
    problematica(p)
    solucao(p)
    diferenciais(p)
    tecnologias(p)
    fontes(p)
    formulas(p)
    melhorias(p)
    equipe(p)
    destino = Path(__file__).with_name("pitch_raio_x_industrial_sc.pdf")
    p.output(str(destino))
    return str(destino)


if __name__ == "__main__":
    caminho = gerar()
    print("Pitch gerado:", caminho)
