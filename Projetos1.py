import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta

# ============================================================
# CONFIGURAÇÕES
# ============================================================
HORAS_MES_REFERENCIA = 176
HORAS_DIA_REFERENCIA = 8

st.set_page_config(page_title="Performance Times ARV - Tarefas de Projetos", layout="wide")
st.title("📊 Dashboard de Performance - Times ARV (Tarefas Concluídas)")

# ============================================================
# 1. CARREGAMENTO E TRATAMENTO DOS DADOS
# ============================================================
@st.cache_data
def load_data():
    df1 = pd.read_excel("data/TAREFAS-PROJETOS-JUN-AGOST.xlsx")
    df2 = pd.read_excel("data/TAREFAS-PROJETOS-SET-NOV.xlsx")
    df = pd.concat([df1, df2], ignore_index=True)

    df = df.rename(columns={
        "Name": "tarefa",
        "Dono": "responsavel",
        "Status": "status",
        "Prazo": "prazo",
        "Duração": "duracao",
        "Data de Conclusão": "data_conclusao",
        "Equipe": "equipe",
        "pontualidade": "pontualidade",
        "Mês": "mes_raw"
    })

    df["duracao"] = df["duracao"].fillna(0).astype(float)
    df["prazo"] = pd.to_datetime(df["prazo"], errors="coerce")
    df["data_conclusao"] = pd.to_datetime(df["data_conclusao"], errors="coerce")
    df["ano_mes"] = df["data_conclusao"].dt.to_period("M").astype(str)
    
    meses_nomes = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    df["mes_nome"] = df["data_conclusao"].dt.month.apply(lambda m: meses_nomes[m-1] if pd.notna(m) else None)
    df["ano"] = df["data_conclusao"].dt.year
    df["dias_atraso"] = (df["data_conclusao"] - df["prazo"]).dt.days
    df["status"] = df["status"].fillna("Feito")
    
    # Novas métricas
    df["semana_conclusao"] = df["data_conclusao"].dt.isocalendar().week
    df["dia_semana"] = df["data_conclusao"].dt.day_name()
    df["no_prazo"] = df["dias_atraso"] <= 0
    df["faixa_duracao"] = pd.cut(df["duracao"], bins=[0, 2, 8, 24, 40, float('inf')], 
                                  labels=['< 2h', '2-8h', '8-24h', '24-40h', '> 40h'])
    
    return df

df = load_data()

# ============================================================
# 2. FILTROS LATERAIS APRIMORADOS
# ============================================================
st.sidebar.header("🔍 Filtros")

# Mapeamento de pessoas por equipe
EQUIPES_PESSOAS = {
    "Manufatura": [
        "Eduardo Ruiz Sacchetto",
        "Alvair de Nascimento Andrade",
        "Thiago Augusto Vanzellotti Jr.",
        "Sergio da Silva Bianco",
        "André Jesus Hugo de Melo",
        "Felipe Jose do Amaral",
        "Rodrigo Camargo Vieira",
        "Gustavo Umebayashi sasagima",
    ],
    "Engenharia Mecânica": [
        "Henrique Kimoto",
        "Heloisa Dias Nunes Junior",
        "Cristhian Patrick",
        "Vinicius Bispo",
        "Lucas Eduardo Manfuvert Souza",
        "Gustavo Limaduqui Sciagglia",
        "Guilherme Marques da Silva",
        "Vinicius Correia",
    ],
    "Engenharia Elétrica": [
        "Lucas Emmanuel Modenese",
        "Ruan Gonçalves de Jesus",
        "Matheus Lopes",
        "Gabriel Marcondes de Siqueira",
        "Fabricio Lima de Carvalho",
        "Lucas Oliveira da Silva",
        "Catiele de Carvalho",
        "Saulo",
    ],
    "Compras": [
        "Viviane Domingues",
        "Cintia Olívia",
        "Kaique Gabriel",
    ]
}

# Filtro de equipe primeiro
st.sidebar.subheader("👥 Equipe")
todas_equipes = list(EQUIPES_PESSOAS.keys())
equipe_filtro = st.sidebar.multiselect(
    "Selecione as equipes",
    options=todas_equipes,
    default=todas_equipes
)

# Seleção de período
st.sidebar.subheader("📅 Período")
periodo_opcao = st.sidebar.radio("Tipo de Período", ["Ano-Mês", "Intervalo de Datas"])

if periodo_opcao == "Ano-Mês":
    meses = sorted(df["ano_mes"].dropna().unique())
    meses_sel = st.sidebar.multiselect("Período (Ano-Mês)", meses, default=meses)
    df_f = df[df["ano_mes"].isin(meses_sel)] if len(meses_sel) > 0 else df
else:
    data_min = df["data_conclusao"].min()
    data_max = df["data_conclusao"].max()
    data_inicio = st.sidebar.date_input("Data Início", data_min, min_value=data_min, max_value=data_max)
    data_fim = st.sidebar.date_input("Data Fim", data_max, min_value=data_min, max_value=data_max)
    df_f = df[(df["data_conclusao"] >= pd.Timestamp(data_inicio)) & 
              (df["data_conclusao"] <= pd.Timestamp(data_fim))]

# Filtra pessoas baseado nas equipes selecionadas
pessoas_equipes_sel = []
for eq in equipe_filtro:
    pessoas_equipes_sel.extend(EQUIPES_PESSOAS[eq])

# Filtro de pessoas (apenas as da equipe selecionada)
st.sidebar.subheader("🧑 Responsáveis")
usuarios_disponiveis = [u for u in sorted(df_f["responsavel"].dropna().unique()) 
                        if u in pessoas_equipes_sel or len(equipe_filtro) == 0]
users_sel = st.sidebar.multiselect("Selecione responsáveis específicos", usuarios_disponiveis)

# Filtros adicionais
st.sidebar.subheader("🔧 Filtros Avançados")
mostrar_atrasadas = st.sidebar.checkbox("Apenas tarefas atrasadas", False)
faixa_duracao_sel = st.sidebar.multiselect("Faixa de Duração", 
                                            df["faixa_duracao"].dropna().unique())

# Aplica filtros
# Filtro por equipe (usando o mapeamento)
if len(equipe_filtro) > 0:
    df_f = df_f[df_f["responsavel"].isin(pessoas_equipes_sel)]

# Filtro por pessoas específicas
if len(users_sel) > 0:
    df_f = df_f[df_f["responsavel"].isin(users_sel)]

# Outros filtros
if mostrar_atrasadas:
    df_f = df_f[df_f["dias_atraso"] > 0]
if len(faixa_duracao_sel) > 0:
    df_f = df_f[df_f["faixa_duracao"].isin(faixa_duracao_sel)]

if df_f.empty:
    st.warning("Nenhum dado encontrado com os filtros selecionados.")
    st.stop()

# ============================================================
# 3. KPIs APRIMORADOS
# ============================================================
total_tarefas = df_f.shape[0]
total_horas = df_f["duracao"].sum()
atraso_medio = df_f["dias_atraso"].mean()
taxa_pontualidade = (df_f["no_prazo"].sum() / total_tarefas * 100) if total_tarefas > 0 else 0

qtd_pessoas = df_f["responsavel"].nunique()
qtd_meses_periodo = df_f["ano_mes"].nunique()
capacidade_total = qtd_pessoas * qtd_meses_periodo * HORAS_MES_REFERENCIA
ocupacao_global = (total_horas / capacidade_total * 100) if capacidade_total > 0 else np.nan

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🧱 Tarefas Concluídas", f"{total_tarefas}")
c2.metric("⏱ Horas Produzidas", f"{total_horas:.1f} h")
c3.metric("📅 Atraso Médio", f"{atraso_medio:.1f} dias")
c4.metric("✅ Taxa de Pontualidade", f"{taxa_pontualidade:.1f}%")
c5.metric("⚙ Ocupação Global", f"{ocupacao_global:.1f}%" if not np.isnan(ocupacao_global) else "N/A")

st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================
# 4. TABS PARA ORGANIZAR VISUALIZAÇÕES
# ============================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Visão Geral", 
    "👥 Análise por Pessoa", 
    "⏱ Tempo & Prazo", 
    "🔥 Carga de Trabalho",
    "📈 Tendências"
])

with tab1:
    st.subheader("📦 Produção por Equipe e Mês")
    
    col_a, col_b = st.columns(2)
    
    # Horas por equipe
    prod_eq = df_f.groupby("equipe")["duracao"].sum().reset_index().sort_values("duracao", ascending=False)
    tarefas_eq = df_f.groupby("equipe").size().reset_index(name="qtd_tarefas")
    prod_eq = prod_eq.merge(tarefas_eq, on="equipe")
    
    fig_eq = make_subplots(specs=[[{"secondary_y": True}]])
    fig_eq.add_trace(go.Bar(x=prod_eq["equipe"], y=prod_eq["duracao"], name="Horas", marker_color='lightblue'))
    fig_eq.add_trace(go.Scatter(x=prod_eq["equipe"], y=prod_eq["qtd_tarefas"], name="Tarefas", 
                                 mode='lines+markers', marker_color='orange'), secondary_y=True)
    fig_eq.update_layout(title="Horas e Tarefas por Equipe", height=400)
    fig_eq.update_yaxes(title_text="Horas", secondary_y=False)
    fig_eq.update_yaxes(title_text="Tarefas", secondary_y=True)
    col_a.plotly_chart(fig_eq, use_container_width=True)
    
    # Evolução mensal
    evolucao = df_f.groupby("ano_mes").agg({
        "duracao": "sum",
        "tarefa": "count"
    }).reset_index().rename(columns={"tarefa": "qtd_tarefas"})
    
    fig_ev = make_subplots(specs=[[{"secondary_y": True}]])
    fig_ev.add_trace(go.Bar(x=evolucao["ano_mes"], y=evolucao["duracao"], name="Horas", marker_color='lightgreen'))
    fig_ev.add_trace(go.Scatter(x=evolucao["ano_mes"], y=evolucao["qtd_tarefas"], name="Tarefas", 
                                mode='lines+markers', marker_color='red'), secondary_y=True)
    fig_ev.update_layout(title="Evolução Mensal", height=400)
    col_b.plotly_chart(fig_ev, use_container_width=True)
    
    # Distribuição por faixa de duração
    st.subheader("⏳ Distribuição de Tarefas por Duração")
    dist_duracao = df_f.groupby("faixa_duracao").size().reset_index(name="qtd")
    fig_dist = px.pie(dist_duracao, values="qtd", names="faixa_duracao", 
                      title="Distribuição de Tarefas por Faixa de Duração")
    st.plotly_chart(fig_dist, use_container_width=True)

with tab2:
    st.subheader("🏅 Performance Individual")
    
    col1, col2 = st.columns(2)
    
    # Ranking de horas
    horas_user = df_f.groupby("responsavel")["duracao"].sum().reset_index().sort_values("duracao", ascending=False)
    fig_hu = px.bar(horas_user.head(15), x="duracao", y="responsavel", orientation="h",
                    title="Top 15 - Horas Produzidas", color="duracao", color_continuous_scale="Blues")
    col1.plotly_chart(fig_hu, use_container_width=True)
    
    # Ranking de tarefas
    tasks_user = df_f.groupby("responsavel").size().reset_index(name="qtd_tarefas").sort_values("qtd_tarefas", ascending=False)
    fig_tu = px.bar(tasks_user.head(15), x="qtd_tarefas", y="responsavel", orientation="h",
                    title="Top 15 - Quantidade de Tarefas", color="qtd_tarefas", color_continuous_scale="Greens")
    col2.plotly_chart(fig_tu, use_container_width=True)
    
    # Análise de eficiência (horas/tarefa)
    st.subheader("📊 Eficiência por Pessoa")
    eficiencia = df_f.groupby("responsavel").agg({
        "duracao": "sum",
        "tarefa": "count"
    }).reset_index()
    eficiencia.columns = ["responsavel", "total_horas", "total_tarefas"]
    eficiencia["horas_por_tarefa"] = eficiencia["total_horas"] / eficiencia["total_tarefas"]
    eficiencia = eficiencia.sort_values("horas_por_tarefa", ascending=False)
    
    fig_ef = px.bar(eficiencia.head(15), x="horas_por_tarefa", y="responsavel", orientation="h",
                    title="Média de Horas por Tarefa (Top 15)", color="horas_por_tarefa",
                    color_continuous_scale="Oranges")
    st.plotly_chart(fig_ef, use_container_width=True)

with tab3:
    st.subheader("⏳ Análise de Prazo e Pontualidade")
    
    col1, col2 = st.columns(2)
    
    # Distribuição de atraso
    fig_hist = px.histogram(df_f, x="dias_atraso", nbins=30, 
                           title="Distribuição de Atraso (dias)",
                           color_discrete_sequence=['indianred'])
    fig_hist.add_vline(x=0, line_dash="dash", line_color="green", annotation_text="No Prazo")
    col1.plotly_chart(fig_hist, use_container_width=True)
    
    # Taxa de pontualidade por equipe
    pont_eq = df_f.groupby("equipe").agg({
        "no_prazo": lambda x: (x.sum() / len(x) * 100)
    }).reset_index()
    pont_eq.columns = ["equipe", "taxa_pontualidade"]
    
    fig_pont = px.bar(pont_eq, x="equipe", y="taxa_pontualidade",
                     title="Taxa de Pontualidade por Equipe (%)",
                     color="taxa_pontualidade", color_continuous_scale="RdYlGn")
    fig_pont.add_hline(y=80, line_dash="dash", line_color="orange", annotation_text="Meta: 80%")
    col2.plotly_chart(fig_pont, use_container_width=True)
    
    # Top 10 pessoas mais pontuais
    st.subheader("🎯 Top 10 Mais Pontuais")
    pont_user = df_f.groupby("responsavel").agg({
        "no_prazo": lambda x: (x.sum() / len(x) * 100),
        "tarefa": "count"
    }).reset_index()
    pont_user.columns = ["responsavel", "taxa_pontualidade", "qtd_tarefas"]
    pont_user = pont_user[pont_user["qtd_tarefas"] >= 5].sort_values("taxa_pontualidade", ascending=False)
    
    fig_top_pont = px.bar(pont_user.head(10), x="taxa_pontualidade", y="responsavel",
                         orientation="h", title="Top 10 Mais Pontuais (mín. 5 tarefas)",
                         color="taxa_pontualidade", color_continuous_scale="Greens")
    st.plotly_chart(fig_top_pont, use_container_width=True)

with tab4:
    st.subheader("🔥 Análise de Carga de Trabalho")
    
    # Heatmap
    pivot_carga = df_f.pivot_table(index="responsavel", columns="ano_mes", 
                                   values="duracao", aggfunc="sum", fill_value=0)
    
    fig_heat = px.imshow(pivot_carga, aspect="auto",
                        labels=dict(x="Mês", y="Responsável", color="Horas"),
                        title="Heatmap de Horas por Pessoa x Mês",
                        color_continuous_scale="YlOrRd")
    st.plotly_chart(fig_heat, use_container_width=True)
    
    # Ocupação da capacidade
    st.subheader("⚙ Ocupação da Capacidade por Usuário")
    user_month = df_f.groupby(["responsavel", "ano_mes"])["duracao"].sum().reset_index()
    user_month["ocupacao_mes"] = user_month["duracao"] / HORAS_MES_REFERENCIA * 100
    ocupacao_user = user_month.groupby("responsavel")["ocupacao_mes"].mean().reset_index()
    ocupacao_user = ocupacao_user.sort_values("ocupacao_mes", ascending=False)
    
    fig_oc = px.bar(ocupacao_user, x="ocupacao_mes", y="responsavel", orientation="h",
                   title="Ocupação Média da Capacidade (%)",
                   color="ocupacao_mes", color_continuous_scale="RdYlGn_r")
    fig_oc.add_vline(x=100, line_dash="dash", line_color="red", annotation_text="100% Cap.")
    st.plotly_chart(fig_oc, use_container_width=True)
    
    st.caption("⚠ 100% = 176h/mês. Acima disso indica sobrecarga.")

with tab5:
    st.subheader("📈 Tendências e Insights")
    
    # Evolução da pontualidade
    pont_mes = df_f.groupby("ano_mes").agg({
        "no_prazo": lambda x: (x.sum() / len(x) * 100)
    }).reset_index()
    pont_mes.columns = ["ano_mes", "taxa_pontualidade"]
    
    fig_tend_pont = px.line(pont_mes, x="ano_mes", y="taxa_pontualidade",
                           title="Evolução da Taxa de Pontualidade ao Longo do Tempo",
                           markers=True)
    fig_tend_pont.add_hline(y=80, line_dash="dash", line_color="green")
    st.plotly_chart(fig_tend_pont, use_container_width=True)
    
    # Produtividade média (tarefas por pessoa por mês)
    prod_mes = df_f.groupby("ano_mes").agg({
        "tarefa": "count",
        "responsavel": "nunique"
    }).reset_index()
    prod_mes["tarefas_por_pessoa"] = prod_mes["tarefa"] / prod_mes["responsavel"]
    
    fig_prod = px.line(prod_mes, x="ano_mes", y="tarefas_por_pessoa",
                      title="Produtividade Média (Tarefas por Pessoa por Mês)",
                      markers=True)
    st.plotly_chart(fig_prod, use_container_width=True)
    
    # Correlação: duração x atraso
    st.subheader("🔍 Correlação: Duração vs Atraso")
    fig_scatter = px.scatter(df_f, x="duracao", y="dias_atraso", 
                            color="equipe", size="duracao",
                            title="Relação entre Duração e Atraso",
                            opacity=0.6)
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    # Estatísticas de correlação
    correlacao = df_f[["duracao", "dias_atraso"]].corr().iloc[0, 1]
    st.caption(f"📊 Correlação: {correlacao:.3f} {'(positiva)' if correlacao > 0 else '(negativa)'}")

# ============================================================
# SEÇÃO DE EXPORT E INSIGHTS
# ============================================================
st.markdown("<hr>", unsafe_allow_html=True)
st.subheader("💡 Insights Automáticos")

col_ins1, col_ins2, col_ins3 = st.columns(3)

# Pessoa mais produtiva
mais_produtivo = horas_user.iloc[0]
col_ins1.info(f"🏆 **Mais Produtivo**: {mais_produtivo['responsavel']} com {mais_produtivo['duracao']:.1f}h")

# Equipe com melhor pontualidade
melhor_pont = pont_eq.sort_values("taxa_pontualidade", ascending=False).iloc[0]
col_ins2.success(f"✅ **Melhor Pontualidade**: {melhor_pont['equipe']} com {melhor_pont['taxa_pontualidade']:.1f}%")

# Alerta de sobrecarga
sobrecarga = ocupacao_user[ocupacao_user["ocupacao_mes"] > 120]
if not sobrecarga.empty:
    col_ins3.warning(f"⚠️ **{len(sobrecarga)} pessoa(s)** em sobrecarga (>120%)")
else:
    col_ins3.success("✅ Nenhuma pessoa em sobrecarga crítica")

# Botão de export
if st.button("📥 Exportar Dados Filtrados para CSV"):
    csv = df_f.to_csv(index=False)
    st.download_button("Download CSV", csv, "dados_filtrados.csv", "text/csv")