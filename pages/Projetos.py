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
        "Eduardo Ruiz Barrichielo",
        "Almir",
        "Thiago Verzinhace",
        "Sergio da Silva Branco",
        "Andre Magni",
        "Felipe Amaral",
        "Rodrigo Camargo Vieira",
        "Gustavo Umebayashi sasagima",
        "Alisson sabino"
    ],
    "Engenharia Mecânica": [
        "Henrique Komoto",
        "Pedro Julio Marques da Silva",
        "Lucas Mantovani",
        "Dario Pereira",
        "Vinicius Correia",
        "Mauricio Machado",
    ],
    "Engenharia Elétrica": [
        "Jean Ribeiro",
        "Ruan Gonçalves de Jesus",
        "Jonatas Silva",
        "Gabriel Marcondes de Siqueira",
        "Fabricio Carvalho",
        "Lucas Nascimento",
        "Saulo",
    ],
    "Compras": [
        "Viviane Domingues",
        "Cintia Olívia",
        "Kaique Gabriel"
    ],
    "Terceiros": [
        "Terceiros Engenharia Elétrica",
        "Terceiros Programação",
        "Terceiros Instalação Mecânica",
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
# 3. KPIs APRIMORADOS COM EXPLICAÇÕES
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

with c1:
    st.metric("🧱 Tarefas Concluídas", f"{total_tarefas}")
    with st.expander("ℹ️ Explicação"):
        st.write("**Total de tarefas** finalizadas no período selecionado.")

with c2:
    st.metric("⏱ Horas Produzidas", f"{total_horas:.1f} h")
    with st.expander("ℹ️ Explicação"):
        st.write("**Soma das durações** de todas as tarefas concluídas. Representa o esforço total investido pela equipe.")

with c3:
    st.metric("📅 Atraso Médio", f"{atraso_medio:.1f} dias")
    with st.expander("ℹ️ Explicação"):
        st.write("**Diferença média** entre a data de conclusão e o prazo estabelecido. Valores negativos indicam adiantamento.")

with c4:
    st.metric("✅ Taxa de Pontualidade", f"{taxa_pontualidade:.1f}%")
    with st.expander("ℹ️ Explicação"):
        st.write("**Percentual de tarefas** entregues dentro do prazo ou antes. Meta ideal: acima de 80%.")

with c5:
    st.metric("⚙ Ocupação Global", f"{ocupacao_global:.1f}%" if not np.isnan(ocupacao_global) else "N/A")
    with st.expander("ℹ️ Explicação"):
        st.write(f"**Utilização da capacidade** do time. Calculado considerando {HORAS_MES_REFERENCIA}h/mês por pessoa. 100% = capacidade total utilizada.")

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
    st.caption("Visualize o volume de trabalho distribuído entre as equipes e a evolução temporal da produtividade.")
    
    col_a, col_b = st.columns(2)
    
    # Horas por equipe
    prod_eq = df_f.groupby("equipe")["duracao"].sum().reset_index().sort_values("duracao", ascending=False)
    tarefas_eq = df_f.groupby("equipe").size().reset_index(name="qtd_tarefas")
    prod_eq = prod_eq.merge(tarefas_eq, on="equipe")
    
    fig_eq = make_subplots(specs=[[{"secondary_y": True}]])
    fig_eq.add_trace(go.Bar(x=prod_eq["equipe"], y=prod_eq["duracao"], 
                            name="Horas Produzidas", marker_color='lightblue'))
    fig_eq.add_trace(go.Scatter(x=prod_eq["equipe"], y=prod_eq["qtd_tarefas"], 
                                name="Quantidade de Tarefas", 
                                mode='lines+markers', marker_color='orange'), secondary_y=True)
    fig_eq.update_layout(title="Produção por Equipe", height=400, hovermode='x unified')
    fig_eq.update_xaxes(title_text="Equipe")
    fig_eq.update_yaxes(title_text="Horas Produzidas", secondary_y=False)
    fig_eq.update_yaxes(title_text="Quantidade de Tarefas", secondary_y=True)
    col_a.plotly_chart(fig_eq, use_container_width=True)
    
    # Evolução mensal
    evolucao = df_f.groupby("ano_mes").agg({
        "duracao": "sum",
        "tarefa": "count"
    }).reset_index().rename(columns={"tarefa": "qtd_tarefas"})
    
    fig_ev = make_subplots(specs=[[{"secondary_y": True}]])
    fig_ev.add_trace(go.Bar(x=evolucao["ano_mes"], y=evolucao["duracao"], 
                            name="Horas Produzidas", marker_color='lightgreen'))
    fig_ev.add_trace(go.Scatter(x=evolucao["ano_mes"], y=evolucao["qtd_tarefas"], 
                                name="Quantidade de Tarefas", 
                                mode='lines+markers', marker_color='red'), secondary_y=True)
    fig_ev.update_layout(title="Evolução Mensal da Produção", height=400, hovermode='x unified')
    fig_ev.update_xaxes(title_text="Período (Ano-Mês)")
    fig_ev.update_yaxes(title_text="Horas Produzidas", secondary_y=False)
    fig_ev.update_yaxes(title_text="Quantidade de Tarefas", secondary_y=True)
    col_b.plotly_chart(fig_ev, use_container_width=True)
    
    # Distribuição por faixa de duração
    st.subheader("⏳ Distribuição de Tarefas por Duração")
    st.caption("Entenda como as tarefas se distribuem por complexidade (tempo de execução).")
    dist_duracao = df_f.groupby("faixa_duracao").size().reset_index(name="quantidade")
    fig_dist = px.pie(dist_duracao, values="quantidade", names="faixa_duracao", 
                      title="Tarefas por Faixa de Duração",
                      labels={"faixa_duracao": "Faixa de Duração", "quantidade": "Quantidade de Tarefas"})
    st.plotly_chart(fig_dist, use_container_width=True)

with tab2:
    st.subheader("🏅 Performance Individual")
    st.caption("Rankings de produtividade e eficiência dos colaboradores no período selecionado.")
    
    col1, col2 = st.columns(2)
    
    # Ranking de horas
    horas_user = df_f.groupby("responsavel")["duracao"].sum().reset_index().sort_values("duracao", ascending=False)
    horas_user.columns = ["Responsável", "Total de Horas"]
    fig_hu = px.bar(horas_user.head(15), y="Responsável", x="Total de Horas", orientation="h",
                    title="Top 15 - Horas Produzidas", color="Total de Horas", 
                    color_continuous_scale="Blues",
                    labels={"Total de Horas": "Horas Produzidas", "Responsável": "Colaborador"})
    fig_hu.update_layout(yaxis={'categoryorder':'total ascending'})
    col1.plotly_chart(fig_hu, use_container_width=True)
    
    # Ranking de tarefas
    tasks_user = df_f.groupby("responsavel").size().reset_index(name="qtd_tarefas").sort_values("qtd_tarefas", ascending=False)
    tasks_user.columns = ["Responsável", "Total de Tarefas"]
    fig_tu = px.bar(tasks_user.head(15), y="Responsável", x="Total de Tarefas", orientation="h",
                    title="Top 15 - Quantidade de Tarefas", color="Total de Tarefas", 
                    color_continuous_scale="Greens",
                    labels={"Total de Tarefas": "Tarefas Concluídas", "Responsável": "Colaborador"})
    fig_tu.update_layout(yaxis={'categoryorder':'total ascending'})
    col2.plotly_chart(fig_tu, use_container_width=True)
    
    # Análise de eficiência (horas/tarefa)
    st.subheader("📊 Eficiência por Pessoa")
    st.caption("Média de horas dedicadas por tarefa. Valores mais altos podem indicar tarefas mais complexas ou necessidade de otimização.")
    eficiencia = df_f.groupby("responsavel").agg({
        "duracao": "sum",
        "tarefa": "count"
    }).reset_index()
    eficiencia.columns = ["Responsável", "Total de Horas", "Total de Tarefas"]
    eficiencia["Horas por Tarefa"] = eficiencia["Total de Horas"] / eficiencia["Total de Tarefas"]
    eficiencia = eficiencia.sort_values("Horas por Tarefa", ascending=False)
    
    fig_ef = px.bar(eficiencia.head(15), y="Responsável", x="Horas por Tarefa", orientation="h",
                    title="Média de Horas por Tarefa (Top 15)", color="Horas por Tarefa",
                    color_continuous_scale="Oranges",
                    labels={"Horas por Tarefa": "Média de Horas/Tarefa", "Responsável": "Colaborador"})
    fig_ef.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_ef, use_container_width=True)

with tab3:
    st.subheader("⏳ Análise de Prazo e Pontualidade")
    st.caption("Avalie o cumprimento de prazos e identifique padrões de atraso ou adiantamento.")
    
    col1, col2 = st.columns(2)
    
    # Distribuição de atraso
    fig_hist = px.histogram(df_f, x="dias_atraso", nbins=30, 
                           title="Distribuição de Atraso nas Entregas",
                           color_discrete_sequence=['indianred'],
                           labels={"dias_atraso": "Dias de Atraso (negativo = adiantado)", 
                                   "count": "Quantidade de Tarefas"})
    fig_hist.add_vline(x=0, line_dash="dash", line_color="green", 
                      annotation_text="Prazo Exato", annotation_position="top")
    col1.plotly_chart(fig_hist, use_container_width=True)
    
    # Taxa de pontualidade por equipe
    pont_eq = df_f.groupby("equipe").agg({
        "no_prazo": lambda x: (x.sum() / len(x) * 100)
    }).reset_index()
    pont_eq.columns = ["Equipe", "Taxa de Pontualidade (%)"]
    
    fig_pont = px.bar(pont_eq, x="Equipe", y="Taxa de Pontualidade (%)",
                     title="Taxa de Pontualidade por Equipe",
                     color="Taxa de Pontualidade (%)", color_continuous_scale="RdYlGn",
                     labels={"Equipe": "Equipe", "Taxa de Pontualidade (%)": "Pontualidade (%)"})
    fig_pont.add_hline(y=80, line_dash="dash", line_color="orange", 
                      annotation_text="Meta: 80%", annotation_position="right")
    col2.plotly_chart(fig_pont, use_container_width=True)
    
    # Top 10 pessoas mais pontuais
    st.subheader("🎯 Top 10 Colaboradores Mais Pontuais")
    st.caption("Classificação dos colaboradores com melhor taxa de entrega no prazo (mínimo de 5 tarefas).")
    pont_user = df_f.groupby("responsavel").agg({
        "no_prazo": lambda x: (x.sum() / len(x) * 100),
        "tarefa": "count"
    }).reset_index()
    pont_user.columns = ["Responsável", "Taxa de Pontualidade (%)", "Total de Tarefas"]
    pont_user = pont_user[pont_user["Total de Tarefas"] >= 5].sort_values("Taxa de Pontualidade (%)", ascending=False)
    
    fig_top_pont = px.bar(pont_user.head(10), y="Responsável", x="Taxa de Pontualidade (%)",
                         orientation="h", title="Top 10 Mais Pontuais",
                         color="Taxa de Pontualidade (%)", color_continuous_scale="Greens",
                         labels={"Taxa de Pontualidade (%)": "Pontualidade (%)", 
                                "Responsável": "Colaborador"})
    fig_top_pont.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_top_pont, use_container_width=True)

with tab4:
    st.subheader("🔥 Análise de Carga de Trabalho")
    st.caption("Identifique sobrecarga e distribuição de trabalho ao longo do tempo.")
    
    # Heatmap
    pivot_carga = df_f.pivot_table(index="responsavel", columns="ano_mes", 
                                   values="duracao", aggfunc="sum", fill_value=0)
    
    fig_heat = px.imshow(pivot_carga, aspect="auto",
                        labels=dict(x="Período (Ano-Mês)", y="Colaborador", color="Horas Trabalhadas"),
                        title="Heatmap de Carga de Trabalho (Horas por Colaborador x Mês)",
                        color_continuous_scale="YlOrRd")
    st.plotly_chart(fig_heat, use_container_width=True)
    
    # Ocupação da capacidade
    st.subheader("⚙ Ocupação da Capacidade por Colaborador")
    st.caption(f"Percentual de utilização da capacidade mensal ({HORAS_MES_REFERENCIA}h/mês). Valores acima de 100% indicam sobrecarga.")
    user_month = df_f.groupby(["responsavel", "ano_mes"])["duracao"].sum().reset_index()
    user_month["ocupacao_mes"] = user_month["duracao"] / HORAS_MES_REFERENCIA * 100
    ocupacao_user = user_month.groupby("responsavel")["ocupacao_mes"].mean().reset_index()
    ocupacao_user.columns = ["Responsável", "Ocupação Média (%)"]
    ocupacao_user = ocupacao_user.sort_values("Ocupação Média (%)", ascending=False)
    
    fig_oc = px.bar(ocupacao_user, y="Responsável", x="Ocupação Média (%)", orientation="h",
                   title="Ocupação Média da Capacidade por Colaborador",
                   color="Ocupação Média (%)", color_continuous_scale="RdYlGn_r",
                   labels={"Ocupação Média (%)": "Ocupação (%)", "Responsável": "Colaborador"})
    fig_oc.add_vline(x=100, line_dash="dash", line_color="red", 
                    annotation_text="100% Capacidade", annotation_position="top")
    fig_oc.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_oc, use_container_width=True)

with tab5:
    st.subheader("📈 Tendências e Insights")
    st.caption("Acompanhe a evolução dos principais indicadores ao longo do tempo e identifique correlações.")
    
    # Evolução da pontualidade
    pont_mes = df_f.groupby("ano_mes").agg({
        "no_prazo": lambda x: (x.sum() / len(x) * 100)
    }).reset_index()
    pont_mes.columns = ["Período", "Taxa de Pontualidade (%)"]
    
    fig_tend_pont = px.line(pont_mes, x="Período", y="Taxa de Pontualidade (%)",
                           title="Evolução da Pontualidade ao Longo do Tempo",
                           markers=True,
                           labels={"Período": "Período (Ano-Mês)", 
                                  "Taxa de Pontualidade (%)": "Pontualidade (%)"})
    fig_tend_pont.add_hline(y=80, line_dash="dash", line_color="green",
                           annotation_text="Meta: 80%", annotation_position="right")
    st.plotly_chart(fig_tend_pont, use_container_width=True)
    
    # Produtividade média (tarefas por pessoa por mês)
    prod_mes = df_f.groupby("ano_mes").agg({
        "tarefa": "count",
        "responsavel": "nunique"
    }).reset_index()
    prod_mes["tarefas_por_pessoa"] = prod_mes["tarefa"] / prod_mes["responsavel"]
    prod_mes.columns = ["Período", "Total de Tarefas", "Total de Pessoas", "Tarefas por Pessoa"]
    
    fig_prod = px.line(prod_mes, x="Período", y="Tarefas por Pessoa",
                      title="Produtividade Média (Tarefas por Pessoa por Mês)",
                      markers=True,
                      labels={"Período": "Período (Ano-Mês)", 
                             "Tarefas por Pessoa": "Média de Tarefas/Pessoa"})
    st.plotly_chart(fig_prod, use_container_width=True)
    
    # Correlação: duração x atraso
    st.subheader("🔍 Correlação: Duração vs Atraso")
    st.caption("Analise se tarefas mais longas tendem a atrasar mais. Cada ponto representa uma tarefa.")
    fig_scatter = px.scatter(df_f, x="duracao", y="dias_atraso", 
                            color="equipe", size="duracao",
                            title="Relação entre Duração da Tarefa e Dias de Atraso",
                            opacity=0.6,
                            labels={"duracao": "Duração da Tarefa (horas)", 
                                   "dias_atraso": "Dias de Atraso",
                                   "equipe": "Equipe"})
    fig_scatter.add_hline(y=0, line_dash="dash", line_color="gray", 
                         annotation_text="Sem Atraso", annotation_position="left")
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    # Estatísticas de correlação
    correlacao = df_f[["duracao", "dias_atraso"]].corr().iloc[0, 1]
    if correlacao > 0.3:
        interpretacao = "forte positiva - tarefas mais longas tendem a atrasar mais"
    elif correlacao > 0:
        interpretacao = "fraca positiva - leve tendência de atraso em tarefas longas"
    elif correlacao > -0.3:
        interpretacao = "fraca negativa - pouca relação entre duração e atraso"
    else:
        interpretacao = "forte negativa - tarefas mais longas tendem a ser entregues antes"
    
    st.info(f"📊 **Correlação**: {correlacao:.3f} ({interpretacao})")

# ============================================================
# SEÇÃO DE EXPORT E INSIGHTS
# ============================================================
st.markdown("<hr>", unsafe_allow_html=True)
st.subheader("💡 Insights Automáticos")
st.caption("Destaques principais baseados nos dados filtrados:")

col_ins1, col_ins2, col_ins3 = st.columns(3)

# Pessoa mais produtiva
mais_produtivo = horas_user.iloc[0]
col_ins1.info(f"🏆 **Colaborador Mais Produtivo**\n\n{mais_produtivo['Responsável']}\n\n**{mais_produtivo['Total de Horas']:.1f} horas** produzidas")

# Equipe com melhor pontualidade
melhor_pont = pont_eq.sort_values("Taxa de Pontualidade (%)", ascending=False).iloc[0]
col_ins2.success(f"✅ **Equipe Mais Pontual**\n\n{melhor_pont['Equipe']}\n\n**{melhor_pont['Taxa de Pontualidade (%)']:.1f}%** de pontualidade")

# Alerta de sobrecarga
sobrecarga = ocupacao_user[ocupacao_user["Ocupação Média (%)"] > 120]
if not sobrecarga.empty:
    col_ins3.warning(f"⚠️ **Alerta de Sobrecarga**\n\n**{len(sobrecarga)} colaborador(es)** operando acima de 120% da capacidade")
else:
    col_ins3.success(f"✅ **Carga Equilibrada**\n\nNenhum colaborador em sobrecarga crítica (>120%)")

# Botão de export
st.markdown("<br>", unsafe_allow_html=True)
col_export1, col_export2, col_export3 = st.columns([2, 1, 2])
with col_export2:
    if st.button("📥 Exportar Dados Filtrados", use_container_width=True):
        csv = df_f.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="⬇️ Download CSV",
            data=csv,
            file_name=f"dados_arv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )