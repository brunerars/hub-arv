import streamlit as st

menu_inicial = st.Page("pages/Home.py", title = "HUB de Dados ARV", icon="🏠")
menu_projetos = st.Page("pages/Projetos.py", title="Engenharia", icon="🔨")
menu_vendas = st.Page("pages/Vendas.py", title="Vendas", icon="💰")

pg = st.navigation(
    {
        "Home" : [menu_inicial],
        "Dashboards":[menu_projetos, menu_vendas],
    }
)

pg.run()