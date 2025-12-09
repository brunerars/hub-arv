import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# ============================================================
# CONFIGURAÇÕES E FUNÇÕES AUXILIARES
# ============================================================
st.set_page_config(page_title="Dashboard de Vendas ARV", layout="wide")
st.title("💰 Dashboard de Vendas - ARV")

# Função para formatar valores em Reais
def formatar_reais(valor):
    """Formata valores em reais com separadores brasileiros"""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Função para formatar valores grandes de forma compacta
def formatar_valor_compacto(valor):
    """Formata valores grandes de forma compacta (1.5M, 250K, etc)"""
    if valor >= 1_000_000:
        return f"R$ {valor/1_000_000:.1f}M"
    elif valor >= 1_000:
        return f"R$ {valor/1_000:.0f}K"
    else:
        return f"R$ {valor:.0f}"

# Função para aplicar formatação brasileira aos eixos do Plotly
def formatar_eixo_reais(fig, eixo='y'):
    """Aplica formatação brasileira aos eixos de gráficos Plotly"""
    if eixo == 'y':
        fig.update_yaxes(tickformat=",.0f", tickprefix="R$ ", separatethousands=True)
    else:
        fig.update_xaxes(tickformat=",.0f", tickprefix="R$ ", separatethousands=True)
    return fig

# ============================================================
# 1. CARREGAMENTO E TRATAMENTO DOS DADOS
# ============================================================
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

    df["data_venda"] = pd.to_datetime(df["data_venda"], errors="coerce")
    df["data_nf"] = pd.to_datetime(df["data_nf"], errors="coerce")
    df["valor_venda"] = pd.to_numeric(df["valor_venda"], errors="coerce")

    df["ano"] = df["data_nf"].dt.year
    df["mes"] = df["data_nf"].dt.month
    df["ano_mes"] = df["data_nf"].dt.to_period("M").astype(str)
    df["trimestre"] = df["data_nf"].dt.quarter
    df["lead_time"] = (df["data_nf"] - df["data_venda"]).dt.days
    
    # Faixa de valor
    df["faixa_valor"] = pd.cut(df["valor_venda"], 
                               bins=[0, 10000, 50000, 100000, 500000, float('inf')],
                               labels=['< R$ 10k', 'R$ 10k-50k', 'R$ 50k-100k', 
                                      'R$ 100k-500k', '> R$ 500k'])

    return df

# ============================================================
# 2. CARREGAMENTO DOS DADOS
# ============================================================
file_path = "data/DADOS-VENDAS.xlsx"
df = load_data(file_path, 5)

# ============================================================
# 3. FILTROS LATERAIS APRIMORADOS
# ============================================================
st.sidebar.header("🔍 Filtros")

# Filtro de período
st.sidebar.subheader("📅 Período")
periodo_opcao = st.sidebar.radio("Tipo de Período", ["Ano-Mês", "Intervalo de Datas"])

if periodo_opcao == "Ano-Mês":
    anos = sorted(df["ano"].dropna().unique())
    ano_sel = st.sidebar.multiselect("Ano da Venda", anos, default=anos)
    df_filtrado = df[df["ano"].isin(ano_sel)]
else:
    data_min = df["data_nf"].min()
    data_max = df["data_nf"].max()
    data_inicio = st.sidebar.date_input("Data Início", data_min, min_value=data_min, max_value=data_max)
    data_fim = st.sidebar.date_input("Data Fim", data_max, min_value=data_min, max_value=data_max)
    df_filtrado = df[(df["data_nf"] >= pd.Timestamp(data_inicio)) & 
                     (df["data_nf"] <= pd.Timestamp(data_fim))]

# Outros filtros
st.sidebar.subheader("🎯 Filtros de Segmentação")

vendedores = sorted(df["vendedor"].dropna().unique())
vendedor_sel = st.sidebar.multiselect("Vendedor Responsável", vendedores)

tipos = sorted(df["tipo_solucao"].dropna().unique())
tipo_sel = st.sidebar.multiselect("Tipo de Solução", tipos)

clientes = sorted(df["cliente"].dropna().unique())
cliente_sel = st.sidebar.multiselect("Cliente", clientes)

# Filtros avançados
st.sidebar.subheader("🔧 Filtros Avançados")
faixa_valor_sel = st.sidebar.multiselect("Faixa de Valor", 
                                         df["faixa_valor"].dropna().unique())

# Aplicar filtros
if len(vendedor_sel) > 0:
    df_filtrado = df_filtrado[df_filtrado["vendedor"].isin(vendedor_sel)]
if len(tipo_sel) > 0:
    df_filtrado = df_filtrado[df_filtrado["tipo_solucao"].isin(tipo_sel)]
if len(cliente_sel) > 0:
    df_filtrado = df_filtrado[df_filtrado["cliente"].isin(cliente_sel)]
if len(faixa_valor_sel) > 0:
    df_filtrado = df_filtrado[df_filtrado["faixa_valor"].isin(faixa_valor_sel)]

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado com os filtros selecionados.")
    st.stop()

# ============================================================
# 4. KPIs PRINCIPAIS COM EXPLICAÇÕES
# ============================================================
total_vendas = df_filtrado["valor_venda"].sum()
qtd_vendas = df_filtrado.shape[0]
ticket_medio = total_vendas / qtd_vendas if qtd_vendas > 0 else 0
ciclo_medio = df_filtrado["lead_time"].mean()
clientes_unicos = df_filtrado["cliente"].nunique()

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric("💰 Faturamento Total", formatar_reais(total_vendas))
    with st.expander("ℹ️ Explicação"):
        st.write("**Soma total** do valor de todas as vendas no período filtrado.")

with c2:
    st.metric("📦 Número de Vendas", f"{qtd_vendas}")
    with st.expander("ℹ️ Explicação"):
        st.write("**Quantidade de vendas** concluídas (com nota fiscal emitida) no período.")

with c3:
    st.metric("🎯 Ticket Médio", formatar_reais(ticket_medio))
    with st.expander("ℹ️ Explicação"):
        st.write("**Valor médio** por venda. Calculado dividindo o faturamento total pelo número de vendas.")

with c4:
    st.metric("⏱ Ciclo Médio", 
              f"{ciclo_medio:.0f} dias" if not pd.isna(ciclo_medio) else "N/A")
    with st.expander("ℹ️ Explicação"):
        st.write("**Tempo médio** entre a data da venda e a emissão da nota fiscal. Indica a velocidade do processo comercial.")

with c5:
    st.metric("👥 Clientes Únicos", f"{clientes_unicos}")
    with st.expander("ℹ️ Explicação"):
        st.write("**Quantidade de clientes diferentes** que realizaram compras no período.")

st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================
# 5. TABS PARA ORGANIZAR ANÁLISES
# ============================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Visão Geral",
    "👤 Vendedores",
    "👥 Clientes",
    "🏗 Produtos/Soluções",
    "📋 Detalhamento"
])

with tab1:
    st.subheader("📈 Evolução do Faturamento")
    st.caption("Acompanhe a performance de vendas ao longo do tempo e identifique tendências.")
    
    col1, col2 = st.columns(2)
    
    # Faturamento mensal
    df_mes = (
        df_filtrado.groupby("ano_mes")["valor_venda"]
        .sum()
        .reset_index()
        .sort_values("ano_mes")
    )
    df_mes.columns = ["Período", "Faturamento"]
    
    fig_mes = px.line(df_mes, x="Período", y="Faturamento", markers=True,
                      title="Evolução Mensal do Faturamento",
                      labels={"Período": "Período (Ano-Mês)", 
                             "Faturamento": "Faturamento (R$)"})
    fig_mes.update_traces(line_color='#1f77b4', line_width=3,
                         hovertemplate='<b>%{x}</b><br>Faturamento: R$ %{y:,.2f}<extra></extra>')
    fig_mes = formatar_eixo_reais(fig_mes, 'y')
    col1.plotly_chart(fig_mes, use_container_width=True)
    
    # Quantidade de vendas mensal
    df_qtd_mes = (
        df_filtrado.groupby("ano_mes").size()
        .reset_index(name="Quantidade")
        .sort_values("ano_mes")
    )
    df_qtd_mes.columns = ["Período", "Quantidade de Vendas"]
    
    fig_qtd = px.bar(df_qtd_mes, x="Período", y="Quantidade de Vendas",
                     title="Quantidade de Vendas por Mês",
                     labels={"Período": "Período (Ano-Mês)", 
                            "Quantidade de Vendas": "Nº de Vendas"},
                     color="Quantidade de Vendas",
                     color_continuous_scale="Greens")
    col2.plotly_chart(fig_qtd, use_container_width=True)
    
    # Distribuição por faixa de valor
    st.subheader("💵 Distribuição de Vendas por Faixa de Valor")
    st.caption("Visualize como as vendas se distribuem entre diferentes faixas de valor.")
    
    col_a, col_b = st.columns(2)
    
    dist_faixa = df_filtrado.groupby("faixa_valor").agg({
        "valor_venda": ["sum", "count"]
    }).reset_index()
    dist_faixa.columns = ["Faixa de Valor", "Faturamento Total", "Quantidade"]
    
    fig_pizza = px.pie(dist_faixa, values="Faturamento Total", names="Faixa de Valor",
                       title="Faturamento por Faixa de Valor",
                       labels={"Faixa de Valor": "Faixa", "Faturamento Total": "Faturamento (R$)"})
    fig_pizza.update_traces(textposition='inside', 
                           textinfo='percent+label',
                           hovertemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>')
    col_a.plotly_chart(fig_pizza, use_container_width=True)
    
    fig_barras = px.bar(dist_faixa, x="Faixa de Valor", y="Quantidade",
                       title="Quantidade de Vendas por Faixa",
                       labels={"Faixa de Valor": "Faixa de Valor", "Quantidade": "Nº de Vendas"},
                       color="Quantidade",
                       color_continuous_scale="Blues")
    col_b.plotly_chart(fig_barras, use_container_width=True)

with tab2:
    st.subheader("👤 Performance de Vendedores")
    st.caption("Análise detalhada do desempenho individual de cada vendedor.")
    
    col1, col2 = st.columns(2)
    
    # Faturamento por vendedor
    df_vend = (
        df_filtrado.groupby("vendedor")["valor_venda"]
        .sum()
        .reset_index()
        .sort_values("valor_venda", ascending=False)
    )
    df_vend.columns = ["Vendedor", "Faturamento Total"]
    
    fig_vend = px.bar(df_vend, y="Vendedor", x="Faturamento Total",
                     orientation="h",
                     title="Faturamento por Vendedor",
                     labels={"Vendedor": "Vendedor", "Faturamento Total": "Faturamento (R$)"},
                     color="Faturamento Total",
                     color_continuous_scale="Blues")
    fig_vend.update_layout(yaxis={'categoryorder':'total ascending'})
    fig_vend.update_traces(hovertemplate='<b>%{y}</b><br>Faturamento: R$ %{x:,.2f}<extra></extra>')
    fig_vend = formatar_eixo_reais(fig_vend, 'x')
    col1.plotly_chart(fig_vend, use_container_width=True)
    
    # Quantidade de vendas por vendedor
    df_vend_qtd = (
        df_filtrado.groupby("vendedor").size()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
    )
    df_vend_qtd.columns = ["Vendedor", "Quantidade de Vendas"]
    
    fig_vend_qtd = px.bar(df_vend_qtd, y="Vendedor", x="Quantidade de Vendas",
                         orientation="h",
                         title="Quantidade de Vendas por Vendedor",
                         labels={"Vendedor": "Vendedor", "Quantidade de Vendas": "Nº de Vendas"},
                         color="Quantidade de Vendas",
                         color_continuous_scale="Greens")
    fig_vend_qtd.update_layout(yaxis={'categoryorder':'total ascending'})
    col2.plotly_chart(fig_vend_qtd, use_container_width=True)
    
    # Ticket médio por vendedor
    st.subheader("💡 Ticket Médio por Vendedor")
    st.caption("Valor médio das vendas de cada vendedor. Indica o perfil de negócios fechados.")
    
    df_ticket = df_filtrado.groupby("vendedor").agg({
        "valor_venda": ["sum", "count", "mean"]
    }).reset_index()
    df_ticket.columns = ["Vendedor", "Faturamento Total", "Quantidade", "Ticket Médio"]
    df_ticket = df_ticket.sort_values("Ticket Médio", ascending=False)
    
    fig_ticket = px.bar(df_ticket, y="Vendedor", x="Ticket Médio",
                       orientation="h",
                       title="Ticket Médio por Vendedor",
                       labels={"Vendedor": "Vendedor", "Ticket Médio": "Ticket Médio (R$)"},
                       color="Ticket Médio",
                       color_continuous_scale="Oranges")
    fig_ticket.update_layout(yaxis={'categoryorder':'total ascending'})
    fig_ticket.update_traces(hovertemplate='<b>%{y}</b><br>Ticket Médio: R$ %{x:,.2f}<extra></extra>')
    fig_ticket = formatar_eixo_reais(fig_ticket, 'x')
    st.plotly_chart(fig_ticket, use_container_width=True)
    
    # Ciclo de venda por vendedor
    st.subheader("⏱ Ciclo de Venda por Vendedor")
    st.caption("Tempo médio entre a venda e a emissão da NF. Valores menores indicam processos mais ágeis.")
    
    df_ciclo = df_filtrado.groupby("vendedor")["lead_time"].mean().reset_index()
    df_ciclo.columns = ["Vendedor", "Ciclo Médio (dias)"]
    df_ciclo = df_ciclo.sort_values("Ciclo Médio (dias)", ascending=True)
    
    fig_ciclo = px.bar(df_ciclo, y="Vendedor", x="Ciclo Médio (dias)",
                      orientation="h",
                      title="Ciclo Médio de Venda por Vendedor",
                      labels={"Vendedor": "Vendedor", "Ciclo Médio (dias)": "Dias"},
                      color="Ciclo Médio (dias)",
                      color_continuous_scale="RdYlGn_r")
    fig_ciclo.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_ciclo, use_container_width=True)

with tab3:
    st.subheader("👥 Análise de Clientes")
    st.caption("Identifique os principais clientes e entenda o comportamento de compra.")
    
    col1, col2 = st.columns(2)
    
    # Top 10 clientes
    df_cliente = (
        df_filtrado.groupby("cliente")["valor_venda"]
        .sum()
        .reset_index()
        .sort_values("valor_venda", ascending=False)
        .head(10)
    )
    df_cliente.columns = ["Cliente", "Faturamento Total"]
    
    fig_cli = px.bar(df_cliente, y="Cliente", x="Faturamento Total",
                    orientation="h",
                    title="Top 10 Clientes por Faturamento",
                    labels={"Cliente": "Cliente", "Faturamento Total": "Faturamento (R$)"},
                    color="Faturamento Total",
                    color_continuous_scale="Blues")
    fig_cli.update_layout(yaxis={'categoryorder':'total ascending'})
    fig_cli.update_traces(hovertemplate='<b>%{y}</b><br>Faturamento: R$ %{x:,.2f}<extra></extra>')
    fig_cli = formatar_eixo_reais(fig_cli, 'x')
    col1.plotly_chart(fig_cli, use_container_width=True)
    
    # Recorrência de clientes
    df_recorrencia = df_filtrado.groupby("cliente").size().reset_index(name="Compras")
    df_recorrencia.columns = ["Cliente", "Número de Compras"]
    df_recorrencia_top = df_recorrencia.sort_values("Número de Compras", ascending=False).head(10)
    
    fig_rec = px.bar(df_recorrencia_top, y="Cliente", x="Número de Compras",
                    orientation="h",
                    title="Top 10 Clientes Mais Recorrentes",
                    labels={"Cliente": "Cliente", "Número de Compras": "Nº de Compras"},
                    color="Número de Compras",
                    color_continuous_scale="Greens")
    fig_rec.update_layout(yaxis={'categoryorder':'total ascending'})
    col2.plotly_chart(fig_rec, use_container_width=True)
    
    # Distribuição de clientes
    st.subheader("📊 Concentração de Clientes")
    st.caption("Análise da concentração de faturamento entre clientes (Curva ABC).")
    
    df_abc = df_filtrado.groupby("cliente")["valor_venda"].sum().sort_values(ascending=False).reset_index()
    df_abc.columns = ["Cliente", "Faturamento"]
    df_abc["Percentual"] = (df_abc["Faturamento"] / df_abc["Faturamento"].sum() * 100)
    df_abc["Percentual Acumulado"] = df_abc["Percentual"].cumsum()
    df_abc["Classificação"] = df_abc["Percentual Acumulado"].apply(
        lambda x: "A (0-80%)" if x <= 80 else ("B (80-95%)" if x <= 95 else "C (95-100%)")
    )
    
    contagem_abc = df_abc["Classificação"].value_counts().reset_index()
    contagem_abc.columns = ["Classificação", "Quantidade de Clientes"]
    
    fig_abc = px.pie(contagem_abc, values="Quantidade de Clientes", names="Classificação",
                    title="Distribuição de Clientes por Curva ABC",
                    color="Classificação",
                    color_discrete_map={"A (0-80%)": "#2ecc71", "B (80-95%)": "#f39c12", "C (95-100%)": "#e74c3c"})
    st.plotly_chart(fig_abc, use_container_width=True)
    
    st.info("💡 **Curva ABC**: Clientes A representam 80% do faturamento, B os próximos 15%, e C os últimos 5%.")

with tab4:
    st.subheader("🏗 Análise de Soluções")
    st.caption("Desempenho de vendas por tipo de solução oferecida.")
    
    col1, col2 = st.columns(2)
    
    # Faturamento por tipo de solução
    df_tipo = (
        df_filtrado.groupby("tipo_solucao")["valor_venda"]
        .sum()
        .reset_index()
        .sort_values("valor_venda", ascending=False)
    )
    df_tipo.columns = ["Tipo de Solução", "Faturamento Total"]
    
    fig_tipo = px.bar(df_tipo, x="Tipo de Solução", y="Faturamento Total",
                     title="Faturamento por Tipo de Solução",
                     labels={"Tipo de Solução": "Tipo de Solução", 
                            "Faturamento Total": "Faturamento (R$)"},
                     color="Faturamento Total",
                     color_continuous_scale="Viridis")
    fig_tipo.update_layout(xaxis_tickangle=-45)
    fig_tipo.update_traces(hovertemplate='<b>%{x}</b><br>Faturamento: R$ %{y:,.2f}<extra></extra>')
    fig_tipo = formatar_eixo_reais(fig_tipo, 'y')
    col1.plotly_chart(fig_tipo, use_container_width=True)
    
    # Quantidade por tipo
    df_tipo_qtd = df_filtrado.groupby("tipo_solucao").size().reset_index(name="Quantidade")
    df_tipo_qtd.columns = ["Tipo de Solução", "Quantidade de Vendas"]
    df_tipo_qtd = df_tipo_qtd.sort_values("Quantidade de Vendas", ascending=False)
    
    fig_tipo_qtd = px.bar(df_tipo_qtd, x="Tipo de Solução", y="Quantidade de Vendas",
                         title="Quantidade de Vendas por Tipo de Solução",
                         labels={"Tipo de Solução": "Tipo de Solução", 
                                "Quantidade de Vendas": "Nº de Vendas"},
                         color="Quantidade de Vendas",
                         color_continuous_scale="Teal")
    fig_tipo_qtd.update_layout(xaxis_tickangle=-45)
    col2.plotly_chart(fig_tipo_qtd, use_container_width=True)
    
    # Evolução por tipo de solução
    st.subheader("📈 Evolução por Tipo de Solução")
    st.caption("Acompanhe a performance de cada tipo de solução ao longo do tempo.")
    
    df_tipo_tempo = df_filtrado.groupby(["ano_mes", "tipo_solucao"])["valor_venda"].sum().reset_index()
    df_tipo_tempo.columns = ["Período", "Tipo de Solução", "Faturamento"]
    
    fig_tipo_tempo = px.line(df_tipo_tempo, x="Período", y="Faturamento", 
                             color="Tipo de Solução",
                             title="Evolução do Faturamento por Tipo de Solução",
                             labels={"Período": "Período (Ano-Mês)", 
                                    "Faturamento": "Faturamento (R$)",
                                    "Tipo de Solução": "Tipo"},
                             markers=True)
    fig_tipo_tempo.update_traces(hovertemplate='<b>%{fullData.name}</b><br>Período: %{x}<br>Faturamento: R$ %{y:,.2f}<extra></extra>')
    fig_tipo_tempo = formatar_eixo_reais(fig_tipo_tempo, 'y')
    st.plotly_chart(fig_tipo_tempo, use_container_width=True)

with tab5:
    st.subheader("📋 Detalhamento Completo das Vendas")
    st.caption("Tabela com todas as vendas do período filtrado. Use os filtros laterais para refinar a visualização.")
    
    # Preparar dataframe para exibição
    df_display = df_filtrado[[
        "data_venda",
        "data_nf",
        "cliente",
        "vendedor",
        "tipo_solucao",
        "descricao_projeto",
        "valor_venda",
        "lead_time",
        "os",
        "proposta"
    ]].sort_values("data_venda", ascending=False).copy()
    
    # Renomear colunas para exibição
    df_display.columns = [
        "Data da Venda",
        "Data da NF",
        "Cliente",
        "Vendedor",
        "Tipo de Solução",
        "Descrição do Projeto",
        "Valor (R$)",
        "Ciclo (dias)",
        "OS",
        "Proposta"
    ]
    
    st.dataframe(df_display, use_container_width=True, height=400)
    
    # Botão de export
    st.markdown("<br>", unsafe_allow_html=True)
    col_export1, col_export2, col_export3 = st.columns([2, 1, 2])
    with col_export2:
        if st.button("📥 Exportar Dados Filtrados", use_container_width=True):
            csv = df_display.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="⬇️ Download CSV",
                data=csv,
                file_name=f"vendas_arv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )

# ============================================================
# INSIGHTS AUTOMÁTICOS
# ============================================================
st.markdown("<hr>", unsafe_allow_html=True)
st.subheader("💡 Insights Automáticos")
st.caption("Destaques principais baseados nos dados filtrados:")

col_ins1, col_ins2, col_ins3, col_ins4 = st.columns(4)

# Melhor vendedor
melhor_vendedor = df_vend.iloc[0]
col_ins1.info(f"🏆 **Melhor Vendedor**\n\n{melhor_vendedor['Vendedor']}\n\n**{formatar_reais(melhor_vendedor['Faturamento Total'])}**")

# Melhor cliente
melhor_cliente = df_cliente.iloc[0]
col_ins2.success(f"👑 **Maior Cliente**\n\n{melhor_cliente['Cliente']}\n\n**{formatar_reais(melhor_cliente['Faturamento Total'])}**")

# Solução mais vendida
sol_mais_vendida = df_tipo.iloc[0]
col_ins3.info(f"🏗 **Solução Mais Vendida**\n\n{sol_mais_vendida['Tipo de Solução']}\n\n**{formatar_reais(sol_mais_vendida['Faturamento Total'])}**")

# Taxa de crescimento (se houver dados de múltiplos meses)
if len(df_mes) >= 2:
    crescimento = ((df_mes.iloc[-1]["Faturamento"] - df_mes.iloc[-2]["Faturamento"]) / 
                   df_mes.iloc[-2]["Faturamento"] * 100)
    if crescimento > 0:
        col_ins4.success(f"📈 **Crescimento Mensal**\n\n+{crescimento:.1f}%\n\nrelativo ao mês anterior")
    else:
        col_ins4.warning(f"📉 **Variação Mensal**\n\n{crescimento:.1f}%\n\nrelativo ao mês anterior")
else:
    col_ins4.info("📊 **Período Único**\n\nDados insuficientes para calcular crescimento")