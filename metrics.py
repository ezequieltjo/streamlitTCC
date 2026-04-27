import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime

# =============================================================================
# FUNÇÕES DE ANÁLISE DE MÉTRICAS E KPIs
# =============================================================================

def analyze_unallocated_tutors(df_allocation, raw_data):
    """
    Analisa os tutores que não foram alocados, determinando o motivo e 
    extraindo suas preferências, polos e disponibilidades.
    Retorna um DataFrame estruturado para exibição direta no Streamlit.
    """ 
    all_tutors = raw_data.get('tutors', [])
    time_slots = raw_data.get('time_slots', [])
    vacancies_dict = raw_data.get('vacancies', {})
    rankings = raw_data.get('rankings', {})
    preferences = raw_data.get('preferences', {})
    availability = raw_data.get('availability', {})
    tutor_districts = raw_data.get('tutor_districts', {})
    
    # --- Identificação de quem ficou de fora ---
    if df_allocation.empty:
        allocated_tutors = set()
    else:
        allocated_tutors = set(df_allocation['Tutor Alocado'].dropna())
    
    unallocated_tutors = set(all_tutors) - allocated_tutors
    
    if not unallocated_tutors:
        # Retorna DataFrame vazio já com as colunas formatadas se todos foram alocados
        return pd.DataFrame(columns=[
            'Tutor', 'Ranking', 'Motivo', 'Escolas Preferenciais', 
            'Polos Preferenciais', 'Turnos Disponíveis'
        ])
        
    # --- Mapeando Vencedores ---
    # Identifica todas as vagas ofertadas originalmente
    available_vacancies = set()
    for (time_slot, school), count in vacancies_dict.items():
        if count > 0:
            available_vacancies.add((school, time_slot))
            
    # Conta alocações por vaga e rastreia o pior ranking vencedor por vaga
    allocated_counts = {}
    winners_by_vacancy = {}

    if not df_allocation.empty:
        df_alloc_temp = df_allocation.copy()
        df_alloc_temp['tutor_rank'] = df_alloc_temp['Tutor Alocado'].map(rankings).fillna(999999).astype(int)
        df_alloc_temp['v_key'] = list(zip(df_alloc_temp['Escola'], df_alloc_temp['Turno da Vaga']))
        allocated_counts = df_alloc_temp['v_key'].value_counts().to_dict()
        winners_by_vacancy = df_alloc_temp.groupby('v_key')['tutor_rank'].max().to_dict()
                
    # --- Análise Individual dos Não Alocados ---
    results = []
    
    # Ordena para o relatório seguir a ordem dos melhores rankings primeiro
    sorted_unallocated = sorted(list(unallocated_tutors), key=lambda t: rankings.get(t, 999999))
    
    for tutor in sorted_unallocated:
        tutor_rank = rankings.get(tutor, 999999)
        
        tutor_avail_slots = [ts for ts in time_slots if availability.get((tutor, ts), 0) > 0]
        tutor_prefs = [p for p in preferences.get(tutor, []) if pd.notna(p) and p]
        tutor_polos = tutor_districts.get(tutor, [])
        
        # Lógica Matemática do Motivo
        compatible_vacancies = {v for v in available_vacancies if v[1] in tutor_avail_slots}
        
        reason = ""
        lost_to_better = 0
        lost_to_worse = 0
        
        if not compatible_vacancies:
            reason = "CONFLITO DE DISPONIBILIDADE"
        else:
            for vacancy in compatible_vacancies:
                # Verifica se a vaga foi totalmente preenchida
                # Se não foi preenchida, o tutor não perdeu por ranking, foi barrado pela otimização global
                if allocated_counts.get(vacancy, 0) < vacancies_dict.get((vacancy[1], vacancy[0]), 0):
                    lost_to_worse += 1 
                else:
                    winner_rank = winners_by_vacancy.get(vacancy)
                    if winner_rank is not None:
                        if winner_rank < tutor_rank:     # Venceu alguém com número menor (melhor)
                            lost_to_better += 1
                        elif winner_rank > tutor_rank:   # Venceu alguém com número maior (pior)
                            lost_to_worse += 1
            
            # Se TODAS as vagas compatíveis foram perdidas estritamente para pessoas de ranking melhor:
            if lost_to_better > 0 and lost_to_worse == 0 and len(compatible_vacancies) == lost_to_better:
                reason = "COMPETIÇÃO POR RANKING"
            else:
                reason = "INDETERMINADO / MISTO"
                
        results.append({
            'Tutor': tutor,
            'Ranking': tutor_rank if tutor_rank != 999999 else 'N/A',
            'Motivo': reason,
            'Escolas Preferenciais': ", ".join(tutor_prefs) if tutor_prefs else "Nenhuma",
            'Polos Preferenciais': ", ".join(tutor_polos) if tutor_polos else "Nenhum",
            'Turnos Disponíveis': ", ".join(tutor_avail_slots) if tutor_avail_slots else "Nenhum"
        })
        
    df_unallocated = pd.DataFrame(results)
    
    return df_unallocated

def analyze_unfilled_vacancies(df_allocation, raw_data):
    """
    Compara as vagas ofertadas originalmente com as alocações realizadas
    pelo modelo para identificar exatamente onde sobraram vagas.
    Retorna um DataFrame estruturado para exibição direta no Streamlit.
    """
    vacancies_dict = raw_data.get('vacancies', {})
    
    # --- Contagem das Alocações Realizadas ---
    if df_allocation.empty:
        allocated_counts = {}
    else:
        # Agrupa pelo Turno e Escola e conta quantas linhas (tutores) existem lá.
        # to_dict() cria algo como: {('Manha', 'Escola A'): 2, ('Tarde', 'Escola B'): 1}
        allocated_counts = df_allocation.groupby(['Turno da Vaga', 'Escola']).size().to_dict()
        
    # --- Verificação de Vagas Sobrando ---
    unfilled_results = []
    
    for (time_slot, school), total_offered in vacancies_dict.items():
        if total_offered > 0:
            # Pega quantas vagas foram preenchidas (se não achar no dicionário, assume 0)
            filled = allocated_counts.get((time_slot, school), 0)
            remaining = total_offered - filled
            
            # Se a quantidade ofertada for maior que a preenchida, sobrou vaga
            if remaining > 0:
                unfilled_results.append({
                    'Escola': school,
                    'Turno da Vaga': time_slot,
                    'Vagas Ofertadas': total_offered,
                    'Vagas Preenchidas': filled,
                    'Vagas Sobrando': remaining
                })
                
    # --- Construção e Formatação do DataFrame ---
    if not unfilled_results:
        # Se não sobrou nenhuma vaga, devolve um DataFrame vazio
        df_unfilled = pd.DataFrame(columns=[
            'Escola', 'Turno da Vaga', 'Vagas Ofertadas', 'Vagas Preenchidas', 'Vagas Sobrando'
        ])
    else:
        df_unfilled = pd.DataFrame(unfilled_results)
        df_unfilled = df_unfilled.sort_values(by=['Escola', 'Turno da Vaga']).reset_index(drop=True)
        
    return df_unfilled

def analyze_polo_matches(df_allocation, raw_data):
    """
    Calcula a quantidade e o percentual de tutores que foram alocados 
    em escolas pertencentes a um de seus polos de preferência.
    Retorna um dicionário com os KPIs para exibição no Streamlit.
    """
    tutor_districts = raw_data.get('tutor_districts', {})
    school_districts = raw_data.get('school_districts', {})
    
    total_allocated = len(df_allocation)
    polo_matches = 0
    
    if total_allocated == 0:
        return {
            'Total_Alocados': 0,
            'Tutores_Polo_Preferido': 0,
            'Percentual_Polo_Preferido': 0.0
        }
        
    # Conta matches de polo via vetorização
    school_polos = df_allocation['Escola'].map(school_districts).fillna('')
    tutor_polos = df_allocation['Tutor Alocado'].map(tutor_districts)
    polo_matches = sum(
        sp and isinstance(tp, list) and sp in tp
        for sp, tp in zip(school_polos, tutor_polos)
    )
            
    # --- Cálculo e Retorno ---
    match_percentage = (polo_matches / total_allocated) * 100 if total_allocated > 0 else 0.0
    
    return {
        'Total_Alocados': total_allocated,
        'Tutores_Polo_Preferido': polo_matches,
        'Percentual_Polo_Preferido': match_percentage
    }

def analyze_preferences_matches(df_allocation, raw_data):
    """
    Analisa o nível de satisfação das alocações verificando se o tutor 
    foi colocado na sua 1ª, 2ª, 3ª opção ou fora das suas preferências diretas.
    Retorna um DataFrame com a contagem e percentual (ideal para gráficos no Streamlit).
    """
    preferences = raw_data.get('preferences', {})
    total_allocated = len(df_allocation)

    counts = {
        '1ª Opção': 0,
        '2ª Opção': 0,
        '3ª Opção': 0,
        'Fora das Preferências': 0
    }
    
    # Se não houver alocações, devolve a tabela zerada
    if total_allocated == 0:
        return pd.DataFrame([
            {'Categoria': k, 'Quantidade': 0, 'Percentual': 0.0}
            for k in counts.keys()
        ])
        
    # Descobre a posição da escola nas preferências do tutor (1, 2, 3) ou 0 se fora
    prefs_series = df_allocation['Tutor Alocado'].map(preferences)

    def _pref_position(prefs, school):
        if isinstance(prefs, list) and school in prefs:
            return prefs.index(school) + 1
        return 0

    positions = pd.Series(
        [_pref_position(p, s) for p, s in zip(prefs_series, df_allocation['Escola'])],
        index=df_allocation.index
    )

    counts['1ª Opção'] = (positions == 1).sum()
    counts['2ª Opção'] = (positions == 2).sum()
    counts['3ª Opção'] = (positions == 3).sum()
    counts['Fora das Preferências'] = (positions == 0).sum()
            
    # --- Construção do DataFrame de Resumo ---
    results = []
    for category, count in counts.items():
        percentage = (count / total_allocated) * 100
        results.append({
            'Categoria': category,
            'Quantidade': count,
            'Percentual': round(percentage, 2)
        })
        
    df_preferences_summary = pd.DataFrame(results)
    
    return df_preferences_summary

def analyze_cross_preferences(df_allocation, raw_data):
    """
    Realiza a Análise Cruzada para saber se o tutor ganhou a Escola, 
    apenas o Polo, ou nenhuma das duas preferências.
    """
    preferences = raw_data.get('preferences', {})
    tutor_districts = raw_data.get('tutor_districts', {})
    school_districts = raw_data.get('school_districts', {})
    
    counts = {
        'ESCOLA_PREFERIDA': 0,
        'POLO_PREFERIDO_APENAS': 0,
        'SEM_PREFERENCIA_ATENDIDA': 0
    }
    
    # Verifica match de escola, polo ou nenhum via vetorização
    prefs_series = df_allocation['Tutor Alocado'].map(preferences)
    tutor_polos_series = df_allocation['Tutor Alocado'].map(tutor_districts)
    school_polos = df_allocation['Escola'].map(school_districts).fillna('')

    school_match = pd.Series(
        isinstance(p, list) and s in p
        for p, s in zip(prefs_series, df_allocation['Escola'])
    )
    polo_match = ~school_match & pd.Series(
        sp and isinstance(tp, list) and sp in tp
        for sp, tp in zip(school_polos, tutor_polos_series)
    )

    counts['ESCOLA_PREFERIDA'] = school_match.sum()
    counts['POLO_PREFERIDO_APENAS'] = polo_match.sum()
    counts['SEM_PREFERENCIA_ATENDIDA'] = (~school_match & ~polo_match).sum()
            
    return counts

# =============================================================================
# FUNÇÕES DE EXPORTAÇÃO DAS MÉTRICAS
# =============================================================================

def _generate_detailed_report(df_allocation, raw_data, params):
    """Gera um DataFrame detalhado com o cálculo real das notas de cada alocação."""
    rows = []
    preferences = raw_data.get('preferences', {})
    distances = raw_data.get('distances', {})
    rankings = raw_data.get('rankings', {})
    
    base_multiplier = params.get('baseRanking', 10**9)
    total_tutors = len(raw_data.get('tutors', []))
    decrement = base_multiplier / total_tutors if total_tutors > 0 else 0

    # Identifica as escolas ativas nesta instância específica
    schools_file = params.get('arq_escolas')
    if isinstance(schools_file, str):
        df_instance_schools = pd.read_csv(schools_file)
    else:
        schools_file.seek(0)
        df_instance_schools = pd.read_csv(schools_file)
    school_col = 'Escola' if 'Escola' in df_instance_schools.columns else df_instance_schools.columns[0]
    active_schools = set(df_instance_schools[school_col].unique())

    # Calcula a média e a maior distância da matriz para os decaimentos (apenas escolas ativas e válidas)
    dist_values = [
        dist for (school_A, school_B), dist in distances.items() 
        if school_A in active_schools and school_B in active_schools and dist != float('inf') and dist > 0
    ]
    
    distance_mean = sum(dist_values) / len(dist_values) if dist_values else 9000
    max_distance = max(dist_values) if dist_values else 20000

    # Extrai colunas como arrays para evitar overhead do iterrows
    alloc_tutors = df_allocation['Tutor Alocado'].values
    alloc_schools = df_allocation['Escola'].values
    alloc_slots = df_allocation['Turno da Vaga'].values

    for i in range(len(df_allocation)):
        tutor = alloc_tutors[i]
        school = alloc_schools[i]
        time_slot = alloc_slots[i]

        tutor_rank = rankings.get(tutor, total_tutors)
        multiplier = max(base_multiplier - (tutor_rank - 1) * decrement, 1)
        tutor_prefs = preferences.get(tutor, [])

        if school in tutor_prefs:
            pref_pos = tutor_prefs.index(school) + 1
            base_score = params.get(f'pref{pref_pos}', 0)
            distance = None
        else:
            pref_pos = None
            ref_school = tutor_prefs[0] if tutor_prefs else None
            distance = distances.get((ref_school, school), float('inf'))

            if ref_school:
                calculated_dist = max_distance if distance == float('inf') else distance
                decay_type = params.get('decayType', 'sigmoid')
                
                if decay_type == 'linear':
                    base_pref = params.get('baseDistance', 5000)
                    base_score = max(0, base_pref * (1 - (calculated_dist / max_distance)))
                else: # Decaimento Sigmoidal
                    scale = params.get('sigmoidCurve', 2000)
                    base_pref = params.get('baseDistance', 5000)
                    base_score = base_pref / (1 + np.exp((calculated_dist - distance_mean) / scale))
            else:
                base_score = 0 # Tutores sem preferência alguma ganham base 0

        final_score = base_score * multiplier

        rows.append({
            'Tutor': tutor, 'Time_Slot': time_slot, 'Ranking': tutor_rank, 'Escola': school,
            'PrefPos': pref_pos, 'Distância': distance, 'Base': base_score, 'Mult': multiplier, 'Final': final_score
        })

    if not rows:
        return pd.DataFrame(columns=['Tutor', 'Time_Slot', 'Ranking', 'Escola', 'PrefPos', 'Distância', 'Base', 'Mult', 'Final'])

    return pd.DataFrame(rows).sort_values(['Ranking', 'Final'])

def _save_visual_charts(df_detailed, path):
    """Gera os gráficos das métricas."""
    plt.figure(figsize=(15, 4))

    total_allocated = len(df_detailed)

    # --- Gráfico de Preferências Atendidas ---
    plt.subplot(1, 3, 1)
    count_pref1 = len(df_detailed[df_detailed['PrefPos'] == 1])
    count_pref2 = len(df_detailed[df_detailed['PrefPos'] == 2])
    count_pref3 = len(df_detailed[df_detailed['PrefPos'] == 3])
    count_other_prefs = len(df_detailed[df_detailed['PrefPos'].isna()])
    
    pct_1 = (count_pref1 / total_allocated * 100) if total_allocated else 0
    pct_2 = (count_pref2 / total_allocated * 100) if total_allocated else 0
    pct_3 = (count_pref3 / total_allocated * 100) if total_allocated else 0
    pct_outras = (count_other_prefs / total_allocated * 100) if total_allocated else 0
    
    barras = plt.bar(['1ª Pref', '2ª Pref', '3ª Pref', 'Outras'], [pct_1, pct_2, pct_3, pct_outras])
    plt.title('Distribuição de Preferências Atendidas')
    plt.ylabel('Porcentagem (%)')

    for barra in barras:
        yval = barra.get_height()
        plt.text(barra.get_x() + barra.get_width()/2, yval + 1, f'{yval:.1f}%', ha='center', va='bottom')

    # --- Histograma de Distâncias (Apenas não-preferências válidas) ---
    plt.subplot(1, 3, 2)
    dist_non_pref = df_detailed[df_detailed['PrefPos'].isna()]['Distância']
    dist_numeric = pd.to_numeric(dist_non_pref, errors='coerce')
    dist_clean = dist_numeric.replace([np.inf, -np.inf], np.nan).dropna()
    
    if not dist_clean.empty:
        plt.hist(dist_clean, bins=20, edgecolor='black')
    plt.title('Distribuição de Distâncias (Não-Preferências)')
    plt.xlabel('Metros')

    # --- Dispersão Ranking vs Benefício ---
    plt.subplot(1, 3, 3)
    rankings_numeric = pd.to_numeric(df_detailed['Ranking'], errors='coerce')
    benefits_numeric = pd.to_numeric(df_detailed['Final'], errors='coerce')
    
    plt.scatter(rankings_numeric, benefits_numeric, alpha=0.5)
    plt.title('Benefício vs Posição no Ranking')
    plt.xlabel('Posição no Ranking')
    plt.ylabel('Benefício')

    plt.tight_layout()
    plt.savefig(os.path.join(path, 'graficos_resultados.png'), dpi=150, bbox_inches='tight')
    plt.close()

def _save_text_report(path, params, stats, df_detailed, df_unallocated, df_unfilled, polo_kpis, pref_summary, cross_analysis):
    """Gera um relatorio_metricas.txt."""
    total_allocated = len(df_detailed)
    
    total_benefit = df_detailed['Final'].sum() if total_allocated > 0 else 0
    avg_ranking = df_detailed['Ranking'].mean() if total_allocated > 0 else 0
    ideal_ranking = (1 + total_allocated) / 2 if total_allocated > 0 else 0
    equity_std_dev = df_detailed['Final'].std() if total_allocated > 1 else 0
    
    dist_non_pref = df_detailed[df_detailed['PrefPos'].isnull()]['Distância'].replace([np.inf, -np.inf], np.nan).dropna()
    avg_dist_non_pref = dist_non_pref.mean() if not dist_non_pref.empty else 0
    avg_scenario_dist = stats.get('avg_scenario_distance', 0)

    total_unallocated = len(df_unallocated)
    best_unallocated_rank = df_unallocated['Ranking'].min() if total_unallocated > 0 and 'Ranking' in df_unallocated else 'N/A'
    
    unallocated_reasons = df_unallocated['Motivo'].value_counts() if total_unallocated > 0 else {}
    rank_competition = unallocated_reasons.get('COMPETIÇÃO POR RANKING', 0)
    time_conflict = unallocated_reasons.get('CONFLITO DE DISPONIBILIDADE', 0)
    mixed_optimization = unallocated_reasons.get('INDETERMINADO / MISTO', 0)

    # Converte DataFrame de preferências em dicionário para lookup rápido
    pref_dict = dict(zip(pref_summary['Categoria'], zip(pref_summary['Quantidade'], pref_summary['Percentual'])))

    decay_type = params.get('decayType', 'sigmoid')
    decay_str = f"{decay_type} (Escala: {params.get('sigmoidCurve', 'N/A')})" if decay_type == 'sigmoid' else decay_type

    with open(os.path.join(path, 'relatorio_metricas.txt'), 'w', encoding='utf-8') as f:
        f.write("RELATÓRIO DE OTIMIZAÇÃO DE ALOCAÇÃO\n")
        f.write(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write("-" * 50 + "\n\n")
        
        f.write("[ CONFIGURAÇÕES DA SIMULAÇÃO ]\n")
        f.write(f"Motor     : Turnos ({params.get('shift_mode', 'N/A')}) | Decaimento ({decay_str})\n")
        f.write(f"Pesos     : 1ª Opção ({params.get('pref1', 0)}) | 2ª Opção ({params.get('pref2', 0)}) | 3ª Opção ({params.get('pref3', 0)})\n\n")
        
        f.write("[ RESULTADOS GERAIS ]\n")
        f.write(f"Vagas Ofertadas    : {stats.get('total_vacancies', 0)}\n")
        f.write(f"Vagas Preenchidas  : {stats.get('filled_vacancies', 0)}\n")
        if not df_unfilled.empty:
            f.write(f"Vagas Ociosas      : {df_unfilled['Vagas Sobrando'].sum()} (Verificar CSV de vagas não preenchidas)\n")
        f.write(f"Tutores De Fora    : {total_unallocated}\n\n")
        
        f.write(f"[ QUALIDADE DA ALOCAÇÃO (Base: {total_allocated} alocados) ]\n")
        f.write(f"Benefício Total    : {total_benefit:,.2f}\n")
        f.write(f"Ranking Médio      : {avg_ranking:.1f} (Cenário Ideal: {ideal_ranking:.1f})\n")
        f.write(f"Desvio Padrão      : {equity_std_dev:,.2f}\n")
        f.write(f"Distância Média    : {avg_dist_non_pref:.2f} m (Cenário Base: {avg_scenario_dist:.2f} m)\n\n")
        
        f.write("[ ATENDIMENTO DE PREFERÊNCIAS (ESCOLAS) ]\n")
        f.write(f"1ª Opção           : {pref_dict.get('1ª Opção', (0,0))[0]:>3} ({pref_dict.get('1ª Opção', (0,0))[1]:>5.1f}%)\n")
        f.write(f"2ª Opção           : {pref_dict.get('2ª Opção', (0,0))[0]:>3} ({pref_dict.get('2ª Opção', (0,0))[1]:>5.1f}%)\n")
        f.write(f"3ª Opção           : {pref_dict.get('3ª Opção', (0,0))[0]:>3} ({pref_dict.get('3ª Opção', (0,0))[1]:>5.1f}%)\n")
        f.write(f"Fora das Opções    : {pref_dict.get('Fora das Preferências', (0,0))[0]:>3} ({pref_dict.get('Fora das Preferências', (0,0))[1]:>5.1f}%)\n\n")

        f.write("[ ATENDIMENTO DE POLOS E ANÁLISE CRUZADA ]\n")
        f.write(f"Sucesso de Polo    : {polo_kpis.get('Percentual_Polo_Preferido', 0):.1f}% ({polo_kpis.get('Tutores_Polo_Preferido', 0)} tutores)\n")
        f.write(f"Match Escola       : {(cross_analysis.get('ESCOLA_PREFERIDA', 0)/total_allocated)*100 if total_allocated else 0:.1f}%\n")
        f.write(f"Match Só Polo      : {(cross_analysis.get('POLO_PREFERIDO_APENAS', 0)/total_allocated)*100 if total_allocated else 0:.1f}%\n")
        f.write(f"Sem Match Nenhum   : {(cross_analysis.get('SEM_PREFERENCIA_ATENDIDA', 0)/total_allocated)*100 if total_allocated else 0:.1f}%\n\n")

        if total_unallocated > 0:
            f.write(f"[ DIAGNÓSTICO DOS {total_unallocated} NÃO ALOCADOS ]\n")
            f.write(f"Melhor Ranking de Fora      : {best_unallocated_rank}\n")
            f.write(f"Competição por Ranking      : {rank_competition} ({(rank_competition/total_unallocated)*100:.1f}%)\n")
            f.write(f"Conflito de Disponibilidade : {time_conflict} ({(time_conflict/total_unallocated)*100:.1f}%)\n")
            f.write(f"Otimização Global (Misto)   : {mixed_optimization} ({(mixed_optimization/total_unallocated)*100:.1f}%)\n")

def get_summary_metrics(df_allocation, raw_data):
    """.
    Retorna apenas os DataFrames e dicionários para exibição no STREAMLIT.
    """
    return {
        'unallocated': analyze_unallocated_tutors(df_allocation, raw_data),
        'unfilled_vacancies': analyze_unfilled_vacancies(df_allocation, raw_data),
        'polo_kpis': analyze_polo_matches(df_allocation, raw_data),
        'preferences_summary': analyze_preferences_matches(df_allocation, raw_data)
    }

def export_local_reports(allocation_result, params, base_path='alocacoes/'):
    """
    Gera exatamente os 6 arquivos e o histórico.
    """
    df_allocation = allocation_result['dataframe']
    raw_data = allocation_result['raw_data']
    stats = allocation_result['stats']

    # Lê o arquivo de escolas desta instância específica para isolar as escolas ativas
    schools_file = params.get('arq_escolas')
    if isinstance(schools_file, str):
        df_instance_schools = pd.read_csv(schools_file)
    else:
        schools_file.seek(0)
        df_instance_schools = pd.read_csv(schools_file)
    school_col = 'Escola' if 'Escola' in df_instance_schools.columns else df_instance_schools.columns[0]
    active_schools = set(df_instance_schools[school_col].unique())

    # Calcula a Distância Média da Instância (apenas entre escolas ativas nessa instância e com distâncias válidas)
    distances = raw_data.get('distances', {})

    dist_values = [
        dist for (school_A, school_B), dist in distances.items() 
        if school_A in active_schools and school_B in active_schools and dist != float('inf') and dist > 0
    ]
    
    distance_mean = sum(dist_values) / len(dist_values) if dist_values else 0
    stats['avg_scenario_distance'] = distance_mean

    # Define o nome da pasta com base no ID da Instância
    instance_id = params.get('Instancia_ID', 'Default_Run')
    output_path = os.path.join(base_path, instance_id)
    os.makedirs(output_path, exist_ok=True)

    # Gera todos os DataFrames de métricas
    df_unallocated = analyze_unallocated_tutors(df_allocation, raw_data)
    df_unfilled = analyze_unfilled_vacancies(df_allocation, raw_data)
    polo_kpis = analyze_polo_matches(df_allocation, raw_data)
    pref_summary = analyze_preferences_matches(df_allocation, raw_data)
    cross_analysis = analyze_cross_preferences(df_allocation, raw_data)
    
    df_detailed = _generate_detailed_report(df_allocation, raw_data, params)

    df_allocation.to_csv(os.path.join(output_path, 'alocacoes.csv'), index=False)
    df_unallocated.to_csv(os.path.join(output_path, 'relatorio_nao_alocados.csv'), index=False)
    df_unfilled.to_csv(os.path.join(output_path, 'relatorio_vagas_nao_preenchidas.csv'), index=False)
    df_detailed.to_csv(os.path.join(output_path, 'report_alocacao.csv'), index=False)

    _save_visual_charts(df_detailed, output_path)

    _save_text_report(output_path, params, stats, df_detailed, df_unallocated, df_unfilled, polo_kpis, pref_summary, cross_analysis)

    _update_general_history(base_path, params, stats, df_detailed, df_unallocated, polo_kpis, cross_analysis)

    print(f"✅ Bateria de relatórios criados com sucesso em: {output_path}")
    return output_path

def _update_general_history(base_path, params, stats, df_detailed, df_unallocated, polo_kpis, cross_analysis):
    """Gera o arquivo historico_alocacoes.csv."""
    history_file = os.path.join(base_path, 'historico_alocacoes.csv')
    
    total_allocated = len(df_detailed)
    total_benefit = df_detailed['Final'].sum() if total_allocated > 0 else 0
    avg_ranking = df_detailed['Ranking'].mean() if total_allocated > 0 else 0
    ideal_ranking = (1 + total_allocated) / 2 if total_allocated > 0 else 0
    equity_std_dev = df_detailed['Final'].std() if total_allocated > 1 else 0

    dist_non_pref = df_detailed[df_detailed['PrefPos'].isnull()]['Distância'].replace([np.inf, -np.inf], np.nan).dropna()
    avg_dist_non_pref = dist_non_pref.mean() if not dist_non_pref.empty else 0

    count_pref1 = len(df_detailed[df_detailed['PrefPos'] == 1])
    count_pref2 = len(df_detailed[df_detailed['PrefPos'] == 2])
    count_pref3 = len(df_detailed[df_detailed['PrefPos'] == 3])
    count_other_prefs = len(df_detailed[df_detailed['PrefPos'].isnull()])

    total_unallocated = len(df_unallocated)
    best_unallocated_rank = df_unallocated['Ranking'].min() if total_unallocated > 0 and 'Ranking' in df_unallocated else 'N/A'
    
    unallocated_reasons = df_unallocated['Motivo'].value_counts() if total_unallocated > 0 else {}
    rank_competition = unallocated_reasons.get('COMPETIÇÃO POR RANKING', 0)
    time_conflict = unallocated_reasons.get('CONFLITO DE DISPONIBILIDADE', 0)
    mixed_optimization = unallocated_reasons.get('INDETERMINADO / MISTO', 0)

    new_entry = {
        'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'Instance_ID': params.get('Instancia_ID', 'N/A'),
        
        # Parâmetros
        'Shift_Mode': params.get('shift_mode', ''),
        'Decay_Type': params.get('decayType', ''),
        'Score_Pref1': params.get('pref1', 0),
        'Score_Pref2': params.get('pref2', 0),
        'Score_Pref3': params.get('pref3', 0),
        'Base_Distance': params.get('baseDistance', 0),
        'Ranking_Multiplier': params.get('baseRanking', 0),
        'Sigmoid_Scale': params.get('sigmoidCurve', 0),
        
        # Métricas Gerais
        'Total_Vacancies': stats.get('total_vacancies', 0),
        'Allocated_Tutors': stats.get('filled_vacancies', 0),
        'Fill_Rate_Pct': (stats.get('filled_vacancies', 0) / stats.get('total_vacancies', 1)) * 100 if stats.get('total_vacancies', 0) else 0,
        
        # Qualidade da Alocação
        'Total_Benefit': total_benefit,
        'Avg_Ranking': avg_ranking,
        'Ideal_Ranking': ideal_ranking,
        'Std_Dev_Benefit': equity_std_dev,
        'Avg_Distance_Non_Pref': avg_dist_non_pref,
        'Avg_Scenario_Distance': stats.get('avg_scenario_distance', 0),
        
        # Satisfação
        'Count_Pref_1': count_pref1,
        'Count_Pref_2': count_pref2,
        'Count_Pref_3': count_pref3,
        'Count_Non_Pref': count_other_prefs,
        'Pct_Pref_1': (count_pref1 / total_allocated * 100) if total_allocated else 0,
        'Pct_Pref_2': (count_pref2 / total_allocated * 100) if total_allocated else 0,
        'Pct_Pref_3': (count_pref3 / total_allocated * 100) if total_allocated else 0,
        'Pct_Non_Pref': (count_other_prefs / total_allocated * 100) if total_allocated else 0,
        
        # Análise Cruzada e Polos
        'Count_Polo_Match': polo_kpis.get('Tutores_Polo_Preferido', 0),
        'Pct_Polo_Match': polo_kpis.get('Percentual_Polo_Preferido', 0),
        'Count_Cross_School_Match': cross_analysis.get('ESCOLA_PREFERIDA', 0),
        'Pct_Cross_School_Match': (cross_analysis.get('ESCOLA_PREFERIDA', 0) / total_allocated * 100) if total_allocated else 0,
        'Count_Cross_Polo_Only': cross_analysis.get('POLO_PREFERIDO_APENAS', 0),
        'Pct_Cross_Polo_Only': (cross_analysis.get('POLO_PREFERIDO_APENAS', 0) / total_allocated * 100) if total_allocated else 0,
        'Count_Cross_None': cross_analysis.get('SEM_PREFERENCIA_ATENDIDA', 0),
        'Pct_Cross_None': (cross_analysis.get('SEM_PREFERENCIA_ATENDIDA', 0) / total_allocated * 100) if total_allocated else 0,

        # Não Alocados
        'Unallocated_Tutors': total_unallocated,
        'Unalloc_Rank_Comp': rank_competition,
        'Pct_Unalloc_Rank_Comp': (rank_competition / total_unallocated * 100) if total_unallocated else 0,
        'Unalloc_Time_Conflict': time_conflict,
        'Pct_Unalloc_Time_Conflict': (time_conflict / total_unallocated * 100) if total_unallocated else 0,
        'Unalloc_Optimization': mixed_optimization,
        'Pct_Unalloc_Optimization': (mixed_optimization / total_unallocated * 100) if total_unallocated else 0,
        'Best_Unalloc_Rank': best_unallocated_rank
    }
    
    df_new = pd.DataFrame([new_entry])
    
    if os.path.exists(history_file):
        df_hist = pd.read_csv(history_file)
        
        # Verifica qual é a instância atual (ex: 'I0')
        instancia_atual = params.get('Instancia_ID', 'N/A')
        
        # Remove a linha antiga da mesma instância, se existir, para evitar duplicatas
        if 'Instance_ID' in df_hist.columns and instancia_atual in df_hist['Instance_ID'].values:
            df_hist = df_hist[df_hist['Instance_ID'] != instancia_atual]
            
        df_hist = pd.concat([df_hist, df_new], ignore_index=True)
    else:
        df_hist = df_new
        
    df_hist.to_csv(history_file, index=False)
