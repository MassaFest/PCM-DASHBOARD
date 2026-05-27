import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
from io import StringIO

st.set_page_config(
    page_title="PCM Dashboard",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── IDs das planilhas (configuráveis via sidebar) ──────────────────────────────
DEFAULT_SHEET_CHAMADOS  = "1AJXsR6YpgSuYrDRo_vtNpsJtn0vSQ9ayjBX_4mMTtdw"
DEFAULT_GID_CHAMADOS    = "2143366097"
DEFAULT_SHEET_RETORNOS  = "1KO_U-Ly1s9rW2YuPdc48zwOcR6EuPf1CfBGbbSZMjEY"
DEFAULT_GID_RETORNOS    = "824431047"

# ── Carregamento de dados ──────────────────────────────────────────────────────
@st.cache_data(ttl=300)  # cache 5 minutos
def load_sheet(sheet_id: str, gid: str) -> pd.DataFrame:
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text))
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar planilha (id={sheet_id}, gid={gid}): {e}")
        return pd.DataFrame()


def parse_date_col(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
    return df


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3208/3208728.png", width=64)
    st.title("PCM Dashboard")
    st.markdown("---")

    st.subheader("Planilhas")
    sheet_chamados = st.text_input("ID – Chamados", DEFAULT_SHEET_CHAMADOS)
    gid_chamados   = st.text_input("GID – Chamados", DEFAULT_GID_CHAMADOS)
    sheet_retornos = st.text_input("ID – Retornos", DEFAULT_SHEET_RETORNOS)
    gid_retornos   = st.text_input("GID – Retornos", DEFAULT_GID_RETORNOS)

    if st.button("🔄 Atualizar dados"):
        st.cache_data.clear()

    st.markdown("---")
    st.caption("Dados atualizados a cada 5 min automaticamente.")


# ── Carregar dados ─────────────────────────────────────────────────────────────
with st.spinner("Carregando planilhas…"):
    df_chamados = load_sheet(sheet_chamados, gid_chamados)
    df_retornos = load_sheet(sheet_retornos, gid_retornos)

if df_chamados.empty and df_retornos.empty:
    st.warning("Nenhum dado encontrado. Verifique se as planilhas estão públicas (compartilhar > qualquer pessoa com o link).")
    st.stop()

# ── Mapeamento de colunas (detecta automaticamente ou usa padrão) ──────────────
# Ajuste os nomes abaixo de acordo com os cabeçalhos reais das suas planilhas.
st.sidebar.markdown("---")
st.sidebar.subheader("Colunas – Chamados")

def col_select(label, df, default_hints, key):
    cols = ["(nenhuma)"] + list(df.columns)
    best = next((c for h in default_hints for c in df.columns if h.lower() in c.lower()), "(nenhuma)")
    idx = cols.index(best) if best in cols else 0
    return st.sidebar.selectbox(label, cols, index=idx, key=key)

if not df_chamados.empty:
    col_data_cham    = col_select("Data/Hora", df_chamados, ["timestamp","data","hora","abertura"], "c_data")
    col_maquina      = col_select("Máquina",   df_chamados, ["maquina","máquina","equipamento","ativo"], "c_maq")
    col_patrimonio   = col_select("Patrimônio",df_chamados, ["patrimonio","patrimônio","tag","codigo"], "c_pat")
    col_problema     = col_select("Problema",  df_chamados, ["problema","descricao","descri","falha","defeito"], "c_prob")
    col_encarregado  = col_select("Encarregado",df_chamados,["encarregado","solicitante","abertura","nome"], "c_enc")
else:
    col_data_cham = col_maquina = col_patrimonio = col_problema = col_encarregado = "(nenhuma)"

st.sidebar.subheader("Colunas – Retornos")
if not df_retornos.empty:
    col_data_ret  = col_select("Data/Hora",  df_retornos, ["timestamp","data","hora","conclusao"], "r_data")
    col_mecanico  = col_select("Mecânico",   df_retornos, ["mecanico","mecânico","tecnico","técnico","executor"], "r_mec")
    col_maq_ret   = col_select("Máquina",    df_retornos, ["maquina","máquina","equipamento","ativo"], "r_maq")
    col_servico   = col_select("Serviço",    df_retornos, ["servico","serviço","atividade","descri","relatorio"], "r_serv")
    col_status    = col_select("Status",     df_retornos, ["status","situacao","situação","concluido"], "r_stat")
else:
    col_data_ret = col_mecanico = col_maq_ret = col_servico = col_status = "(nenhuma)"


# ── Pré-processar ──────────────────────────────────────────────────────────────
if not df_chamados.empty and col_data_cham != "(nenhuma)":
    df_chamados = parse_date_col(df_chamados, col_data_cham)

if not df_retornos.empty and col_data_ret != "(nenhuma)":
    df_retornos = parse_date_col(df_retornos, col_data_ret)

# Coluna de máquina unificada nos retornos
maq_col_ret = col_maq_ret if col_maq_ret != "(nenhuma)" else None


# ── Filtros principais ─────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.subheader("Filtros")

# Período
all_dates = []
if not df_chamados.empty and col_data_cham != "(nenhuma)":
    all_dates += list(df_chamados[col_data_cham].dropna())
if not df_retornos.empty and col_data_ret != "(nenhuma)":
    all_dates += list(df_retornos[col_data_ret].dropna())

if all_dates:
    min_date = min(all_dates).date()
    max_date = max(all_dates).date()
else:
    min_date = datetime.today().date() - timedelta(days=365)
    max_date = datetime.today().date()

periodo = st.sidebar.date_input("Período", value=(min_date, max_date), min_value=min_date, max_value=max_date)
if len(periodo) == 2:
    dt_ini, dt_fim = pd.Timestamp(periodo[0]), pd.Timestamp(periodo[1]) + timedelta(days=1)
else:
    dt_ini, dt_fim = pd.Timestamp(min_date), pd.Timestamp(max_date) + timedelta(days=1)

# Filtro mecânico
mecánicos = []
if not df_retornos.empty and col_mecanico != "(nenhuma)":
    mecánicos = sorted(df_retornos[col_mecanico].dropna().unique().tolist())
sel_mecanicos = st.sidebar.multiselect("Mecânicos", mecánicos, default=mecánicos)

# Filtro máquina (união das duas planilhas)
maquinas = []
if not df_chamados.empty and col_maquina != "(nenhuma)":
    maquinas += df_chamados[col_maquina].dropna().unique().tolist()
if not df_retornos.empty and maq_col_ret:
    maquinas += df_retornos[maq_col_ret].dropna().unique().tolist()
maquinas = sorted(set(maquinas))
sel_maquinas = st.sidebar.multiselect("Máquinas", maquinas, default=maquinas)


# ── Aplicar filtros ────────────────────────────────────────────────────────────
def filter_df(df, date_col, maq_col_name, mec_col_name=None):
    if df.empty:
        return df
    if date_col != "(nenhuma)" and date_col in df.columns:
        df = df[df[date_col].between(dt_ini, dt_fim, inclusive="left")]
    if maq_col_name and maq_col_name in df.columns and sel_maquinas:
        df = df[df[maq_col_name].isin(sel_maquinas)]
    if mec_col_name and mec_col_name in df.columns and sel_mecanicos:
        df = df[df[mec_col_name].isin(sel_mecanicos)]
    return df

df_ch = filter_df(df_chamados, col_data_cham, col_maquina if col_maquina != "(nenhuma)" else None)
df_ret = filter_df(df_retornos, col_data_ret, maq_col_ret, col_mecanico if col_mecanico != "(nenhuma)" else None)


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
st.title("🔧 PCM – Painel de Manutenção")

tab_visao, tab_mecanico, tab_maquina, tab_historico, tab_dados = st.tabs([
    "📊 Visão Geral", "👷 Por Mecânico", "🏭 Por Máquina", "📋 Histórico", "📂 Dados Brutos"
])


# ─────────────────────────────────────────────
# ABA 1: Visão Geral
# ─────────────────────────────────────────────
with tab_visao:
    c1, c2, c3, c4 = st.columns(4)
    total_chamados = len(df_ch)
    total_retornos = len(df_ret)
    total_maquinas = len(set(
        (list(df_ch[col_maquina].dropna()) if col_maquina != "(nenhuma)" and not df_ch.empty else []) +
        (list(df_ret[maq_col_ret].dropna()) if maq_col_ret and not df_ret.empty else [])
    ))
    total_mecanicos = df_ret[col_mecanico].nunique() if col_mecanico != "(nenhuma)" and not df_ret.empty else 0

    c1.metric("Total de Chamados", total_chamados)
    c2.metric("Atendimentos Realizados", total_retornos)
    c3.metric("Máquinas Atendidas", total_maquinas)
    c4.metric("Mecânicos Ativos", total_mecanicos)

    st.markdown("---")

    col_l, col_r = st.columns(2)

    # Chamados ao longo do tempo
    with col_l:
        st.subheader("Chamados ao longo do tempo")
        if not df_ch.empty and col_data_cham != "(nenhuma)":
            granularidade = st.selectbox("Granularidade", ["Dia", "Semana", "Mês"], key="gran_visao")
            freq_map = {"Dia": "D", "Semana": "W", "Mês": "ME"}
            ts = df_ch.set_index(col_data_cham).resample(freq_map[granularidade]).size().reset_index(name="Chamados")
            fig = px.bar(ts, x=col_data_cham, y="Chamados", color_discrete_sequence=["#1f77b4"])
            fig.update_layout(margin=dict(t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Configure a coluna de data dos chamados no menu lateral.")

    # Atendimentos por mecânico
    with col_r:
        st.subheader("Atendimentos por mecânico")
        if not df_ret.empty and col_mecanico != "(nenhuma)":
            mec_count = df_ret[col_mecanico].value_counts().reset_index()
            mec_count.columns = ["Mecânico", "Atendimentos"]
            fig = px.bar(mec_count, x="Atendimentos", y="Mecânico", orientation="h",
                         color="Atendimentos", color_continuous_scale="Blues")
            fig.update_layout(margin=dict(t=10, b=10), yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Configure a coluna de mecânico no menu lateral.")


# ─────────────────────────────────────────────
# ABA 2: Por Mecânico
# ─────────────────────────────────────────────
with tab_mecanico:
    st.subheader("Desempenho por Mecânico")

    if df_ret.empty or col_mecanico == "(nenhuma)":
        st.info("Dados de retorno não disponíveis ou coluna de mecânico não configurada.")
    else:
        mec_df = df_ret[col_mecanico].value_counts().reset_index()
        mec_df.columns = ["Mecânico", "Atendimentos"]
        mec_df["% do Total"] = (mec_df["Atendimentos"] / mec_df["Atendimentos"].sum() * 100).round(1)

        col_a, col_b = st.columns([1, 2])
        with col_a:
            st.dataframe(mec_df, use_container_width=True, hide_index=True)

        with col_b:
            fig = px.pie(mec_df, names="Mecânico", values="Atendimentos",
                         title="Distribuição de atendimentos",
                         color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)

        # Evolução mensal por mecânico
        if col_data_ret != "(nenhuma)":
            st.markdown("---")
            st.subheader("Evolução mensal por mecânico")
            df_ret_copy = df_ret.copy()
            df_ret_copy["Mês"] = df_ret_copy[col_data_ret].dt.to_period("M").astype(str)
            mensal = df_ret_copy.groupby(["Mês", col_mecanico]).size().reset_index(name="Atendimentos")
            fig2 = px.line(mensal, x="Mês", y="Atendimentos", color=col_mecanico, markers=True)
            fig2.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig2, use_container_width=True)


# ─────────────────────────────────────────────
# ABA 3: Por Máquina
# ─────────────────────────────────────────────
with tab_maquina:
    st.subheader("Máquinas com mais manutenção")

    maq_src_col = col_maquina if (col_maquina != "(nenhuma)" and not df_ch.empty) else None
    maq_ret_col = maq_col_ret if (maq_col_ret and not df_ret.empty) else None

    # Contagem por origem
    frames = []
    if maq_src_col:
        c = df_ch[maq_src_col].value_counts().reset_index()
        c.columns = ["Máquina", "Chamados"]
        frames.append(c.set_index("Máquina"))
    if maq_ret_col:
        c = df_ret[maq_ret_col].value_counts().reset_index()
        c.columns = ["Máquina", "Atendimentos"]
        frames.append(c.set_index("Máquina"))

    if frames:
        maq_df = pd.concat(frames, axis=1).fillna(0).astype(int).reset_index()
        maq_df.columns = ["Máquina"] + [f.columns.tolist()[0] for f in frames]
        maq_df["Total"] = maq_df.iloc[:, 1:].sum(axis=1)
        maq_df = maq_df.sort_values("Total", ascending=False)

        col_t, col_g = st.columns([1, 2])
        with col_t:
            st.dataframe(maq_df, use_container_width=True, hide_index=True)
        with col_g:
            fig = px.bar(maq_df.head(20), x="Máquina", y="Total",
                         title="Top 20 máquinas por ocorrências",
                         color="Total", color_continuous_scale="Reds")
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Configure as colunas de máquina no menu lateral.")


# ─────────────────────────────────────────────
# ABA 4: Histórico por Máquina
# ─────────────────────────────────────────────
with tab_historico:
    st.subheader("Histórico de manutenção por máquina")

    maquinas_disp = []
    if maq_src_col:
        maquinas_disp += df_ch[maq_src_col].dropna().unique().tolist()
    if maq_ret_col:
        maquinas_disp += df_ret[maq_ret_col].dropna().unique().tolist()
    maquinas_disp = sorted(set(maquinas_disp))

    if not maquinas_disp:
        st.info("Nenhuma máquina encontrada. Configure as colunas no menu lateral.")
    else:
        maq_sel = st.selectbox("Selecione a máquina", maquinas_disp)

        # Chamados dessa máquina
        hist_rows = []
        if maq_src_col and not df_ch.empty:
            subset = df_ch[df_ch[maq_src_col] == maq_sel].copy()
            subset["Origem"] = "Chamado"
            rename = {}
            if col_data_cham != "(nenhuma)":  rename[col_data_cham] = "Data/Hora"
            if col_problema   != "(nenhuma)":  rename[col_problema]   = "Descrição"
            if col_encarregado!= "(nenhuma)":  rename[col_encarregado]= "Encarregado"
            subset = subset.rename(columns=rename)
            hist_rows.append(subset)

        # Retornos dessa máquina
        if maq_ret_col and not df_ret.empty:
            subset = df_ret[df_ret[maq_ret_col] == maq_sel].copy()
            subset["Origem"] = "Atendimento"
            rename = {}
            if col_data_ret  != "(nenhuma)": rename[col_data_ret]  = "Data/Hora"
            if col_servico   != "(nenhuma)": rename[col_servico]   = "Descrição"
            if col_mecanico  != "(nenhuma)": rename[col_mecanico]  = "Mecânico"
            if col_status    != "(nenhuma)": rename[col_status]    = "Status"
            subset = subset.rename(columns=rename)
            hist_rows.append(subset)

        if hist_rows:
            hist = pd.concat(hist_rows, ignore_index=True)
            if "Data/Hora" in hist.columns:
                hist = hist.sort_values("Data/Hora", ascending=False)

            cols_show = [c for c in ["Data/Hora","Origem","Descrição","Mecânico","Encarregado","Status"] if c in hist.columns]
            st.dataframe(hist[cols_show], use_container_width=True, hide_index=True)

            # Métricas rápidas
            m1, m2 = st.columns(2)
            m1.metric("Total de ocorrências", len(hist))
            if "Mecânico" in hist.columns:
                top_mec = hist["Mecânico"].value_counts().idxmax() if not hist["Mecânico"].isna().all() else "—"
                m2.metric("Mecânico que mais atendeu", top_mec)
        else:
            st.info("Nenhum registro encontrado para esta máquina no período selecionado.")


# ─────────────────────────────────────────────
# ABA 5: Dados Brutos
# ─────────────────────────────────────────────
with tab_dados:
    st.subheader("Dados brutos")
    aba = st.radio("Planilha", ["Chamados", "Retornos"], horizontal=True)
    df_show = df_ch if aba == "Chamados" else df_ret

    if df_show.empty:
        st.info("Nenhum dado disponível.")
    else:
        st.write(f"{len(df_show)} registros")
        st.dataframe(df_show, use_container_width=True)
        csv = df_show.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇ Baixar CSV",
            data=csv,
            file_name=f"{aba.lower()}_{datetime.today().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
