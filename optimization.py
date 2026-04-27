import csv
import io
import math
import pandas as pd
from mip import Model, xsum, MAXIMIZE, BINARY, CBC, OptimizationStatus

distance_matrix = 'distancias.csv'

# =============================================================================
# FUNÇÕES DE LEITURA DE ARQUIVOS
# =============================================================================

def read_tutors(file_input, shift_mode):
    """
    Lê os dados dos tutores aceitando tanto o caminho do arquivo (string para rodar localmente) 
    quanto o objeto de arquivo (BytesIO do Streamlit).

    Estrutura esperada do CSV:
    - Coluna 1: 'Tutor' - Identificador único do tutor (ex: 'T1', 'T2')
    - Coluna 2: 'Ranking' - Classificação no processo seletivo (inteiro)
    - Colunas de Vagas: <Dia>_<Turno> ou <Turno> (binário 0/1)
    - Colunas de Preferência: 'Preferencia1', 'Preferencia2', 'Preferencia3'
    - Coluna Opcional: 'Polos' - Distritos desejados separados por vírgula

    Retorna:
    - tutors: Lista de tutores
    - availability: Dicionário {(tutor, turno): 0/1}
    - preferences: Dicionário {tutor: [escola1, escola2, escola3]}
    - rankings: Dicionário {tutor: ranking}
    - tutor_districts: Dicionário {tutor: ['PoloA', 'PoloB']}
    - total_tutors: Quantidade total de tutores lidos (int)
    """
    tutors = []
    availability = {}
    preferences = {}
    rankings = {}
    tutor_districts = {}

    # --- LÓGICA HÍBRIDA ---
    if isinstance(file_input, str):
        # Rodando localmente: abre o arquivo pelo caminho
        f = open(file_input, 'r', encoding='utf-8')
        should_close = True
        reader_source = f
    else:
        # Rodando no Streamlit: usa o objeto em memória
        file_input.seek(0)                                      # Rebobina o arquivo
        content = file_input.read().decode('utf-8')             # Decodifica
        f = io.StringIO(content)                                # Cria o StringIO
        should_close = False
        reader_source = f

    try:
        reader = csv.DictReader(reader_source)
            
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

                for time_slot in time_slots:
                    # Usa .get() para segurança e trata strings vazias como '0'
                    slot_val = row.get(time_slot, '0')
                    availability[(tutor, time_slot)] = int(slot_val if slot_val else '0')

            elif shift_mode == 'shifts':
                for time_slot in ['Manha', 'Tarde']:
                    slot_val = row.get(time_slot, '0')
                    availability[(tutor, time_slot)] = int(slot_val if slot_val else '0')
            
            # Usa .get() para evitar erros caso as colunas de preferência não existam
            preferences[tutor] = [
                p for p in [
                    row.get('Preferencia1'),
                    row.get('Preferencia2'),
                    row.get('Preferencia3')
                ] if p and str(p).strip()
            ]

            district_str = row.get('Polos', '').strip()
            if district_str:
                tutor_districts[tutor] = [p.strip() for p in district_str.split(',')]
            else:
                tutor_districts[tutor] = []
    
    except Exception as e:
        # Relança um erro claro que o Streamlit ou console podem capturar
        raise ValueError(f"Erro ao ler o arquivo de tutores: {e}. Verifique o formato do CSV.")
        
    finally:
        # Garante fechamento apenas se o arquivo foi aberto fisicamente
        if should_close:
            f.close()

    return tutors, availability, preferences, rankings, tutor_districts, len(tutors)

def read_schools(file_input, shift_mode):
    """
    Lê os dados das escolas aceitando tanto o caminho do arquivo (string para rodar localmente) 
    quanto o objeto de arquivo (BytesIO do Streamlit).

    Estrutura esperada do CSV:
    - Coluna 1: 'Escola' - Nome da escola (ex: 'EscolaA', 'EscolaB')
    - Coluna: 'Polo' - Distrito/Região da escola
    - Colunas de Vagas: <Dia>_<Turno> ou apenas <Turno>

    Retorna:
    - schools: Lista de escolas
    - vacancies: Dicionário de vagas {(turno, escola): quantidade}
    - school_districts: Dicionário mapeando a escola ao seu polo
    - total_schools: Quantidade total de escolas lidas
    - total_vacancies: Somatório de todas as vagas encontradas
    """

    schools = []
    vacancies = {}
    school_districts = {}
    total_vacancies = 0

    if isinstance(file_input, str):
        # Rodando localmente: abre o arquivo pelo caminho
        f = open(file_input, 'r', encoding='utf-8')
        should_close = True
        reader_source = f
    else:
        # Rodando no Streamlit: usa o objeto em memória
        file_input.seek(0)                                      # Rebobina o arquivo
        content = file_input.read().decode('utf-8')             # Decodifica
        f = io.StringIO(content)                                # Cria o StringIO
        should_close = False
        reader_source = f

    try:
        reader = csv.DictReader(reader_source)
            
        for row in reader:
            # Usa .get() para evitar erro se a coluna 'Escola' não existir
            school = row.get('Escola', '').strip()
            if not school:
                continue    # Pula linhas onde a escola não tem nome
                
            schools.append(school)

            district = row.get('Polo', '').strip()
            school_districts[school] = district

            if shift_mode == 'days_shifts':
                days = ['Segunda', 'Terca', 'Quarta', 'Quinta', 'Sexta']
                shifts_per_day = ['Manha', 'Tarde']
                time_slots = [f"{day}_{shift}" for day in days for shift in shifts_per_day]

                for time_slot in time_slots:
                    slot_val = row.get(time_slot, '0')
                    val = int(slot_val if slot_val else '0')
                    vacancies[(time_slot, school)] = val
                    total_vacancies += val

            elif shift_mode == 'shifts':
                for time_slot in ['Manha', 'Tarde']:
                    slot_val = row.get(time_slot, '0')
                    val = int(slot_val if slot_val else '0')
                    vacancies[(time_slot, school)] = val
                    total_vacancies += val
    
    except Exception as e:
        # Relança um erro claro que o Streamlit ou o console podem capturar
        raise ValueError(f"Erro ao ler o arquivo de escolas: {e}. Verifique o formato do CSV.")
        
    finally:
        # Garante fechamento apenas se o arquivo foi aberto fisicamente pelo código local
        if should_close:
            f.close()
    
    return schools, vacancies, school_districts, len(schools), total_vacancies

def read_distances(file_input):
    """
    Lê a matriz de distâncias entre escolas, aceitando tanto o caminho do arquivo (string) 
    quanto o objeto de arquivo (BytesIO do Streamlit).

    Estrutura esperada do CSV:
    - Linha 1 (cabeçalho): Escolas na ordem de referência 
      * Formato: ,SchoolA,SchoolB,SchoolC (primeira célula vazia)
    - Linhas subsequentes: 
      * Coluna 1: Nome da escola de origem
      * Demais colunas: Distância para escola do cabeçalho (número)

    Retorna:
    - distances: Dicionário de distâncias {(origem, destino): valor}
    """
    distances = {}

    if isinstance(file_input, str):
        # Rodando localmente: abre o arquivo pelo caminho
        f = open(file_input, 'r', encoding='utf-8')
        should_close = True
        reader_source = f
    else:
        # Rodando no Streamlit: usa o objeto em memória
        file_input.seek(0)
        content = file_input.read().decode('utf-8')
        f = io.StringIO(content)
        should_close = False
        reader_source = f

    try:
        reader = csv.reader(reader_source)
        
        try:
            # Lê o cabeçalho (lista de escolas)
            header = next(reader)
            schools = [s.strip() for s in header[1:]]
        except StopIteration:
            raise ValueError("O arquivo de distâncias está vazio.")
        
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
    
    except Exception as e:
        # Captura outros erros e envia para o Streamlit/Console
        raise ValueError(f"Erro ao processar o arquivo de distâncias: {e}")
        
    finally:
        # Garante fechamento apenas se o arquivo foi aberto fisicamente
        if should_close:
            f.close()
            
    return distances

def calculate_mean_distances(file_input, active_schools):
    """
    Lê a matriz de distâncias e calcula a média dinamicamente.
    Aceita tanto o caminho do arquivo (string) quanto o objeto em memória (Streamlit).
    Considera apenas as escolas presentes na lista 'active_schools'.
    
    Args:
    - file_input: Caminho do arquivo ou objeto BytesIO/StringIO.
    - active_schools: Lista de strings com os nomes das escolas ativas.

    Retorna:
    - distances_mean: A média (float) das distâncias > 0 entre as escolas ativas.
    """
    distances_mean = 0.0

    #print(f"--- Calculando média de distância dinâmica ---")
    #print(f"Escolas ativas neste cenário: {len(active_schools)}")

    # --- LÓGICA HÍBRIDA (Super simples graças ao Pandas) ---
    if not isinstance(file_input, str):
        file_input.seek(0) # Rebobina o arquivo se for um upload do Streamlit

    try:
        # O Pandas lê diretamente tanto do disco quanto da memória!
        df = pd.read_csv(file_input, index_col=0)
        
        # Identifica escolas que estão na lista de vagas mas NÃO estão na matriz
        missing_schools = [e for e in active_schools if e not in df.index]
        
        if len(missing_schools) > 0:
            print(f"⚠️ ATENÇÃO: {len(missing_schools)} escolas ativas NÃO foram encontradas na matriz de distâncias.")
            # Descomente a linha abaixo se quiser ver os nomes das escolas faltando
            # for school in missing_schools: print(f"   -> {school}")

        # Interseção: escolas que estão 'ativas' E que existem na matriz
        valid_schools = [e for e in active_schools if e in df.index]
        
        if len(valid_schools) >= 2:
            print(f"Matriz filtrada para {len(valid_schools)} x {len(valid_schools)} escolas.")
            df = df.loc[valid_schools, valid_schools]
        else:
            print("AVISO: Menos de 2 escolas ativas na matriz. Usando matriz completa.")
        
        # Filtra distâncias maiores que zero
        relevant_distances = df.stack()
        relevant_distances = relevant_distances[relevant_distances > 0]
        
        if not relevant_distances.empty:
            distances_mean = relevant_distances.mean()
            print(f"Distancia Média entre escolas dessa instância = {distances_mean:.2f}")
        else:
            print("Nenhuma distância válida encontrada > 0. Retornando 0.")
            
    except FileNotFoundError:
        # Mantido para caso file_input seja uma string de um caminho incorreto
        raise FileNotFoundError("ERRO: O arquivo de distâncias não foi encontrado.")
    except Exception as e:
        raise ValueError(f"Erro ao processar o arquivo de distâncias para calcular a média: {e}")

    return distances_mean

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
        
        valid_prefs = [p for p in prefs if p and str(p).strip()]
        reference_school = valid_prefs[0] if valid_prefs else None
        
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

def extract_allocation_results(X_dict):
    """
    Extrai as alocações do dicionário de variáveis do modelo otimizado.
    Retorna uma lista de dicionários com os resultados.
    
    Args:
    - X_dict: Dicionário contendo as variáveis de decisão do MIP. 
    O formato esperado das chaves é uma tupla: (tutor, time_slot, school)
    """
    results = []
    
    # Itera diretamente sobre o dicionário de variáveis criadas no modelo
    for keys, var in X_dict.items():
        # Desempacota a tupla da chave
        tutor, time_slot, school = keys
        
        # Verifica se a variável foi selecionada (valor ~1) pelo algoritmo
        if var.x >= 0.99:
            results.append({
                'Escola': school,
                'Turno da Vaga': time_slot,
                'Tutor Alocado': tutor
            })
    
    return results

# =============================================================================
# FUNÇÃO PRINCIPAL DA OTIMIZAÇÃO
# =============================================================================

def generate_allocation(tutors_file, schools_file, distances_file, params_dict):
    """
    Função mestra que executa todo o processo de otimização.
    
    Recebe:
    - tutors_file: O objeto de arquivo CSV dos tutores (ou string de caminho)
    - schools_file: O objeto de arquivo CSV das escolas (ou string de caminho)
    - distances_file: O objeto ou caminho do arquivo da matriz de distâncias
    - params_dict: Um dicionário com todos os parâmetros da página de config
    
    Retorna:
    - Um dicionário contendo o DataFrame final, as estatísticas e os dados puros (raw_data).
    """
    
    try:
        # --- Definir Parâmetros de Turno ---
        shift_mode = params_dict.get('shift_mode', 'days_shifts') 

        if shift_mode == 'days_shifts':
            days = ['Segunda', 'Terca', 'Quarta', 'Quinta', 'Sexta']
            shifts_per_day = ['Manha', 'Tarde']
            time_slots = [f"{day}_{shift}" for day in days for shift in shifts_per_day]
        elif shift_mode == 'shifts':
            time_slots = ['Manha', 'Tarde']
        else:
            raise ValueError(f"Modo de turno '{shift_mode}' desconhecido.")

        # --- Extrair Parâmetros de Configuração ---
        PREF1_SCORE = params_dict.get('pref1', 8000)
        PREF2_SCORE = params_dict.get('pref2', 7000)
        PREF3_SCORE = params_dict.get('pref3', 6000)
        NON_PREF_BASE_SCORE = params_dict.get('baseDistance', 5000)
        RANKING_MULTIPLIER = params_dict.get('baseRanking', 10**9)
        DISTANCE_DECAY_TYPE = params_dict.get('decayType', 'sigmoid')
        SIGMOID_SCALE = params_dict.get('sigmoidCurve', 2000)

        # --- Carregar Dados ---
        tutors, availability, preferences, rankings, tutor_districts, total_tutors = read_tutors(tutors_file, shift_mode)
        schools, vacancies, school_districts, total_schools, total_vacancies = read_schools(schools_file, shift_mode)

        active_schools = list({s for (slot, s), v in vacancies.items() if v > 0})
        
        # Agora passamos o arquivo de distâncias como parâmetro
        distances = read_distances(distances_file)
        DISTANCE_MEAN = calculate_mean_distances(distances_file, active_schools) 

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
        model.verbose = 0 # Silencia os logs do solver no console

        # --- Configuração para Reprodutibilidade ---
        model.threads = 1  # Força o uso de apenas 1 núcleo do processador
        model.seed = 37    # Fixa a semente matemática para os desempates e heurísticas

        # Dicionário de variáveis (X)
        X = {}
        for t in tutors:
            for time_slot in time_slots:
                for s in schools:
                    # Só cria a variável de decisão se o tutor tem disponibilidade E a escola tem vaga.
                    if availability.get((t, time_slot), 0) > 0 and vacancies.get((time_slot, s), 0) > 0:
                        X[(t, time_slot, s)] = model.add_var(var_type=BINARY)

        # Restrição 1: Cada tutor em no máximo um turno/escola
        for t in tutors:
            # Pega apenas as variáveis que existem para este tutor
            vars_tutor = [X[k] for k in X if k[0] == t]
            if vars_tutor:
                model += xsum(vars_tutor) <= 1

        # Restrição 2: Respeitar vagas das escolas
        for time_slot in time_slots:
            for s in schools:
                # Pega apenas as variáveis que existem para esta escola e turno
                vars_escola_turno = [X[k] for k in X if k[1] == time_slot and k[2] == s]
                if vars_escola_turno:
                    model += xsum(vars_escola_turno) <= vacancies.get((time_slot, s), 0)

        # Restrição 3: Respeitar disponibilidade dos tutores
        for keys, var in X.items():
            t, time_slot, s = keys
            model += var <= availability.get((t, time_slot), 0)

        # Função Objetivo
        model.objective = xsum(
            benefits.get((keys[0], keys[2]), 0) * var
            for keys, var in X.items()
        )
        
        # Resolver o modelo e verificar o status da solução
        status = model.optimize()

        if status == OptimizationStatus.INFEASIBLE:
            raise ValueError(
                "O modelo não possui solução viável. "
                "Verifique se há tutores com disponibilidade para as vagas ofertadas."
            )
        elif status == OptimizationStatus.NO_SOLUTION_FOUND:
            raise ValueError(
                "O solver não conseguiu encontrar uma solução no tempo limite. "
                "Tente simplificar as restrições ou aumentar o tempo máximo."
            )
        elif status not in (OptimizationStatus.OPTIMAL, OptimizationStatus.FEASIBLE):
            raise ValueError(
                f"O solver retornou status inesperado: {status}. "
                "Não foi possível gerar uma alocação confiável."
            )

        # --- Extrair e Retornar os Resultados ---
        results_list = extract_allocation_results(X)

        if not results_list:
            df_allocation = pd.DataFrame(columns=['Escola', 'Turno da Vaga', 'Tutor Alocado'])
        else:
            df_allocation = pd.DataFrame(results_list)

        # --- Cálculo das Estatísticas ---
        stats = {
            "total_tutors": total_tutors,
            "total_schools": total_schools,
            "total_vacancies": total_vacancies,
            "filled_vacancies": len(results_list)
        }

        return {
            "dataframe": df_allocation,
            "stats": stats,
            "raw_data": {
                "tutors": tutors,
                "schools": schools,               
                "time_slots": time_slots,
                "vacancies": vacancies,
                "rankings": rankings,
                "preferences": preferences,
                "availability": availability,
                "distances": distances,
                "tutor_districts": tutor_districts,
                "school_districts": school_districts
            }
        }

    except Exception as e:
        raise ValueError(f"Erro ao processar a otimização: {e}")
