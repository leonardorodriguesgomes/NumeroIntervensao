import streamlit as st
import pandas as pd

# Sidebar - Upload com senha
st.sidebar.title("Controle de Intervenções")
password = st.sidebar.text_input("Senha", type="password")
if password == "Ecovias123":
    uploaded_file = st.sidebar.file_uploader("Upload da planilha (.xlsx)", type=["xlsx"])
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        st.session_state['df'] = df
        st.sidebar.success("Arquivo carregado com sucesso!")
else:
    st.sidebar.warning("Digite a senha para habilitar o upload.")

st.title("Dashboard de Intervenções")

# Campo para buscar número(s)
numeros = st.text_area("Digite os números de intervenção (um por linha):")

if st.button("Buscar"):
    if 'df' in st.session_state:
        df = st.session_state['df']
        numeros_lista = [n.strip() for n in numeros.split("\n") if n.strip() != ""]
        resultados = df[df["Num Interv"].astype(str).isin(numeros_lista)]
        if not resultados.empty:
            st.write("### Resultados encontrados:")
            st.dataframe(resultados)
        else:
            st.warning("Nenhum resultado encontrado.")
    else:
        st.error("Por favor, carregue um arquivo válido primeiro.")
