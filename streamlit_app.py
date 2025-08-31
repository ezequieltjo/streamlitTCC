import streamlit as st
import pandas as pd
import numpy as np
import time
import csv
from PIL import Image

if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = 'home'

# --- BARRA LATERAL COM BOTÕES ---
with st.sidebar:
    st.header("Menu")
    
    # Atualiza o estado da sessão com base no botão clicado
    if st.button("Início", use_container_width=True):
        st.session_state.pagina_atual = 'home'

    if st.button("Configurações", use_container_width=True):
        st.session_state.pagina_atual = 'config'

    if st.button("Informações", use_container_width=True):
        st.session_state.pagina_atual = 'info'
        
    st.info("Projeto de Trabalho de Conclusão de Curso do discente Ezequiel Teotônio Jó.")

# --- DECLARAÇÃO DAS PÁGINAS ---
if st.session_state.pagina_atual == "home":

    st.set_page_config(
        page_title="Otimização da Alocação de Tutores CODE",
        page_icon="🧑🏽‍💻",
        layout="wide" 
    )

    col1, col2, col3 = st.columns([1, 3, 1])

    with col2:
        # Adicionando imagem do projeto CODE
        try:
            banner = Image.open("code-programacao.png")
            st.image(banner, use_container_width=True)
        except FileNotFoundError:
            st.error("Imagem do projeto não encontrada!")

        st.markdown("<h1 style='text-align: center; color: #eb8334;'>Otimização da Alocação de Tutores CODE</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Uma ferramenta que otimiza a alocação dos tutores às escolas do projeto.</p>", unsafe_allow_html=True)
        #st.markdown("<p style='text-align: center;'>Projeto de Trabalho de Conclusão de Curso do discente Ezequiel Teotônio Jó.</p>", unsafe_allow_html=True)

        # Simulação de um processo de otimização   
        if st.button("Otimizar", use_container_width=True):
            st.success("Otimização iniciada!", icon="🚀")
            time.sleep(2)  # Simula o tempo de processamento
            st.success("Otimização concluída!", icon="✅")
            
            # Exibir resultados simulados no arquivo 'resultados.csv'
            st.subheader("Resultados da Otimização")
            try:
                alocacao = pd.read_csv("alocacoes.csv")
                st.dataframe(alocacao)
            except FileNotFoundError:
                st.error("Arquivo 'alocacoes.csv' não encontrado!")




    

if st.session_state.pagina_atual == "config":
    st.set_page_config(
        page_title="Configurações - Otimização CODE ",
        page_icon="🧑🏽‍💻",
        layout="wide" 
    )

    col1, col2, col3 = st.columns([1, 3, 1])

    st.markdown("<h1 style='text-align: center; color: #eb8334;'>Configurações</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Configure os parâmetros do algoritmo.</p>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Para mais informações consulte a página de Informações.</p>", unsafe_allow_html=True)
    
    pref1 = st.number_input("Pontuação da 1º Preferência de Escola:", min_value=0, icon="🥇")
    #st.write("Primeira Preferência:", pref1)

    pref2 = st.number_input("Pontuação da 2º Preferência Escola:", min_value=0, icon="🥈")
    #st.write("Primeira Preferência:", pref2)

    pref3 = st.number_input("Pontuação da 3º Preferência Escola:", min_value=0, icon="🥉")
    #st.write("Primeira Preferência:", pref3)

    baseDistancia = st.number_input("Pontuação Base da Preferência por Distâncias:", min_value=0, icon="🗺️")

    baseRanking = st.number_input("Pontuação Base para o Ranking dos Tutores:", min_value=0, icon="🏆")

    

    st.write("Configurações: ", pref1, "/", pref2, "/", pref3, "/", baseDistancia, "/", baseRanking)

if st.session_state.pagina_atual == "info":
    st.set_page_config(
        page_title="Informações - Otimização CODE ",
        page_icon="🧑🏽‍💻",
        layout="wide" 
    )

    col1, col2, col3 = st.columns([1, 3, 1])