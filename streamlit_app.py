import io
import streamlit as st
from PIL import Image
import optimization as opt
import metrics as met

st.set_page_config(
    page_title="Otimização da Alocação de Tutores CODE",
    page_icon="🧑🏽‍💻",
    layout="wide" 
    )

# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'home'

if 'optimization_done' not in st.session_state:
    st.session_state.optimization_done = False

if 'optimization_result' not in st.session_state:
    st.session_state.optimization_result = None

if 'saved_config' not in st.session_state:
    st.session_state.saved_config = False

# Evita reprocessamento dos arquivos em cada renderização, se eles não mudarem
@st.cache_data
def _get_tutor_count(t_bytes, shift_mode):
    _, _, _, _, _, n_tutors = opt.read_tutors(io.BytesIO(t_bytes), shift_mode)
    return n_tutors

@st.cache_data
def _get_school_stats(s_bytes, shift_mode):
    _, _, _, n_schools, n_vacancies = opt.read_schools(io.BytesIO(s_bytes), shift_mode)
    return n_schools, n_vacancies

def show_file_stats(t_file, s_file, shift_mode):
    # Exibe estatísticas básicas dos arquivos importados para feedback imediato ao usuário
    c1, c2 = st.columns(2)

    if s_file:
        try:
            n_schools, n_vacancies = _get_school_stats(s_file.getvalue(), shift_mode)
            c1.info(f"✅ **{n_schools}** Escolas importadas, com **{n_vacancies}** vagas totais")
        except Exception as e:
            c1.error(f"Erro no arquivo de Escolas: {e}")

    if t_file:
        try:
            n_tutors = _get_tutor_count(t_file.getvalue(), shift_mode)
            c2.info(f"✅ **{n_tutors}** Tutores importados")
        except Exception as e:
            c2.error(f"Erro no arquivo de Tutores: {e}")

# --- BARRA LATERAL COM BOTÕES ---
with st.sidebar:
    st.header("Menu")
    
    # Atualiza o estado da sessão com base no botão clicado
    if st.button("Início", width="stretch"):
        st.session_state.current_page = 'home'

    if st.button("Configurações", width="stretch"):
        st.session_state.current_page = 'config'

    if st.button("Informações", width="stretch"):
        st.session_state.current_page = 'info'
        
    st.info("Projeto de Trabalho de Conclusão de Curso do discente Ezequiel Teotônio Jó.")

# --- DECLARAÇÃO DAS PÁGINAS ---
# ------------------ HOME ------------------
if st.session_state.current_page == "home":

    col1, col2, col3 = st.columns([1, 10, 1])

    with col2:
        # Adicionando imagem do projeto CODE
        try:
            banner = Image.open("code-programacao.png")
            st.image(banner, width="stretch")
        except FileNotFoundError:
            st.error("Imagem do projeto não encontrada!")

        st.markdown("<h1 style='text-align: center; color: #eb8334;'>Otimização da Alocação de Tutores CODE</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Uma ferramenta que otimiza a alocação dos tutores às escolas do projeto.</p>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Importe as planilhas de Tutores e Escolas, salve as configurações e clique em Otimizar para gerar o resultado da alocação.</p>", unsafe_allow_html=True)

        # Dividindo para centralizar o botão
        btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1]) 

        with btn_col2:
            with st.container(horizontal_alignment="center"):
                btn_col2_1, btn_col2_2 = st.columns([1, 1])

                with btn_col2_1:
                    if st.button("Importar dados", width="stretch"):
                        st.session_state.current_page = 'config'
                        st.rerun()

                with btn_col2_2:
                    # 1. Apenas guardamos se o botão foi clicado (True ou False)
                    clicou_otimizar = st.button("Otimizar", width="stretch", type="primary")

            # 2. Toda a lógica vem para FORA de btn_col2_1 e btn_col2_2, 
            # mas continua centralizada abaixo deles!
            if clicou_otimizar:
                if not st.session_state.get("saved_config", False):
                    st.warning("Por favor, importe os dados e salve as configurações primeiro.")
                else:
                    try:
                        with st.spinner("Otimizando... Isso pode levar alguns segundos."):
                            
                            t_file = st.session_state.tutors_file
                            s_file = st.session_state.schools_file
                            params = st.session_state.params
                            d_file = "distancias.csv" 
                            
                            result_dict = opt.generate_allocation(t_file, s_file, d_file, params)
                            
                            df_alocacao = result_dict["dataframe"]
                            raw_data = result_dict["raw_data"]
                            metricas = met.get_summary_metrics(df_alocacao, raw_data)

                            st.session_state.optimization_result = result_dict
                            st.session_state.df_allocation_result = df_alocacao
                            st.session_state.df_unallocated = metricas["unallocated"]
                            st.session_state.df_unfilled = metricas["unfilled_vacancies"]
                            
                            st.session_state.optimization_done = True
                            
                        # O success precisa ficar fora do bloco 'with st.spinner' 
                        # para aparecer no lugar exato do spinner quando ele sumir.
                        st.success("Otimização concluída!", icon="✅")

                    except Exception as e:
                        st.error(f"Erro durante a otimização: {e}")

        # --- EXIBIÇÃO DOS RESULTADOS ---
        if st.session_state.get("optimization_done", False):

            res = st.session_state.optimization_result
            stats = res["stats"]

            st.markdown("---")
            st.subheader("📊 Estatísticas da Alocação")

            st.markdown(
                """
                <style>
                [data-testid="stMetricDelta"] svg {
                    display: none;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            
            m1, m2, m3, m4 = st.columns(4)
            
            m1.metric("Tutores Inscritos", stats["total_tutors"])
            m2.metric("Escolas Disponíveis", stats["total_schools"])
            m3.metric("Vagas Totais", stats["total_vacancies"])
            
            vagas_ocupadas = stats["filled_vacancies"]
            vagas_totais = stats["total_vacancies"]
            if vagas_ocupadas < vagas_totais:
                delta_msg = f"{vagas_totais - vagas_ocupadas} vagas ociosas"
                delta_color = "off"
            else:
                delta_msg = "Todas preenchidas!"
                delta_color = "normal"

            m4.metric("Vagas Preenchidas", vagas_ocupadas, delta=delta_msg, delta_color=delta_color)

            st.markdown("---")
            st.markdown("### 📋 Resultados Detalhados")

            aba1, aba2, aba3 = st.tabs(["✅ Alocações", "❌ Não Alocados", "⚠️ Vagas Remanescentes"])

            with aba1:
                allocation = st.session_state.df_allocation_result
                if allocation.empty:
                    st.info("Nenhuma alocação foi possível com os dados e restrições fornecidos.")
                else:
                    st.dataframe(allocation, width="stretch", hide_index=True)
                    
                    csv_data = allocation.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Baixar alocação como CSV",
                        data=csv_data,
                        file_name="alocacao_final.csv",
                        mime="text/csv",
                    )
            
            with aba2:
                df_nao_alocados = st.session_state.df_unallocated
                if df_nao_alocados.empty:
                    st.success("Excelente! Todos os tutores foram alocados em alguma vaga.")
                else:
                    st.dataframe(df_nao_alocados, width="stretch", hide_index=True)
                    
            with aba3:
                df_vagas = st.session_state.df_unfilled
                if df_vagas.empty:
                    st.success("Perfeito! Todas as vagas ofertadas pelas escolas foram preenchidas.")
                else:
                    st.dataframe(df_vagas, width="stretch", hide_index=True)

# ------------------ CONFIGURAÇÕES ------------------
if st.session_state.current_page == "config":

    st.markdown("<h1 style='text-align: center; color: #eb8334;'>Configurações</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Configure os parâmetros do algoritmo.</p>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Para mais informações consulte a página de Informações.</p>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns([1, 5, 5, 1])

    with col2:
        st.markdown("##### Arquivos de Entrada")
        st.markdown("Faça o upload dos arquivos CSV contendo os dados das escolas e dos tutores:")

        schools_file = st.file_uploader("Upload do arquivo de Escolas (CSV)", type=["csv"], key="schools_uploader")
        if schools_file is not None:
            st.success("Arquivo de Escolas carregado com sucesso!", icon="✅")
        elif st.session_state.get("schools_file"):
            schools_file = st.session_state.schools_file
            st.info("Arquivo de Escolas previamente importado (envie um novo para substituir).")

        tutors_file = st.file_uploader("Upload do arquivo de Tutores (CSV)", type=["csv"], key="tutors_uploader")
        if tutors_file is not None:
            st.success("Arquivo de Tutores carregado com sucesso!", icon="✅")
        elif st.session_state.get("tutors_file"):
            tutors_file = st.session_state.tutors_file
            st.info("Arquivo de Tutores previamente importado (envie um novo para substituir).")

    with col3:
        st.markdown("##### Parâmetros do Algoritmo de Otimização")
        st.markdown("Ajuste os parâmetros que influenciam a alocação dos tutores às escolas:")

        # Valores padrão recomendados
        RECOMMENDED = {
            "pref1": 8000, "pref2": 7000, "pref3": 6000,
            "baseDistance": 5000, "baseRanking": 1000000000,
            "decayType": "sigmoid", "sigmoidCurve": 2000,
            "shift_mode": "days_shifts"
        }
        # Recupera parâmetros salvos ou usa os recomendados
        saved = st.session_state.get("params", {})

        st.markdown("###### Modo de Turnos:")
        shift_mode_options = ['Dias e Turnos (10 colunas)', 'Apenas Turnos (2 colunas)']
        shift_index = 0 if saved.get("shift_mode", "days_shifts") == "days_shifts" else 1
        selected_shift_mode_label = st.radio(
            "Selecione a quantidade de turnos possíveis:",
            options=shift_mode_options,
            index=shift_index,
            horizontal=True
        )

        # Converte a seleção do usuário para os valores que o seu script espera
        if selected_shift_mode_label == 'Dias e Turnos (10 colunas)':
            shift_mode = 'days_shifts'
        else:
            shift_mode = 'shifts'

        st.markdown("###### Pontuação das preferências:")

        pref1 = st.number_input("Pontuação da 1º Preferência de Escola:", min_value=0,
            value=saved.get("pref1", RECOMMENDED["pref1"]), icon="🥇")
        pref2 = st.number_input("Pontuação da 2º Preferência Escola:", min_value=0,
            value=saved.get("pref2", RECOMMENDED["pref2"]), icon="🥈")
        pref3 = st.number_input("Pontuação da 3º Preferência Escola:", min_value=0,
            value=saved.get("pref3", RECOMMENDED["pref3"]), icon="🥉")

        baseDistance = st.number_input("Pontuação Base da Preferência por Distâncias:", min_value=0,
            value=saved.get("baseDistance", RECOMMENDED["baseDistance"]), icon="🗺️")

        baseRanking = st.number_input("Pontuação Base para o Ranking dos Tutores:", min_value=0,
            value=saved.get("baseRanking", RECOMMENDED["baseRanking"]), icon="🏆")

        st.markdown("###### Tipo de Decaimento da Pontuação por Distância:")

        decayOptions = ['Sigmoide', 'Linear']
        decay_index = 0 if saved.get("decayType", "sigmoid") == "sigmoid" else 1
        decayType = st.radio(
            "Escolha o tipo de decaimento:",
            options=decayOptions,
            index=decay_index,
            horizontal=True,
            label_visibility="collapsed",
            width="stretch"
        )

        if decayType == 'Sigmoide':
            decayType = 'sigmoid'
        else:
            decayType = 'linear'

        sigmoidCurve = st.number_input("Escala de Inclinação da Curva Sigmoide:", min_value=0,
            value=saved.get("sigmoidCurve", RECOMMENDED["sigmoidCurve"]), icon="📉")

        # Restaura todos os parâmetros para os valores recomendados
        if st.button("Usar configuração recomendada"):
            st.session_state.pop("params", None)
            st.rerun()

    if tutors_file or schools_file:
        st.markdown("---")
        st.markdown("##### 🔍 Pré-visualização dos Dados")
        show_file_stats(tutors_file, schools_file, shift_mode)

    btn_c1, btn_c2, btn_c3 = st.columns([2, 1, 2])
    with btn_c2:
        if st.button("Salvar Configurações", type="primary", width="content"):
                # Verificar se os arquivos foram enviados
                if tutors_file is None or schools_file is None:
                    st.error("Por favor, faça o upload dos arquivos de Tutores e Escolas.")
                else:
                    # Salvar arquivos na sessão
                    st.session_state.tutors_file = tutors_file
                    st.session_state.schools_file = schools_file

                    # Salvar parâmetros na sessão
                    st.session_state.params = {
                        "pref1": pref1,
                        "pref2": pref2,
                        "pref3": pref3,
                        "baseDistance": baseDistance,
                        "baseRanking": baseRanking,
                        "decayType": decayType,
                        "sigmoidCurve": sigmoidCurve,
                        "shift_mode": shift_mode
                    }

                    # Salvar flag de sucesso e mudar de página
                    st.session_state.saved_config = True
                    st.success("Configurações salvas! Retornando ao Início para otimizar.")
                    st.session_state.current_page = 'home'
                    st.rerun()

# ------------------ INFORMAÇÕES ------------------
if st.session_state.current_page == "info":
    st.markdown("<h1 style='text-align: center; color: #eb8334;'>Informações do Sistema</h1>", unsafe_allow_html=True)
    st.write("")

    col1, col2, col3 = st.columns([1, 10, 1])

    with col2:
        st.info("""
        **🎓 Sobre o Projeto**: Esta ferramenta é fruto do **Trabalho de Conclusão de Curso (TCC)** em **Engenharia de Computação** pela **Universidade Federal da Paraíba (UFPB)**. 
        O objetivo é resolver o complexo problema de alocação de tutores do projeto CODE através de técnicas de Pesquisa Operacional (Programação Inteira Mista).
        """)

        st.markdown("### ⚙️ Como o Algoritmo Funciona?")
        st.markdown("""
        O sistema não faz escolhas aleatórias. Ele busca a **melhor distribuição global** possível cruzando os dados e resolvendo um problema matemático de maximização, respeitando regras estritas:
        * **Restrições Rígidas:** Um tutor não pode ser alocado em turnos nos quais não tem disponibilidade; e uma escola não pode receber mais tutores do que o seu limite de vagas ofertadas.
        * **Função Objetivo:** O motor avalia milhares de combinações para gerar a maior "pontuação" total. Essa pontuação é calculada individualmente para cada possível par (Tutor ↔ Escola) com base nos pesos definidos.
        """)

        st.markdown("### 🎛️ Entendendo os Parâmetros")
        
        with st.expander("Clique para ver os detalhes dos parâmetros configuráveis", expanded=True):
            st.markdown("""
            - 🥇🥈🥉 **Preferências (1ª, 2ª e 3ª Opção):** Tutores alocados em suas escolas preferidas geram as maiores pontuações. Você pode definir o 'peso' de cada uma dessas escolhas.
            - 🏆 **Ranking:** O multiplicador do ranking garante justiça ao processo. Tutores com melhor classificação no processo seletivo recebem uma prioridade matemática na disputa por vagas concorridas.
            - 🗺️ **Distância e Decaimento:** Caso o tutor não consiga vaga em suas preferências diretas, o sistema tenta alocá-lo em uma escola próxima à sua 1ª opção. O modelo calcula a matriz de distâncias geográficas e reduz a pontuação quanto mais longe for a escola (utilizando um decaimento **Linear** ou **Sigmoide**).
            """)

        st.markdown("### 📊 Interpretando os Resultados")
        st.markdown("""
        Após rodar a otimização na aba **Início**, o sistema gera um painel de diagnóstico completo dividido em três visões:
        1. **✅ Alocações:** A lista oficial final de quem foi alocado, para qual escola e em qual turno.
        2. **❌ Não Alocados:** Uma auditoria detalhada listando os tutores que ficaram de fora e o motivo matemático exato (ex: *Competição por Ranking* ou *Conflito de Disponibilidade*).
        3. **⚠️ Vagas Remanescentes:** Um alerta para a coordenação mostrando quais escolas ainda têm vagas ociosas para futuras chamadas.
        """)
        
        st.markdown("---")
        st.markdown("<p style='text-align: center; color: gray;'>Desenvolvido por Ezequiel Teotônio Jó.</p>", unsafe_allow_html=True)