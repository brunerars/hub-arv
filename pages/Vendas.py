import streamlit as st
import pandas as pd
import plotly.express as px

# ==============================
# 1. Função de carga dos dados
# ==============================
@st.cache_data
def load_data(path, sheet):
    df = pd.read_excel(path, sheet_name=sheet)

    df = df.rename(columns={
        "Data da Venda": "data_venda",
        "Data de Emissão da NF": "data_nf",
        "Cliente": "cliente",
        "Vendedor Responsável": "vendedor",
        "Tipo de Solução": "tipo_solucao",
        "Descrição do Projeto": "descricao_projeto",
        "Valor da Venda (R$)": "valor_venda",
        "OS.": "os",
        "Proposta": "proposta",
    })

    df["data_venda"] = pd.to_datetime(df["data_venda"])
    df["data_nf"] = pd.to_datetime(df["data_nf"])

    df["valor_venda"] = pd.to_numeric(df["valor_venda"], errors="coerce")

    df["ano"] = df["data_nf"].dt.year
    df["mes"] = df["data_nf"].dt.month
    df["ano_mes"] = df["data_nf"].dt.to_period("M").astype(str)

    return df


# ==============================
# 2. Título da Página
# ==============================
st.title("📊 Dashboard de Vendas")


# ==============================
# 3. Carregar dados
# ==============================
file_path = "data/DADOS-VENDAS.xlsx"
df = load_data(file_path, 5)


# ==============================
# 4. Filtros laterais
# ==============================
st.sidebar.header("Filtros")

anos = sorted(df["ano"].unique())
ano_sel = st.sidebar.multiselect("Ano da Venda", anos, default=anos)

vendedores = sorted(df["vendedor"].dropna().unique())
vendedor_sel = st.sidebar.multiselect("Vendedor", vendedores, default=vendedores)

tipos = sorted(df["tipo_solucao"].dropna().unique())
tipo_sel = st.sidebar.multiselect("Tipo de Solução", tipos, default=tipos)

clientes = sorted(df["cliente"].dropna().unique())
cliente_sel = st.sidebar.multiselect("Cliente", clientes, default=clientes)

df_filtrado = df[
    (df["ano"].isin(ano_sel)) &
    (df["vendedor"].isin(vendedor_sel)) &
    (df["tipo_solucao"].isin(tipo_sel)) &
    (df["cliente"].isin(cliente_sel))
]


# ==============================
# 5. KPIs
# ==============================
st.subheader("📌 Indicadores Gerais")

total_vendas = df_filtrado["valor_venda"].sum()
qtd_vendas = df_filtrado.shape[0]
ticket_medio = total_vendas / qtd_vendas if qtd_vendas > 0 else 0

df_filtrado["lead_time"] = (df_filtrado["data_nf"] - df_filtrado["data_venda"]).dt.days
ciclo_medio = df_filtrado["lead_time"].mean()

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Faturamento Total", f"R$ {total_vendas:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
col2.metric("📦 Nº de Vendas", qtd_vendas)
col3.metric("🎯 Ticket Médio", f"R$ {ticket_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
col4.metric("⏱ Ciclo Médio (dias)", f"{ciclo_medio:.1f}" if not pd.isna(ciclo_medio) else "-")

st.markdown("---")


# ==============================
# 6. Gráfico – Faturamento por mês
# ==============================
st.subheader("📈 Faturamento por Mês")

if not df_filtrado.empty:
    df_mes = (
        df_filtrado.groupby("ano_mes")["valor_venda"]
        .sum()
        .reset_index()
        .sort_values("ano_mes")
    )

    fig = px.line(df_mes, x="ano_mes", y="valor_venda", markers=True,
                  title="Faturamento ao longo do tempo",
                  labels={"ano_mes": "Ano-Mês", "valor_venda": "Faturamento (R$)"})
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nenhum dado encontrado para os filtros selecionados.")


# ==============================
# 7. Gráfico – Faturamento por Tipo de Solução
# ==============================
st.subheader("🏗 Faturamento por Tipo de Solução")

if not df_filtrado.empty:
    df_tipo = (
        df_filtrado.groupby("tipo_solucao")["valor_venda"]
        .sum()
        .reset_index()
        .sort_values("valor_venda", ascending=False)
    )

    fig = px.bar(df_tipo, x="tipo_solucao", y="valor_venda",
                 title="Faturamento por Tipo de Solução",
                 labels={"tipo_solucao": "Tipo", "valor_venda": "Faturamento"})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nenhum dado encontrado para os filtros selecionados.")


# ==============================
# 8. Gráfico – Top 10 Clientes
# ==============================
st.subheader("👥 Top 10 Clientes por Faturamento")

if not df_filtrado.empty:
    df_cliente = (
        df_filtrado.groupby("cliente")["valor_venda"]
        .sum()
        .reset_index()
        .sort_values("valor_venda", ascending=False)
        .head(10)
    )

    fig = px.bar(df_cliente, x="valor_venda", y="cliente",
                 orientation="h",
                 title="Top 10 Clientes",
                 labels={"cliente": "Cliente", "valor_venda": "Faturamento"})
    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nenhum dado encontrado para os filtros selecionados.")


# ==============================
# 9. Gráfico – Faturamento por Vendedor
# ==============================
st.subheader("👤 Faturamento por Vendedor")

if not df_filtrado.empty:
    df_vend = (
        df_filtrado.groupby("vendedor")["valor_venda"]
        .sum()
        .reset_index()
        .sort_values("valor_venda", ascending=False)
    )

    fig = px.bar(df_vend, x="vendedor", y="valor_venda",
                 title="Faturamento por Vendedor")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nenhum dado encontrado para os filtros selecionados.")


# ==============================
# 10. Tabela de detalhes
# ==============================
st.subheader("📄 Detalhamento das Vendas")

st.dataframe(
    df_filtrado[[
        "data_venda",
        "data_nf",
        "cliente",
        "vendedor",
        "tipo_solucao",
        "descricao_projeto",
        "valor_venda",
        "os",
        "proposta"
    ]].sort_values("data_venda", ascending=False),
    use_container_width=True
)
