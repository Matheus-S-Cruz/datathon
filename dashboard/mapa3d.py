"""Mapa 3D "sólido" das mesorregiões de SC como componente Streamlit (st.components.v2).

Por que não pydeck? Ao selecionar um objeto, o Streamlit aplica um esmaecimento
translúcido próprio às demais regiões (e recriar o gráfico mata a animação). Aqui o
desenho é um SVG gerado em Python: o "volume" vem de cópias empilhadas do contorno
(laterais) e a região clicada sobe com transição CSS — liso, opaco e animado.

Uso:
    from mapa3d import mapa_sc
    clicada = mapa_sc(regioes, selecionada="Serrana", key="mapa")
    # `regioes`: DataFrame com cod_meso, regiao e colunas de texto para o tooltip.
"""
import json
import math
from pathlib import Path

import streamlit as st

GEO = Path(__file__).resolve().parent.parent / "dataset" / "ibge" / "sc_mesorregioes.geojson"

LARGURA = 1000          # largura do viewBox (unidades SVG)
INCLINACAO = 0.80       # achata o eixo Y -> sensação de mapa visto em ângulo
ESPESSURA = 16          # altura das laterais do bloco
ELEVACAO = 13           # quanto a região selecionada sobe
MARGEM = 20


@st.cache_data
def _geometria():
    """Caminhos SVG (já projetados e suavizados) por mesorregião."""
    from shapely.geometry import shape

    geo = json.loads(GEO.read_text(encoding="utf-8"))
    formas = {int(f["properties"]["codarea"]): shape(f["geometry"]).simplify(0.009)
              for f in geo["features"]}

    minx = min(g.bounds[0] for g in formas.values())
    miny = min(g.bounds[1] for g in formas.values())
    maxx = max(g.bounds[2] for g in formas.values())
    maxy = max(g.bounds[3] for g in formas.values())
    kx = math.cos(math.radians((miny + maxy) / 2))         # correção de longitude
    escala = (LARGURA - 2 * MARGEM) / ((maxx - minx) * kx)

    def xy(lon, lat):
        return (MARGEM + (lon - minx) * kx * escala,
                MARGEM + ELEVACAO + (maxy - lat) * escala * INCLINACAO)

    caminhos = {}
    for cod, g in formas.items():
        partes = [g] if g.geom_type == "Polygon" else list(g.geoms)
        d = []
        for p in partes:
            if p.area < 1e-4:
                continue
            pts = [xy(x, y) for x, y in p.exterior.coords]
            d.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z")
        caminhos[cod] = "".join(d)

    altura = MARGEM * 2 + ELEVACAO + ESPESSURA + (maxy - miny) * escala * INCLINACAO
    return caminhos, round(altura)


CSS = """
.wrap { position: relative; width: 100%; max-width: 760px; margin: 0 auto; user-select: none; }
svg { width: 100%; height: auto; max-height: 62vh; display: block; overflow: visible; }

/* laterais (cópias empilhadas) e tampo */
.lado  { fill: var(--lado, #b9bec6); }
.tampo { fill: var(--tampo, #f3f4f6); stroke: #a3a9b3; stroke-width: 0.9;
         vector-effect: non-scaling-stroke; stroke-linejoin: round;
         cursor: pointer; transition: fill .3s ease; }
.base .tampo:hover { fill: #e6f4ec; }

/* com uma região selecionada, as outras ficam num cinza sólido */
.tem-sel .base .tampo { fill: #dfe2e7; }
.tem-sel .base .lado  { fill: #aeb3bb; }

/* cópia "elevável" de cada região: invisível até ser selecionada.
   Cada camada da lateral anima de --y0 (empilhada na espessura do bloco) para --y1
   (espalhada do tampo elevado até o fundo do bloco) -> a parede "cresce" junto com a
   subida e fica sempre contínua com a base, sem vão. */
.elev { opacity: 0; pointer-events: none;
        transition: opacity 0s linear .35s; }           /* some só ao terminar de descer */
.elev.ativa { opacity: 1; pointer-events: auto; transition: opacity 0s; }
.elev .lado, .elev .tampo {
        transform: translateY(var(--y0));
        transition: transform .35s cubic-bezier(.3,.7,.3,1), fill .25s ease; }
.elev.ativa .lado, .elev.ativa .tampo { transform: translateY(var(--y1)); }

/* sombra: forma fixa já desfocada sob a região; só a opacidade anima (barato),
   então ela acompanha a subida em vez de aparecer depois */
.elev .sombra { fill: rgba(0,0,0,.30); pointer-events: none;
                transform: translate(5px, 9px); opacity: 0;
                transition: opacity .3s ease; }
.elev.ativa .sombra { opacity: 1; }

/* cor: a região que desce volta ao cinza da base JÁ durante a descida (sem ficar
   "verde parada" no chão); a que sobe vai do cinza ao verde enquanto sobe */
.elev .tampo { fill: #dfe2e7; stroke: #a3a9b3; }
.elev .lado  { fill: #aeb3bb; }
svg:not(.tem-sel) .elev .tampo { fill: #f3f4f6; }
svg:not(.tem-sel) .elev .lado  { fill: #b9bec6; }
.elev.ativa .tampo { fill: #2f9e64; stroke: #1f7a4a; }
.elev.ativa .lado  { fill: #1f7a4a; }

.dica { position: absolute; pointer-events: none; display: none; z-index: 5;
        background: #1f2937; color: #fff; font: 13px/1.35 sans-serif;
        padding: 6px 9px; border-radius: 6px; white-space: nowrap;
        box-shadow: 0 4px 12px rgba(0,0,0,.25); }
"""

JS = """
export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  if (!data) return;
  const NS = 'http://www.w3.org/2000/svg';

  // Monta o SVG uma única vez; nas próximas execuções só atualiza a seleção,
  // assim a transição CSS (subir/descer) acontece de verdade.
  let wrap = parentElement.querySelector('.wrap');
  if (!wrap || wrap.dataset.assinatura !== data.assinatura) {
    if (wrap) wrap.remove();
    wrap = document.createElement('div');
    wrap.className = 'wrap';
    wrap.dataset.assinatura = data.assinatura;
    parentElement.appendChild(wrap);

    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', `0 0 ${data.largura} ${data.altura}`);
    wrap.appendChild(svg);
    const dica = document.createElement('div');
    dica.className = 'dica';
    wrap.appendChild(dica);

    const camadaLados = document.createElementNS(NS, 'g');
    const camadaTampos = document.createElementNS(NS, 'g');
    const camadaElev = document.createElementNS(NS, 'g');
    camadaLados.setAttribute('class', 'base');
    camadaTampos.setAttribute('class', 'base');
    const defs = document.createElementNS(NS, 'defs');
    defs.innerHTML = '<filter id="desfoque" x="-10%" y="-10%" width="120%" height="120%">' +
                     '<feGaussianBlur stdDeviation="6"/></filter>';
    svg.append(defs, camadaLados, camadaTampos, camadaElev);

    const caminho = (d, cls, dy) => {
      const p = document.createElementNS(NS, 'path');
      p.setAttribute('d', d);
      p.setAttribute('class', cls);
      if (dy) p.setAttribute('transform', `translate(0 ${dy})`);
      return p;
    };

    for (const r of data.regioes) {
      // laterais: todas antes de todos os tampos (uma não "invade" o tampo da vizinha)
      const PASSO = 1.5;  // espaçamento entre camadas da lateral (< 1px na tela; menos caminhos = mais leve)
      for (let k = data.espessura; k > 0; k -= PASSO) camadaLados.appendChild(caminho(r.d, 'lado', k));
      const tampo = caminho(r.d, 'tampo');
      tampo.dataset.regiao = r.nome;
      camadaTampos.appendChild(tampo);

      // cópia que sobe quando a região é selecionada
      const g = document.createElementNS(NS, 'g');
      g.setAttribute('class', 'elev');
      g.dataset.regiao = r.nome;
      const E = data.espessura, L = data.elevacao, N = Math.ceil((E + L) / PASSO);
      const sombra = caminho(r.d, 'sombra');
      sombra.setAttribute('filter', 'url(#desfoque)');
      g.appendChild(sombra);
      for (let i = N; i >= 1; i--) {
        const lado = caminho(r.d, 'lado');
        lado.style.setProperty('--y0', `${(i * E) / N}px`);
        lado.style.setProperty('--y1', `${-L + (i * (E + L)) / N}px`);
        g.appendChild(lado);
      }
      const t2 = caminho(r.d, 'tampo');
      t2.style.setProperty('--y0', '0px');
      t2.style.setProperty('--y1', `${-L}px`);
      t2.dataset.regiao = r.nome;
      g.appendChild(t2);
      camadaElev.appendChild(g);
    }

    const info = Object.fromEntries(data.regioes.map(r => [r.nome, r.dica]));
    svg.addEventListener('click', (e) => {
      const alvo = e.target.closest('[data-regiao]');
      if (!alvo) return;
      const nome = alvo.dataset.regiao;
      const atual = wrap.dataset.sel || '';
      const nova = nome === atual ? '' : nome;     // clicar de novo na mesma = desselecionar
      aplicarSelecao(nova);                          // resposta imediata no navegador
      // Só avisa o Python DEPOIS da animação: a reexecução do Streamlit ocupa a thread
      // principal e "congelaria" a transição do SVG no meio (o atraso na troca).
      clearTimeout(wrap._aviso);
      wrap._aviso = setTimeout(() => setTriggerValue('selecionada', nova || '__nenhuma__'), 380);
    });
    svg.addEventListener('mousemove', (e) => {
      const alvo = e.target.closest('[data-regiao]');
      if (!alvo) { dica.style.display = 'none'; return; }
      const box = wrap.getBoundingClientRect();
      dica.innerHTML = info[alvo.dataset.regiao];
      dica.style.display = 'block';
      dica.style.left = `${e.clientX - box.left + 14}px`;
      dica.style.top = `${e.clientY - box.top + 14}px`;
    });
    svg.addEventListener('mouseleave', () => { dica.style.display = 'none'; });
  }

  function aplicarSelecao(nome) {
    wrap.dataset.sel = nome || '';
    wrap.querySelector('svg').classList.toggle('tem-sel', !!nome);
    wrap.querySelectorAll('.elev').forEach(g => {
      const ativa = g.dataset.regiao === nome;
      // SVG <g> recebe a classe via setAttribute (classList funciona nos navegadores modernos)
      g.classList.toggle('ativa', ativa);
    });
  }

  // Só obedece ao Python quando o valor dele MUDA. Enquanto o Python processa um clique,
  // o componente é reexecutado com o valor antigo; reaplicá-lo "re-selecionaria" a região
  // anterior por um instante (a pausa na troca de região).
  const doPython = data.selecionada || '';
  if (wrap.dataset.ultimoPython !== doPython) {
    wrap.dataset.ultimoPython = doPython;
    aplicarSelecao(doPython);
  }
}
"""

_componente = st.components.v2.component("mapa_sc_3d", css=CSS, js=JS)


def mapa_sc(regioes, selecionada=None, key="mapa_sc", on_click=None):
    """Desenha o mapa. O navegador decide a seleção (clicar de novo desseleciona) e envia
    o estado final; devolve-o nesta execução (nome, None = nenhuma) ou None se não houve clique.

    regioes: DataFrame com `cod_meso`, `regiao` e `dica_html` (texto do tooltip).
    on_click: callback opcional chamado quando uma região é clicada.
    """
    caminhos, altura = _geometria()
    itens = [
        {"nome": r.regiao, "d": caminhos[int(r.cod_meso)], "dica": r.dica_html}
        for r in regioes.itertuples()
        if int(r.cod_meso) in caminhos
    ]
    dados = {
        "regioes": itens,
        "selecionada": selecionada,
        "largura": LARGURA,
        "altura": altura,
        "espessura": ESPESSURA,
        "elevacao": ELEVACAO,
        # muda só se a geometria/dicas mudarem -> o SVG não é recriado a cada clique
        "assinatura": str(hash(tuple((i["nome"], i["dica"]) for i in itens))),
    }
    resultado = _componente(
        key=key,
        data=dados,
        on_selecionada_change=on_click or (lambda: None),
    )
    return valor_selecionado(getattr(resultado, "selecionada", None))


def valor_selecionado(v):
    """Converte o valor enviado pelo navegador: nome da região, ou None (nenhuma)."""
    if v is None:
        return None
    return None if v == "__nenhuma__" else v
