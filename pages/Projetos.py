import streamlit as st
import pandas as pd
import plotly.express as px

# ============================================================
# CONFIGURAÇÕES
# ============================================================
HORAS_MES = 176  # Jornada base padrão
st.set_page_config(page_title="Performance Engenharia", layout="wide")
st.title("🔨 Dashboard de Engenharia")


# ============================================================
# 1. CARREGAMENTO DOS DADOS
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
        "Equipe": "departamento",
        "pontualidade": "pontualidade",
        "Mês": "mes"
    })

    df["duracao"] = df["duracao"].fillna(0).astype(float)
    df["horas_produzidas"] = df["duracao"]

    df["data_conclusao"] = pd.to_datetime(df["data_conclusao"], errors="coerce")
    df["ano_mes"] = df["data_conclusao"].dt.to_period("M").astype(str)

    df["pontualidade"] = df["pontualidade"].fillna(0).astype(float) * 100

    return df


df = load_data()


# ============================================================
# 2. FILTROS LATERAIS
# ============================================================
st.sidebar.header("Filtros")

departamentos = sorted(df["departamento"].dropna().unique())
usuarios = sorted(df["responsavel"].dropna().unique())

deps_sel = st.sidebar.multiselect("Departamentos", departamentos, default=departamentos)
users_sel = st.sidebar.multiselect("Usuários", usuarios)

df_f = df[df["departamento"].isin(deps_sel)]

modo_usuario = len(users_sel) > 0


# ============================================================
# 3. PRODUTIVIDADE MENSAL POR USUÁRIO
# ============================================================
prod_user = (
    df_f.groupby(["departamento", "responsavel", "ano_mes"])["horas_produzidas"]
    .sum()
    .reset_index()
)

prod_user["produtividade_user_mes"] = (
    prod_user["horas_produzidas"] / HORAS_MES * 100
)


# ============================================================
# 4. PRODUTIVIDADE MENSAL POR DEPARTAMENTO (MÉDIA DOS USUÁRIOS)
# ============================================================
prod_depto = (
    prod_user.groupby(["departamento", "ano_mes"])["produtividade_user_mes"]
    .mean()
    .reset_index()
    .rename(columns={"produtividade_user_mes": "produtividade_depto"})
)


# ============================================================
# 5. PRODUTIVIDADE INDIVIDUAL ACUMULADA (CORRETÍSSIMA)
# ============================================================
num_meses_periodo = df_f["ano_mes"].nunique()

prod_pessoa_total = (
    df_f.groupby("responsavel")["horas_produzidas"]
    .sum()
    .reset_index()
)

prod_pessoa_total["produtividade_user"] = (
    prod_pessoa_total["horas_produzidas"] /
    (HORAS_MES * num_meses_periodo) * 100
)

prod_pessoa_total = prod_pessoa_total.sort_values("produtividade_user")


# ============================================================
# 6. KPIs GERAIS
# ============================================================
df_kpi = df_f if not modo_usuario else df[df["responsavel"].isin(users_sel)]

total_tarefas = df_kpi[df_kpi["status"] == "Feito"].shape[0]
media_pontualidade = df_kpi["pontualidade"].mean()
media_produtividade = prod_pessoa_total["produtividade_user"].mean()

c1, c2, c3 = st.columns(3)
c1.metric("🧱 Tarefas Concluídas", total_tarefas)
c2.metric("⏱ Média de Pontualidade", f"{media_pontualidade:.2f}%")
c3.metric("⚙ Produtividade Média", f"{media_produtividade:.2f}%")

st.markdown("<hr>", unsafe_allow_html=True)


# ============================================================
# 7. MODO USUÁRIO
# ============================================================
if modo_usuario:
    st.markdown("## 👤 Análise por Usuário")

    for user in users_sel:
        st.markdown(f"### 👨‍🔧 {user}")

        df_u = prod_user[prod_user["responsavel"] == user]

        fig = px.line(
            df_u,
            x="ano_mes",
            y="produtividade_user_mes",
            title=f"Produtividade Mensal — {user}",
            markers=True,
            color_discrete_sequence=["#2980b9"]
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

    st.stop()


# ============================================================
# 8. MODO DEPARTAMENTO
# ============================================================
st.markdown("## 🧰 Análise por Departamento")

for dep in deps_sel:
    st.markdown(f"### 🧱 {dep}")

    df_dep = df_f[df_f["departamento"] == dep]
    df_dep_prod = prod_depto[prod_depto["departamento"] == dep]

    tarefas_mes = (
        df_dep[df_dep["status"] == "Feito"]
        .groupby("ano_mes").size()
        .reset_index(name="tarefas")
    )

    pont_mes = df_dep.groupby("ano_mes")["pontualidade"].mean().reset_index()

    col1, col2, col3 = st.columns(3)

    fig_t = px.bar(
        tarefas_mes,
        x="ano_mes",
        y="tarefas",
        title="Tarefas Concluídas",
        color_discrete_sequence=["#2ecc71"]
    )
    col1.plotly_chart(fig_t, use_container_width=True)

    fig_p = px.line(
        pont_mes,
        x="ano_mes",
        y="pontualidade",
        title="Pontualidade (%)",
        markers=True,
        color_discrete_sequence=["#9b59b6"]
    )
    col2.plotly_chart(fig_p, use_container_width=True)

    fig_pr = px.line(
        df_dep_prod,
        x="ano_mes",
        y="produtividade_depto",
        title="Produtividade (%)",
        markers=True,
        color_discrete_sequence=["#3498db"]
    )
    col3.plotly_chart(fig_pr, use_container_width=True)

    st.markdown("#### 👤 Produtividade Individual Acumulada")

    df_people = prod_pessoa_total.merge(
        df_f[["responsavel", "departamento"]].drop_duplicates(),
        on="responsavel"
    )

    df_people = df_people[df_people["departamento"] == dep]
    df_people = df_people.sort_values("produtividade_user")

    fig_ind = px.bar(
        df_people,
        x="produtividade_user",
        y="responsavel",
        orientation="h",
        title="Produtividade Individual (%)",
        color_discrete_sequence=["#e67e22"]
    )
    st.plotly_chart(fig_ind, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)
