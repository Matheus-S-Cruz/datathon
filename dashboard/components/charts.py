"""Gráficos Plotly com identidade visual única.

Decisões de cor (paleta validada para daltonismo, ver README):
- admissões = azul, desligamentos = laranja: são IDENTIDADES, não "bom/ruim";
- saldo usa as mesmas duas cores pelo sinal (positivo = lado das admissões);
- magnitudes usam uma única matiz (azul claro → escuro);
- nunca dois eixos Y no mesmo gráfico.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard import formatting as fmt

# Paleta validada (scripts/validate_palette.js da skill de visualização):
# par categórico e rampas ordinais aprovados nos temas claro e escuro.
LIGHT = dict(blue="#2a78d6", orange="#eb6834",
             ordinal=["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281", "#08213f"])
DARK = dict(blue="#3987e5", orange="#d95926",
            ordinal=["#184f95", "#256abf", "#3987e5", "#6da7ec", "#a9ccf5", "#e3efff"])
GRAY = "#898781"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGING = [[0.0, "#c24d1c"], [0.25, "#f2a07c"], [0.5, "#d9d8d2"], [0.75, "#86b6ef"], [1.0, "#1c5cab"]]

# Faixas ordinais de escolaridade para gráficos empilhados (agregam os códigos do
# dicionário; a tabela ao lado mantém os 12 níveis originais).
EDUCATION_BANDS = [
    ("Até fundamental incompleto", ["1", "2", "3", "4"]),
    ("Fundamental completo / médio incompleto", ["5", "6"]),
    ("Médio completo", ["7"]),
    ("Superior incompleto", ["8"]),
    ("Superior completo", ["9"]),
    ("Pós-graduação, mestrado ou doutorado", ["80", "10", "11"]),
]


def palette() -> dict:
    try:
        return DARK if st.context.theme.type == "dark" else LIGHT
    except Exception:  # noqa: BLE001 — fora do Streamlit ou tema desconhecido
        return LIGHT


def _layout(fig: go.Figure, title: str, x_title: str | None = None, y_title: str | None = None,
            height: int = 380, legend: bool = True) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=15)),
        separators=",.", height=height, margin=dict(l=8, r=8, t=56, b=8),
        colorway=SERIES, bargap=0.25, hovermode="closest",
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1, title=None),
    )
    fig.update_xaxes(title=x_title, showgrid=False, zeroline=False)
    fig.update_yaxes(title=y_title, gridcolor="rgba(137,135,129,0.25)", zeroline=True,
                     zerolinecolor="rgba(137,135,129,0.6)")
    return fig


def show(fig: go.Figure, key: str | None = None) -> None:
    st.plotly_chart(fig, width="stretch", key=key, config={"displaylogo": False, "locale": "pt-BR"})


def flow_bars(df: pd.DataFrame, label_col: str, title: str, x_title: str = "") -> go.Figure:
    """Admissões e desligamentos lado a lado (mesma escala, um eixo)."""
    pal = palette()
    fig = go.Figure()
    for col, name, color in [("admissoes", "Admissões", pal["blue"]), ("desligamentos", "Desligamentos", pal["orange"])]:
        fig.add_bar(x=df[label_col], y=df[col], name=name, marker_color=color,
                    customdata=[fmt.integer(v) for v in df[col]],
                    hovertemplate="%{x}<br>" + name + ": %{customdata}<extra></extra>")
    fig.update_layout(barmode="group")
    fig.update_yaxes(tickformat=",d")
    return _layout(fig, title, x_title, "Movimentações")


def balance_bars(df: pd.DataFrame, label_col: str, title: str, x_title: str = "",
                 horizontal: bool = False) -> go.Figure:
    pal = palette()
    colors = [pal["blue"] if v >= 0 else pal["orange"] for v in df["saldo"]]
    text = [fmt.signed(v) for v in df["saldo"]]
    if horizontal:
        fig = go.Figure(go.Bar(y=df[label_col], x=df["saldo"], orientation="h", marker_color=colors,
                               customdata=text, hovertemplate="%{y}<br>Saldo: %{customdata}<extra></extra>"))
        fig.update_yaxes(autorange="reversed", automargin=True)
        fig.update_xaxes(tickformat=",d")
        return _layout(fig, title, "Saldo (admissões − desligamentos)", None, height=max(380, 22 * len(df)),
                       legend=False)
    fig = go.Figure(go.Bar(x=df[label_col], y=df["saldo"], marker_color=colors, customdata=text,
                           hovertemplate="%{x}<br>Saldo: %{customdata}<extra></extra>"))
    fig.update_yaxes(tickformat=",d")
    return _layout(fig, title, x_title, "Saldo (admissões − desligamentos)", legend=False)


def ranked_bars(df: pd.DataFrame, label_col: str, value_col: str, title: str, value_title: str,
                color: str | None = None, money: bool = False) -> go.Figure:
    color = color or palette()["blue"]
    text = [fmt.brl(v) if money else fmt.integer(v) for v in df[value_col]]
    fig = go.Figure(go.Bar(y=df[label_col], x=df[value_col], orientation="h", marker_color=color,
                           customdata=text, hovertemplate="%{y}<br>%{customdata}<extra></extra>"))
    fig.update_yaxes(autorange="reversed", automargin=True)
    fig.update_xaxes(tickformat=",.0f")
    return _layout(fig, title, value_title, None, height=max(380, 24 * len(df)), legend=False)


def histogram(bins: pd.DataFrame, title: str, x_title: str, money: bool = False) -> go.Figure:
    f = fmt.brl if money else (lambda v: fmt.num(v, 1))
    labels = [f"{f(a)} a {f(b)}" for a, b in zip(bins["inicio"], bins["fim"])]
    fig = go.Figure(go.Bar(x=(bins["inicio"] + bins["fim"]) / 2, y=bins["n"],
                           width=(bins["fim"] - bins["inicio"]) * 0.96, marker_color=palette()["blue"],
                           customdata=list(zip(labels, [fmt.integer(v) for v in bins["n"]])),
                           hovertemplate="%{customdata[0]}<br>Registros: %{customdata[1]}<extra></extra>"))
    fig.update_yaxes(tickformat=",d")
    if money:
        fig.update_xaxes(tickformat=",.0f", tickprefix="R$ ")
    return _layout(fig, title, x_title, "Registros", legend=False)


def value_histogram(values: pd.Series, title: str, x_title: str, bins: int = 30,
                    log_x: bool = False) -> go.Figure:
    """Histograma de poucas observações (ex.: 295 municípios), calculado no navegador."""
    import numpy as np
    clean = values.dropna().astype(float)
    if log_x:
        clean = clean[clean > 0]
        edges = np.logspace(np.log10(clean.min()), np.log10(clean.max()), bins + 1)
    else:
        edges = np.linspace(clean.min(), clean.max(), bins + 1)
    counts, edges = np.histogram(clean, bins=edges)
    df = pd.DataFrame({"inicio": edges[:-1], "fim": edges[1:], "n": counts})
    fig = histogram(df, title, x_title)
    if log_x:
        fig.update_xaxes(type="log")
        fig.data[0].width = None
    fig.update_yaxes(title="Municípios")
    return fig


def scatter(df: pd.DataFrame, x: str, y: str, title: str, x_title: str, y_title: str,
            hover: str | None = None, log_x: bool = False, log_y: bool = False,
            group: str | None = None) -> go.Figure:
    fig = go.Figure()
    groups = [(None, df)] if not group else list(df.groupby(group, sort=True))
    if group and len(groups) > len(SERIES):
        top = df[group].value_counts().index[: len(SERIES) - 1]
        df = df.assign(**{group: df[group].where(df[group].isin(top), "Outros")})
        groups = list(df.groupby(group, sort=True))
    for i, (name, part) in enumerate(groups):
        names = part[hover] if hover else [""] * len(part)
        fig.add_scatter(
            x=part[x], y=part[y], mode="markers", name=str(name) if name is not None else "",
            marker=dict(size=8, color=SERIES[i % len(SERIES)], opacity=0.65,
                        line=dict(width=1, color="rgba(255,255,255,0.8)")),
            customdata=list(zip(names, [fmt.num(v, 2) for v in part[x]], [fmt.num(v, 2) for v in part[y]])),
            hovertemplate="%{customdata[0]}<br>" + x_title + ": %{customdata[1]}<br>" + y_title
                          + ": %{customdata[2]}<extra></extra>")
    fig.update_xaxes(tickformat=",~f")
    fig.update_yaxes(tickformat=",~f")
    if log_x:
        fig.update_xaxes(type="log")
    if log_y:
        fig.update_yaxes(type="log")
    return _layout(fig, title, x_title, y_title, height=460, legend=bool(group))


def heatmap(pivot: pd.DataFrame, title: str, value_title: str, diverging: bool = False,
            money: bool = False) -> go.Figure:
    z = pivot.values.astype(float)
    text = [[(fmt.brl(v) if money else fmt.integer(v)) if pd.notna(v) else "—" for v in row] for row in z]
    kwargs = dict(colorscale=DIVERGING, zmid=0) if diverging else dict(colorscale=SEQUENTIAL)
    fig = go.Figure(go.Heatmap(z=z, x=[str(c) for c in pivot.columns], y=[str(i) for i in pivot.index],
                               text=text, hovertemplate="%{y}<br>%{x}<br>" + value_title + ": %{text}<extra></extra>",
                               colorbar=dict(title=value_title), xgap=2, ygap=2, **kwargs))
    fig.update_yaxes(autorange="reversed", automargin=True, showgrid=False)
    fig.update_xaxes(automargin=True)
    return _layout(fig, title, None, None, height=max(420, 26 * len(pivot.index) + 120), legend=False)


def education_share(df: pd.DataFrame, group_col: str, title: str) -> go.Figure:
    """Barras 100% empilhadas da escolaridade por grupo, em 6 faixas ordinais.
    `df` precisa das colunas: group_col, escolaridade (código), n."""
    band_of = {code: label for label, codes in EDUCATION_BANDS for code in codes}
    data = df.assign(faixa=df["escolaridade"].map(lambda c: band_of.get(c, "Não identificado")))
    data = data.groupby([group_col, "faixa"], as_index=False)["n"].sum()
    data["share"] = data["n"] / data.groupby(group_col)["n"].transform("sum")
    ramp = palette()["ordinal"]
    fig = go.Figure()
    for i, (label, _) in enumerate(EDUCATION_BANDS + [("Não identificado", [])]):
        part = data[data["faixa"] == label]
        if part.empty:
            continue
        color = ramp[i] if i < len(ramp) else GRAY
        fig.add_bar(y=part[group_col], x=part["share"], orientation="h", name=label,
                    marker=dict(color=color, line=dict(width=2, color="rgba(255,255,255,0.9)")),
                    customdata=list(zip([fmt.pct(v) for v in part["share"]], [fmt.integer(v) for v in part["n"]])),
                    hovertemplate="%{y}<br>" + label + ": %{customdata[0]} (%{customdata[1]})<extra></extra>")
    fig.update_layout(barmode="stack")
    fig.update_xaxes(tickformat=".0%", range=[0, 1])
    fig.update_yaxes(autorange="reversed", automargin=True)
    fig = _layout(fig, title, "Participação nas movimentações", None,
                  height=max(420, 30 * data[group_col].nunique() + 180))
    fig.update_layout(legend=dict(orientation="h", y=-0.12, yanchor="top", x=0, xanchor="left", traceorder="normal"))
    return fig


def line_series(df: pd.DataFrame, x: str, ys: list[tuple[str, str, str]], title: str,
                y_title: str) -> go.Figure:
    fig = go.Figure()
    for col, name, color in ys:
        fig.add_scatter(x=df[x], y=df[col], mode="lines+markers", name=name, line=dict(width=2, color=color),
                        marker=dict(size=8), customdata=[fmt.integer(v) for v in df[col]],
                        hovertemplate="%{x}<br>" + name + ": %{customdata}<extra></extra>")
    fig.update_layout(hovermode="x unified")
    return _layout(fig, title, None, y_title)
