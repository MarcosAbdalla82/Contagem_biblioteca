import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz
import io

# ── Configurações via Secrets ────────────────────────
SUPABASE_URL    = st.secrets["SUPABASE_URL"]
SUPABASE_APIKEY = st.secrets["SUPABASE_APIKEY"]

HEADERS = {
    "apikey":        SUPABASE_APIKEY,
    "Authorization": f"Bearer {SUPABASE_APIKEY}",
    "Content-Type":  "application/json"
}

# ── Buscar visitas ───────────────────────────────────
@st.cache_data(ttl=30)  # atualiza a cada 30 segundos
def buscar_visitas():
    url = f"{SUPABASE_URL}/rest/v1/visitas?select=*&order=entrada_em.desc"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    dados = res.json()
    return pd.DataFrame(dados if isinstance(dados, list) else [])

# ── Resumo por dia ───────────────────────────────────
def resumo_por_dia(df):
    df["data"] = pd.to_datetime(df["entrada_em"]).dt.date
    return df.groupby("data").size().reset_index(name="total_visitas")

# ── Gerar Excel em memória (sem salvar arquivo) ──────
def gerar_excel(df, resumo):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer,     sheet_name="Registros",     index=False)
        resumo.to_excel(writer, sheet_name="Resumo Diário", index=False)
    return buffer.getvalue()

# ── Interface Streamlit ──────────────────────────────
st.set_page_config(page_title="Contador de Visitas", page_icon="🏪", layout="wide")

st.title("🏪 Contador de Visitas da Biblioteca")
st.caption(f"Atualizado automaticamente a cada 30 segundos")

# Botão de atualização manual
if st.button("🔄 Atualizar agora"):
    st.cache_data.clear()

df = buscar_visitas()

if df.empty:
    st.warning("Nenhuma visita registrada ainda.")
else:
    resumo = resumo_por_dia(df)

    # ── Métricas no topo ─────────────────────────────
    fuso_brasilia = pytz.timezone("America/Sao_Paulo")
    hoje          = datetime.now(fuso_brasilia).date()

    visitas_hoje = resumo[resumo["data"] == hoje]["total_visitas"].sum()
    total_geral  = len(df)

    col1, col2, col3 = st.columns(3)
    col1.metric("📅 Visitas hoje",     visitas_hoje)
    col2.metric("📊 Total geral",      total_geral)
    col3.metric("📆 Dias registrados", len(resumo))

    st.divider()

    # ── Gráfico de visitas por dia ───────────────────
    st.subheader("📈 Visitas por dia")
    resumo_chart = resumo.set_index("data")
    st.bar_chart(resumo_chart["total_visitas"])

    # ── Tabelas ──────────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("📋 Resumo diário")
        st.dataframe(resumo, use_container_width=True)

    with col_b:
        st.subheader("🗂️ Todos os registros")
        st.dataframe(df[["id", "entrada_em", "data"]], use_container_width=True)

    # ── Download Excel ───────────────────────────────
    st.divider()
    excel = gerar_excel(df[["id", "entrada_em", "data"]], resumo)
    st.download_button(
        label="⬇️ Baixar planilha Excel",
        data=excel,
        file_name=f"visitas_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
