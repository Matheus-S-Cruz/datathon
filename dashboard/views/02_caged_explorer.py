"""Página 2 — Explorador do Novo CAGED: tabela paginada, pesquisa, amostras, registro e exportação."""

import math

import pandas as pd
import streamlit as st

from dashboard import formatting as fmt
from dashboard.components import filters, tables, ui
from dashboard.services import queries as Q
from dashboard.services.catalog import BY_NAME, CAGED_COLUMNS, q
from dashboard.services.dictionary import NO_DESCRIPTION, layout_table, load_sheets

RAW_COLUMNS = [c.name for c in CAGED_COLUMNS]
MAX_VALUE_OPTIONS = 400


@st.cache_data(show_spinner=False)
def _layout_descriptions() -> dict[str, str]:
    lay = layout_table(load_sheets())
    return dict(zip(lay["variavel"], lay["descricao"]))


def search_panel() -> dict:
    """Pesquisa por texto e filtro por valores de qualquer coluna."""
    with st.expander("Pesquisar e filtrar por valores", icon=":material/search:", expanded=True):
        with st.form("exp_search"):
            c = st.columns([0.35, 0.2, 0.45])
            col = c[0].selectbox("Coluna pesquisada", ["(todas as colunas)"] + RAW_COLUMNS, key="exp_tcol")
            mode = c[1].selectbox("Modo", Q.TEXT_MODES, key="exp_tmode")
            term = c[2].text_input("Texto ou código", key="exp_term",
                                   placeholder="ex.: 715505, 2018,00, 420910")
            st.caption("A base guarda **códigos**, não nomes: para achar um município pelo nome, use o filtro "
                       "**Município** na barra lateral. Pesquisa sem diferenciar maiúsculas de minúsculas.")
            c = st.columns([0.35, 0.65])
            vcol = c[0].selectbox("Filtrar valores da coluna", ["(nenhuma)"] + RAW_COLUMNS, key="exp_vcol")
            values: list[str] = []
            if vcol != "(nenhuma)":
                n_distinct = Q.count_distinct(q(vcol))
                if n_distinct <= MAX_VALUE_OPTIONS:
                    opts = Q.distinct_values(q(vcol))
                    sheet = BY_NAME[vcol].sheet
                    label = {v: f"{v}" + (f" · {Q.describe(sheet, v)}" if sheet else "") + f"  ({fmt.integer(n)})"
                             for v, n in zip(opts["valor"], opts["n"])}
                    values = c[1].multiselect(f"Valores de `{vcol}`", list(opts["valor"]),
                                              format_func=lambda v: label.get(v, v), key=f"exp_vals_{vcol}")
                else:
                    c[1].info(f"`{vcol}` tem {fmt.integer(n_distinct)} valores distintos — use a pesquisa por texto.")
            st.form_submit_button("Pesquisar", icon=":material/search:")
    return {"texto": term.strip() or None,
            "texto_coluna": None if col == "(todas as colunas)" else col,
            "texto_modo": mode,
            "valores_coluna": ((vcol, tuple(values)),) if values else ()}


def record_view(linha: int) -> None:
    rec = Q.record(linha)
    if rec.empty:
        st.warning(f"Não existe a linha {fmt.integer(linha)} no arquivo.")
        return
    row = rec.iloc[0]
    desc = _layout_descriptions()
    rows = []
    for c in CAGED_COLUMNS:
        typed = row[c.typed]
        rows.append({
            "coluna original": c.name,
            "valor original (texto)": row[c.name],
            "valor convertido": "" if pd.isna(typed) else (fmt.brl(typed) if c.kind.startswith("valor monetário") else str(typed)),
            "significado do código (dicionário)": Q.describe(c.sheet, typed) if c.sheet else "",
            "tipo identificado": c.kind,
            "descrição do campo (dicionário)": desc.get(c.name, NO_DESCRIPTION),
        })
    st.markdown(f"**Linha {fmt.integer(linha)} do arquivo** · {row['movimento'] or 'movimento inválido'} · "
                f"{Q.municipality_names().get(row['municipio'], row['municipio'])} · "
                f"{fmt.competencia(row['competencia_dec'])}")
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=1080)


def main() -> None:
    ui.section_header("Exploração e consulta", "Explorador do Novo CAGED",
                   "Consulta sob demanda ao Parquet (3,4 milhões de linhas). Só a página visível é enviada ao navegador.")
    ui.explain("Cada linha é **uma movimentação** (uma admissão ou um desligamento), não uma pessoa nem uma vaga. "
               "Os valores aparecem **exatamente como estão no arquivo** (texto). Use a aba *Registro individual* "
               "para ver o valor convertido e o significado de cada código.")

    base = filters.filter_panel("exp")
    extra = search_panel()
    f = Q.Filters(**{**base.__dict__, **extra})
    ui.active_filters(f.active())

    with st.spinner("Contando registros…"):
        total = Q.explorer_count(f)
    st.metric("Registros encontrados", fmt.integer(total))
    if total == 0:
        st.warning("Nenhum registro atende aos filtros.")
        return

    tab_table, tab_sample, tab_record, tab_struct = st.tabs(
        ["Tabela paginada", "Amostras", "Registro individual", "Estrutura das colunas"])

    with tab_table:
        c = st.columns([0.4, 0.25, 0.15, 0.2])
        cols = c[0].multiselect("Colunas exibidas", RAW_COLUMNS, default=RAW_COLUMNS, key="exp_cols",
                                placeholder="Todas")
        order = c[1].selectbox("Ordenar por", ["linha"] + RAW_COLUMNS, key="exp_order",
                               help="Colunas numéricas (salário, idade, horas) são ordenadas pelo valor, não pelo texto.")
        desc = c[2].toggle("Decrescente", key="exp_desc")
        size = c[3].selectbox("Registros por página", [25, 50, 100, 250, 500], index=1, key="exp_size")
        pages = max(math.ceil(total / size), 1)
        signature = (f, size, order, desc)
        if st.session_state.get("exp_signature") != signature or st.session_state.get("exp_page", 1) > pages:
            st.session_state["exp_signature"] = signature
            st.session_state["exp_page"] = 1
        c = st.columns([0.25, 0.75])
        page = c[0].number_input(f"Página (de {fmt.integer(pages)})", min_value=1, max_value=pages,
                                 step=1, key="exp_page")
        start = (page - 1) * size + 1
        c[1].caption(f"Mostrando registros {fmt.integer(start)} a {fmt.integer(min(page * size, total))} "
                     f"de {fmt.integer(total)}. A coluna **linha** é a posição no arquivo (identificador do registro).")
        with st.spinner("Consultando página…"):
            df = Q.explorer_page(f, cols, order, desc, size, page)
        event = st.dataframe(df, hide_index=True, width="stretch", height=min(38 * len(df) + 40, 720),
                             on_select="rerun", selection_mode="single-row", key="exp_grid")
        sel = event.selection.rows if event and event.selection else []
        if sel:
            st.session_state["exp_selected"] = int(df.iloc[sel[0]]["linha"])
            st.success(f"Linha {fmt.integer(st.session_state['exp_selected'])} selecionada — veja a aba "
                       "*Registro individual*.", icon=":material/touch_app:")
        else:
            st.caption("Clique na caixa à esquerda de uma linha para abrir o registro completo.")

        with st.expander("Exportar resultados filtrados (CSV)", icon=":material/download:"):
            st.markdown(f"Exporta os registros filtrados com os **valores originais**, na ordem escolhida, "
                        f"até {fmt.integer(Q.EXPORT_MAX_ROWS)} linhas. Separador `;` e codificação UTF-8 (abre no Excel).")
            if total > Q.EXPORT_MAX_ROWS:
                st.warning(f"O filtro atual tem {fmt.integer(total)} registros; só os primeiros "
                           f"{fmt.integer(Q.EXPORT_MAX_ROWS)} serão exportados. Refine os filtros para exportar tudo.")
            if st.button("Preparar arquivo", icon=":material/build:", key="exp_prepare"):
                with st.spinner("Gerando CSV…"):
                    data, n = Q.export_csv(f, cols, order, desc)
                st.session_state["exp_export"] = (data, n, (f, tuple(cols), order, desc))
            prepared = st.session_state.get("exp_export")
            if prepared and prepared[2] != (f, tuple(cols), order, desc):
                st.caption("Os filtros mudaram desde a última preparação: clique em *Preparar arquivo* de novo.")
            elif prepared:
                data, n, _ = prepared
                st.download_button(f"Baixar CSV ({fmt.integer(n)} registros, {fmt.megabytes(len(data) / 1048576)})",
                                   data, file_name="caged_filtrado.csv", mime="text/csv",
                                   icon=":material/download:", key="exp_download")
                st.caption("O arquivo reflete os filtros do momento em que foi preparado.")

    with tab_sample:
        c = st.columns([0.4, 0.3, 0.3])
        method = c[0].radio("Tipo de amostragem", ["primeiros", "aleatória"], horizontal=True, key="exp_smethod",
                            format_func=lambda m: "Primeiros registros (ordem do arquivo)" if m == "primeiros"
                            else "Amostra aleatória simples")
        n = c[1].number_input("Tamanho da amostra", 10, 5000, 100, step=10, key="exp_sn")
        seed = c[2].number_input("Semente", 0, 1_000_000, 42, key="exp_seed", disabled=method != "aleatória",
                                 help="Mesma semente + mesmos filtros = mesma amostra.")
        df = Q.explorer_sample(f, [], int(n), method, int(seed))
        if method == "aleatória":
            st.badge(f"Amostra aleatória simples, sem reposição: {fmt.integer(len(df))} de {fmt.integer(total)} "
                     f"registros filtrados (semente {seed})", icon=":material/shuffle:", color="violet")
        else:
            st.badge(f"Primeiros {fmt.integer(len(df))} registros filtrados, na ordem do arquivo — NÃO é uma amostra "
                     "representativa (o arquivo está ordenado por mês)", icon=":material/vertical_align_top:",
                     color="gray")
        st.dataframe(df, hide_index=True, width="stretch", height=520)
        tables.download(df, f"caged_amostra_{method}.csv", "Baixar amostra (CSV)", key="exp_sample_dl")

    with tab_record:
        default = st.session_state.get("exp_selected", 1)
        linha = st.number_input("Número da linha no arquivo", min_value=1, max_value=int(Q.overview_kpis()["registros"]),
                                value=int(default), step=1, key=f"exp_rec_{default}")
        record_view(int(linha))

    with tab_struct:
        desc = _layout_descriptions()
        types = Q.run("SELECT column_name, column_type FROM (DESCRIBE caged_raw)")
        stored = dict(zip(types["column_name"], types["column_type"]))
        st.dataframe(pd.DataFrame([{
            "coluna original": c.name, "tipo armazenado": stored.get(c.name, "?"), "tipo identificado": c.kind,
            "coluna convertida (SQL)": c.typed, "aba de códigos": c.sheet or "—",
            "descrição (dicionário)": desc.get(c.name, NO_DESCRIPTION)} for c in CAGED_COLUMNS]),
            hide_index=True, width="stretch", height=1100)


ui.guarded(main)
