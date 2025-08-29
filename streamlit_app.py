import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="Otimização CODE",
    page_icon="🧑🏽‍💻",
    layout="wide" 
)

col1, col2, col3 = st.columns([1, 3, 1])

with col2:
    # Adicionando imagem do projeto CODE
    try:
        imgProjeto = Image.open("code-programacao.png")
        st.image(imgProjeto, use_container_width=True)
    except FileNotFoundError:
        st.error("Imagem do projeto não encontrada!")

    st.markdown("<h1 style='text-align: center; color: #da21ff;'>Otimização CODE</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Uma ferramenta que otimiza a alocação dos tutores às escolas do projeto.</p>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Projeto de Trabalho de Conclusão de Curso do discente Ezequiel Teotônio Jó.</p>", unsafe_allow_html=True)

