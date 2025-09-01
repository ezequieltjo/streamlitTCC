import streamlit as st
import pandas as pd
import numpy as np
import time
import csv
from PIL import Image

st.set_page_config(
    page_title="Otimização da Alocação de Tutores CODE",
    page_icon="🧑🏽‍💻",
    layout="wide" 
    )

if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = 'home'

# --- BARRA LATERAL COM BOTÕES ---
with st.sidebar:
    st.header("Menu")
    
    # Atualiza o estado da sessão com base no botão clicado
    if st.button("Início", width="stretch"):
        st.session_state.pagina_atual = 'home'

    if st.button("Configurações", width="stretch"):
        st.session_state.pagina_atual = 'config'

    if st.button("Informações", width="stretch"):
        st.session_state.pagina_atual = 'info'
        
    st.info("Projeto de Trabalho de Conclusão de Curso do discente Ezequiel Teotônio Jó.")

# --- DECLARAÇÃO DAS PÁGINAS ---
if st.session_state.pagina_atual == "home":

    col1, col2, col3 = st.columns([1, 3, 1])

    with col2:
        # Adicionando imagem do projeto CODE
        try:
            banner = Image.open("code-programacao.png")
            st.image(banner, width="stretch")
        except FileNotFoundError:
            st.error("Imagem do projeto não encontrada!")

        st.markdown("<h1 style='text-align: center; color: #eb8334;'>Otimização da Alocação de Tutores CODE</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Uma ferramenta que otimiza a alocação dos tutores às escolas do projeto.</p>", unsafe_allow_html=True)
        #st.markdown("<p style='text-align: center;'>Projeto de Trabalho de Conclusão de Curso do discente Ezequiel Teotônio Jó.</p>", unsafe_allow_html=True)

        # Simulação de um processo de otimização   
        if st.button("Otimizar", width="content"):

            with st.spinner("Otimizando... Por favor, aguarde."):
                time.sleep(3)
                st.success("Otimização concluída!", icon="✅")
                    
            # Exibir resultados simulados no arquivo 'resultados.csv'
            st.subheader("Resultados da Otimização")
            try:
                alocacao = pd.read_csv("alocacoes.csv")
                st.dataframe(alocacao)
            except FileNotFoundError:
                st.error("Arquivo 'alocacoes.csv' não encontrado!")

if st.session_state.pagina_atual == "config":

    col1, col2, col3 = st.columns([1, 3, 1])

    st.markdown("<h1 style='text-align: center; color: #eb8334;'>Configurações</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Configure os parâmetros do algoritmo.</p>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Para mais informações consulte a página de Informações.</p>", unsafe_allow_html=True)
    
    pref1 = st.number_input("Pontuação da 1º Preferência de Escola:", min_value=0, value= 8000, icon="🥇")
    #st.write("Primeira Preferência:", pref1)

    pref2 = st.number_input("Pontuação da 2º Preferência Escola:", min_value=0, value= 7000, icon="🥈")
    #st.write("Primeira Preferência:", pref2)

    pref3 = st.number_input("Pontuação da 3º Preferência Escola:", min_value=0, value= 6000, icon="🥉")
    #st.write("Primeira Preferência:", pref3)

    baseDistance = st.number_input("Pontuação Base da Preferência por Distâncias:", min_value=0, value= 5000, icon="🗺️")

    baseRanking = st.number_input("Pontuação Base para o Ranking dos Tutores:", min_value=0, value= 1000000000, icon="🏆")

    decayType = 'sigmoid'

    st.markdown("###### Tipo de Decaimento da Pontuação por Distância:")
    # Cria um seletor de rádio na horizontal
    decayOptions = ['Sigmoide', 'Linear']
    decayType = st.radio(
        "Escolha o tipo de decaimento:", 
        options=decayOptions, 
        horizontal=True, 
        label_visibility="collapsed",
        width="stretch"
    )

    if decayType == 'Sigmoide':
        decayType = 'sigmoid'
    else:
        decayType = 'linear'

    sigmoidCurve = st.number_input("Escala de Inclinação da Curva Sigmoide:", min_value=0, value=2000, icon="📉")

    #st.write("Configurações: ", pref1, "/", pref2, "/", pref3, "/", baseDistance, "/", baseRanking, "/", decayType, "/", sigmoidCurve)


if st.session_state.pagina_atual == "info":

    col1, col2, col3 = st.columns([1, 3, 1])

    st.markdown("<h1 style='text-align: center; color: #eb8334;'>Informações</h1>", unsafe_allow_html=True)

    with col2:
        st.markdown("### Sobre o Projeto")
        st.markdown("""
        Este projeto visa otimizar a alocação de tutores às escolas do projeto CODE, utilizando um algoritmo que considera as preferências dos tutores, suas classificações e a distância até as escolas.
        """)

        st.markdown("### Parâmetros do Algoritmo")
        st.markdown("""
        - **Preferências dos Tutores:** Cada tutor pode indicar suas preferências por até três escolas. A pontuação atribuída a cada preferência pode ser configurada na página de Configurações.
        - **Distância até as Escolas:** A distância entre a localização do tutor e a escola influencia a pontuação. A pontuação base e o tipo de decaimento (sigmoide ou linear) podem ser ajustados.
        - **Classificação dos Tutores:** A classificação dos tutores no sistema CODE também afeta a pontuação. Uma pontuação base para o ranking pode ser definida.
        """)

        st.markdown("### Como Utilizar")
        st.markdown("""
        1. Navegue até a página de Configurações para ajustar os parâmetros do algoritmo conforme suas necessidades.
        2. Retorne à página inicial e clique no botão 'Otimizar' para executar o algoritmo de alocação.
        3. Após a conclusão, os resultados da otimização serão exibidos em uma tabela.
        """)