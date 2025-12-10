import csv
import io
import math
import pandas as pd
from mip import Model, xsum, MAXIMIZE, BINARY, CBC

distance_matrix = 'distancias.csv'

# =============================================================================
# FUNÇÕES DE LEITURA DE ARQUIVOS
# =============================================================================

def read_tutors(tutors_file_object, shift_mode):
    """
    Lê o OBJETO DE ARQUIVO CSV (vindo do Streamlit) de tutores com disponibilidade e preferências.

    Estrutura esperada do CSV:
    - Coluna 1: 'Tutor' - Identificador único do tutor (ex: 'T1', 'T2')
    - Coluna 2: 'Ranking' - Classificação no processo seletivo (inteiro)
    - Colunas 3-12: Disponibilidade em 10 turnos (binário 0/1):
      * Formato: <Dia>_<Turno> (ex: 'Segunda_Manha', 'Terca_Tarde')
      * Dias: Segunda, Terca, Quarta, Quinta, Sexta
      * Turnos: Manha, Tarde
    - Colunas 13-15: 'Preferencia1', 'Preferencia2', 'Preferencia3' - Escolas preferidas em ordem

    Exemplo de linha:
    Tutor,Ranking,Segunda_Manha,...,Sexta_Tarde,Preferencia1,Preferencia2,Preferencia3
    T1,1,1,0,...,1,EscolaA,EscolaB,EscolaC

    Retorna:
    - Lista de tutores: ['T1', 'T2', ...]
    - Dicionário de disponibilidade: {(tutor, turno): 0/1}
    - Dicionário de preferências: {tutor: [escola1, escola2, escola3]}
    - Dicionário de rankings: {tutor: ranking}
    """

    tutors = []
    availability = {}
    preferences = {}
    rankings = {}

    try:
        # Rebobina o arquivo para garantir leitura do início
        tutors_file_object.seek(0)

        # O objeto do Streamlit (tutors_file_object) é um stream de bytes.
        with io.TextIOWrapper(tutors_file_object, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                tutor = row['Tutor'].strip()
                tutors.append(tutor)

                # Adiciona verificação para valores vazios antes de converter para int
                rank_val = row.get('Ranking', '0')
                rankings[tutor] = int(rank_val if rank_val else '0')

                if shift_mode == 'days_shifts':
                    days = ['Segunda', 'Terca', 'Quarta', 'Quinta', 'Sexta']
                    shifts_per_day = ['Manha', 'Tarde']
                    time_slots = [f"{day}_{shift}" for day in days for shift in shifts_per_day]

                    # Map availability for all time slots in 'days_shifts' mode
                    for time_slot in time_slots:
                        # Usa .get() para segurança e trata strings vazias como '0'
                        slot_val = row.get(time_slot, '0')
                        availability[(tutor, time_slot)] = int(slot_val if slot_val else '0')

                elif shift_mode == 'shifts':
                    # Map availability for 'shifts' mode (Manha, Tarde)
                    for time_slot in ['Manha', 'Tarde']:
                        slot_val = row.get(time_slot, '0')
                        availability[(tutor, time_slot)] = int(slot_val if slot_val else '0')
                
                # Usa .get() para evitar erros caso as colunas de preferência não existam
                preferences[tutor] = [
                    row.get('Preferencia1'),
                    row.get('Preferencia2'),
                    row.get('Preferencia3')
                ]
    
    except Exception as e:
        # Relança um erro claro que o Streamlit pode capturar e exibir com st.error()
        raise ValueError(f"Erro ao ler o arquivo de tutores: {e}. Verifique o formato do CSV.")
        
    return tutors, availability, preferences, rankings, len(tutors)

def read_schools(schools_file_object, MODO_TURNOS, time_slots):
    """
    Lê o OBJETO DE ARQUIVO CSV (vindo do Streamlit) de escolas com vagas por turno.

    Estrutura esperada do CSV:
    - Coluna 1: 'Escola' - Nome da escola (ex: 'EscolaA', 'EscolaB')
    - Colunas 2-11: Vagas em 10 turnos (inteiro ≥ 0):
      * Mesmo formato de turnos dos tutores: <Dia>_<Turno>

    Exemplo de linha:
    Escola,Segunda_Manha,...,Sexta_Tarde
    EscolaA,2,1,...,0

    Retorna:
    - Lista de escolas: ['EscolaA', 'EscolaB', ...]
    - Dicionário de vagas: {(turno, escola): quantidade}
    """

    schools = []
    vacancies = {}
    total_vacancies = 0
    
    try:
        # Rebobina o arquivo para garantir leitura do início
        schools_file_object.seek(0)

        # Decodifica o objeto de arquivo do Streamlit para texto
        with io.TextIOWrapper(schools_file_object, encoding='utf-8') as f:

            reader = csv.DictReader(f)
            
            for row in reader:
                # Usa .get() para evitar erro se a coluna 'Escola' não existir
                school = row.get('Escola', '').strip()
                if not school:
                    continue    # Pula linhas onde a escola não tem nome
                
                schools.append(school)

                if MODO_TURNOS == 'dias_turnos':
                    for time_slot in time_slots:
                        # Usa .get() para segurança e trata strings vazias como '0'
                        slot_val = row.get(time_slot, '0')
                        val = int(slot_val if slot_val else '0')
                        vacancies[(time_slot, school)] = val
                        total_vacancies += val

                elif MODO_TURNOS == 'turnos':
                    for time_slot in ['Manha', 'Tarde']:
                        slot_val = row.get(time_slot, '0')
                        val = int(slot_val if slot_val else '0')
                        vacancies[(time_slot, school)] = val
                        total_vacancies += val
    
    except Exception as e:
        # Relança um erro claro que o Streamlit pode capturar e exibir com st.error()
        raise ValueError(f"Erro ao ler o arquivo de escolas: {e}. Verifique o formato do CSV.")
    
    return schools, vacancies, len(schools), total_vacancies

def read_distances():
    """
    Lê a matriz de distâncias (arquivo 'distancias.csv' local) entre escolas.

    Estrutura esperada do CSV:
    - Linha 1 (cabeçalho): Escolas na ordem de referência 
    * Formato: ,SchoolA,SchoolB,SchoolC (primeira célula vazia)
    - Linhas subsequentes: 
    * Coluna 1: Nome da escola de origem
    * Demais colunas: Distância para escola do cabeçalho (número)

    Exemplo:
    ,SchoolA,SchoolB,SchoolC
    SchoolA,0,5,8
    SchoolB,5,0,6
    SchoolC,8,6,0

    Retorna:
    - Dicionário de distâncias: {(origem, destino): valor}
    * Ex: distancias[('SchoolA','SchoolB')] = 5

    Notas:
    - A ordem das escolas no cabeçalho e primeira coluna deve ser idêntica
    """

    distances = {}
    filename = distance_matrix

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            
            try:
                # Lê o cabeçalho (lista de escolas)
                header = next(reader)
                schools = [s.strip() for s in header[1:]]
            except StopIteration:
                raise ValueError(f"O arquivo '{filename}' está vazio.")
            
            # Processa cada linha da matriz
            for row in reader:
                if not row:     # Pula linhas vazias
                    continue
                
                origin_school = row[0].strip()
                for idx, distance_str in enumerate(row[1:]):
                    
                    # Garante que não tente ler além do número de escolas do cabeçalho
                    if idx < len(schools):
                        target_school = schools[idx]
                        
                        # Converte o valor da distância
                        distance_val = distance_str.strip()
                        if distance_val:
                            distances[(origin_school, target_school)] = (
                                float(distance_val) if '.' in distance_val else int(distance_val)
                            )
                        else:
                            # Trata caso de célula vazia como distância 0 ou indefinida
                            distances[(origin_school, target_school)] = 0 
    
    except FileNotFoundError:
        # Informa se o arquivo não foi encontrado no repositório
        raise FileNotFoundError(
            f"ERRO: O arquivo '{filename}' não foi encontrado. "
            "Certifique-se de que ele esteja no mesmo diretório do seu script."
        )
    except Exception as e:
        # Captura outros erros
        raise ValueError(f"Erro ao processar o arquivo de distâncias '{filename}': {e}")
        
    return distances

def calculate_mean_distances():
    """
    Lê a matriz de distâncias ('distancias.csv') e calcula a média geral.

    Retorna:
    - A média (float) de todas as distâncias > 0.
    """

    filename = distance_matrix  
    overall_mean = 0.0

    try:
        df = pd.read_csv(filename, index_col=0)
        
        # Empilha a matriz para uma única coluna e filtra distâncias maiores que zero
        relevant_distances = df.stack()
        relevant_distances = relevant_distances[relevant_distances > 0]
        
        if not relevant_distances.empty:
            overall_mean = relevant_distances.mean()
            
    except FileNotFoundError:
        raise FileNotFoundError(
            f"ERROR: The distance file '{filename}' was not found. "
            "Check if it is in the repository."
        )
    except Exception as e:
        raise ValueError(f"An error occurred while reading the distance file: {e}")

    return overall_mean

# =============================================================================
# FUNÇÕES DE CÁLCULO DE BENEFÍCIOS
# =============================================================================

def linear_decay(distance, max_distance, base_score):
    """
    Calcula a pontuação com base em um decaimento linear.
    A pontuação é 'base_score' em distance=0 e 0 em distance='max_distance'.
    """
    if max_distance == 0 or distance >= max_distance:
        return 0

    score = (-base_score / max_distance) * distance + base_score    # Fórmula da reta decrescente
    return max(0, score) # Garante que a pontuação não seja negativa

def sigmoid_decay(distance, bmax, mean, scale):
    """
    Calcula a pontuação de decaimento sigmoide.
    Os parâmetros (bmax, mean, scale) agora são passados explicitamente.
    """
    return bmax / (1 + math.exp((distance - mean) / scale))

def calculate_benefits(tutors, schools, preferences, distances, rankings, 
                        decay_type,
                        pref1, 
                        pref2, 
                        pref3, 
                        baseDistance,
                        baseRanking,
                        sigmoidCurve,
                        distance_mean):
    """
    Calcula os benefícios para cada par (tutor, escola) usando a curva de decaimento especificada.
    Recebe todos os parâmetros de configuração (pref1, baseDistance, etc.) vindos do Streamlit.
    """

    benefits = {}
    total_tutors = len(tutors)

    decrement = baseRanking / total_tutors if total_tutors > 0 else 0

    maior_distancia = max(distances.values()) if distances else 0
    
    for tutor in tutors:
        prefs = preferences.get(tutor, [])
        ranking_position = rankings.get(tutor, total_tutors)
        # Usa o parâmetro 'baseRanking'
        multiplier = max(baseRanking - (ranking_position - 1) * decrement, 1)
        
        reference_school = prefs[0] if prefs else None
        
        for school in schools:
            if school in prefs:
                position = prefs.index(school) + 1
                if position == 1:
                    benefit_score = pref1  # Usa o parâmetro 'pref1'
                elif position == 2:
                    benefit_score = pref2  # Usa o parâmetro 'pref2'
                elif position == 3:
                    benefit_score = pref3  # Usa o parâmetro 'pref3'
                else:
                    benefit_score = 0
            else:
                if reference_school:
                    distance = distances.get((reference_school, school), float('inf'))

                    if decay_type == 'linear':
                        # Passa o parâmetro 'baseDistance'
                        benefit_score = int(linear_decay(distance, maior_distancia, baseDistance))
                    elif decay_type == 'sigmoid':
                        # Passa todos os parâmetros necessários
                        benefit_score = int(sigmoid_decay(distance, 
                                                            bmax=baseDistance, 
                                                            mean=distance_mean, 
                                                            scale=sigmoidCurve))

                    benefit_score = max(benefit_score, 1)
                else:
                    benefit_score = 0
            
            # Aplica o multiplicador baseado na posição do ranking
            benefits[(tutor, school)] = benefit_score * multiplier
    
    return benefits

def extract_allocation_results(model, tutors, time_slots, schools):
    """
    Extrai as alocações do modelo otimizado e retorna uma lista de dicionários.
    (Baseado em 'save_allocation_results' mas sem salvar em arquivo).
    """
    results = []
    
    # Coletar alocações válidas
    for tutor in tutors:
        for time_slot in time_slots:
            for school in schools:
                
                # Tenta encontrar a variável de decisão pelo nome
                var_name = f'X_{tutor}_{time_slot}_{school}'
                var = model.var_by_name(var_name)
                
                # Verifica se a variável existe e se foi selecionada (valor ~1)
                if var is not None and var.x >= 0.99:
                    results.append({
                        'Escola': school,
                        'Turno da Vaga': time_slot,
                        'Tutor Alocado': tutor
                    })
    
    return results

# =============================================================================
# FUNÇÃO PRINCIPAL DA OTIMIZAÇÃO
# =============================================================================

def generate_allocation(tutors_file, schools_file, params_dict):
    """
    Função mestra que executa todo o processo de otimização.
    
    Recebe:
    - tutors_file: O objeto de arquivo CSV dos tutores (do st.file_uploader)
    - schools_file: O objeto de arquivo CSV das escolas (do st.file_uploader)
    - params_dict: Um dicionário com todos os parâmetros da página de config
    
    Retorna:
    - Um DataFrame do Pandas com a alocação final.
    """
    
    try:
        # --- Definir Parâmetros de Turno ---
        # Pega o 'shift_mode' que veio do params_dict.
        # Usa 'dias_turnos' como padrão se nada for passado.
        SHIFT_MODE = params_dict.get('shift_mode', 'dias_turnos') 
            
        if SHIFT_MODE == 'dias_turnos':
            days = ['Segunda', 'Terca', 'Quarta', 'Quinta', 'Sexta']
            shifts_per_day = ['Manha', 'Tarde']
            time_slots = [f"{day}_{shift}" for day in days for shift in shifts_per_day]
        elif SHIFT_MODE == 'turnos':
            time_slots = ['Manha', 'Tarde']
        else:
            raise ValueError(f"Modo de turno '{SHIFT_MODE}' desconhecido.")

        # --- Extrair Parâmetros de Configuração ---
        PREF1_SCORE = params_dict.get('pref1', 8000)
        PREF2_SCORE = params_dict.get('pref2', 7000)
        PREF3_SCORE = params_dict.get('pref3', 6000)
        NON_PREF_BASE_SCORE = params_dict.get('baseDistance', 5000)
        RANKING_MULTIPLIER = params_dict.get('baseRanking', 10**9)
        DISTANCE_DECAY_TYPE = params_dict.get('decayType', 'sigmoid')
        SIGMOID_SCALE = params_dict.get('sigmoidCurve', 2000)

        # --- Carregar Dados ---
        tutors, availability, preferences, rankings, total_tutors = read_tutors(tutors_file, SHIFT_MODE, time_slots)
        schools, vacancies, total_schools, total_vacancies = read_schools(schools_file, SHIFT_MODE, time_slots)
        distances = read_distances()
        DISTANCE_MEAN = calculate_mean_distances() # Calcula a média de 'distancias.csv'

        # --- Calcular Benefícios ---
        benefits = calculate_benefits(
            tutors, schools, preferences, distances, rankings,
            decay_type=DISTANCE_DECAY_TYPE,
            pref1=PREF1_SCORE,
            pref2=PREF2_SCORE,
            pref3=PREF3_SCORE,
            baseDistance=NON_PREF_BASE_SCORE,
            baseRanking=RANKING_MULTIPLIER,
            sigmoidCurve=SIGMOID_SCALE,
            distance_mean=DISTANCE_MEAN
        )

        # --- Construir e Rodar o Modelo MIP ---
        model = Model(sense=MAXIMIZE, solver_name=CBC)

        X = {
            (t, time_slot, s): model.add_var(name=f'X_{t}_{time_slot}_{s}', var_type=BINARY)
            for t in tutors
            for time_slot in time_slots
            for s in schools
        }

        # Restrição 1: Cada tutor em no máximo um turno/escola
        for t in tutors:
            model += xsum(X[t, time_slot, s] for time_slot in time_slots for s in schools) <= 1

        # Restrição 2: Respeitar vagas das escolas
        for time_slot in time_slots:
            for s in schools:
                model += xsum(X[t, time_slot, s] for t in tutors) <= vacancies.get((time_slot, s), 0)

        # Restrição 3: Respeitar disponibilidade dos tutores
        for t in tutors:
            for time_slot in time_slots:
                for s in schools:
                    model += X[t, time_slot, s] <= availability.get((t, time_slot), 0)

        # Função Objetivo
        model.objective = xsum(
            benefits[t, s] * X[t, time_slot, s]
            for t in tutors
            for time_slot in time_slots
            for s in schools
        )
        
        # Resolver o modelo
        model.optimize()

        # --- Extrair e Retornar os Resultados ---  
        results_list = extract_allocation_results(model, tutors, time_slots, schools)

        if not results_list:
            # Retorna um DataFrame vazio se nenhuma alocação for feita
            return pd.DataFrame(columns=['Escola', 'Turno da Vaga', 'Tutor Alocado'])
        
        # Converte a lista de resultados em um DataFrame
        df_allocation = pd.DataFrame(results_list)

        # --- CÁLCULO DAS ESTATÍSTICAS ---
        stats = {
            "total_tutors": total_tutors,
            "total_schools": total_schools,
            "total_vacancies": total_vacancies,
            "filled_vacancies": len(results_list)
        }

        return {
            "dataframe": df_allocation,
            "stats": stats
        }

    except Exception as e:
        raise e
