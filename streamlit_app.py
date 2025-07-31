import streamlit as st
import folium
import pandas as pd
import numpy as np
from streamlit_folium import st_folium
import requests
from datetime import datetime
import zipfile
import io
import random

# ⚙️ Configurações
st.set_page_config(
    page_title="Sistema Inteligente de Rotas", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 CSS personalizado para interface mais bonita
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #FF6B6B, #4ECDC4);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        color: white;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #FF6B6B;
    }
    .risk-toggle {
        background: #FF4444;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# 🌎 Base de cidades com coordenadas e informações de risco
CIDADES_BASE = {
    "São Paulo": {
        "coords": (-23.5505, -46.6333),
        "pop": 12400000,
        "risco_base": 0.6,
        "principais_brs": [116, 381, 374]
    },
    "Rio de Janeiro": {
        "coords": (-22.9068, -43.1729),
        "pop": 6700000,
        "risco_base": 0.7,
        "principais_brs": [116, 40, 101]  # BR-040 corrigido para 40
    },
    "Belo Horizonte": {
        "coords": (-19.9167, -43.9345),
        "pop": 2500000,
        "risco_base": 0.4,
        "principais_brs": [381, 40, 262]  # BR-040 corrigido para 40
    },
    "Campinas": {
        "coords": (-22.9056, -47.0608),
        "pop": 1200000,
        "risco_base": 0.3,
        "principais_brs": [348, 374]
    },
    "São José dos Campos": {
        "coords": (-23.1896, -45.8841),
        "pop": 700000,
        "risco_base": 0.25,
        "principais_brs": [116]
    },
    "Sorocaba": {
        "coords": (-23.5015, -47.4526),
        "pop": 650000,
        "risco_base": 0.35,
        "principais_brs": [374]
    },
    "Santos": {
        "coords": (-23.9618, -46.3322),
        "pop": 430000,
        "risco_base": 0.5,
        "principais_brs": [101, 116]
    },
    "Guarulhos": {
        "coords": (-23.4536, -46.5228),
        "pop": 1400000,
        "risco_base": 0.45,
        "principais_brs": [116]
    }
}

# 🛣️ Definição de rotas possíveis com dados reais
ROTAS_POSSIVEIS = {
    ("São Paulo", "Rio de Janeiro"): {
        "distancia": 435,
        "tempo_medio": "5h30min",
        "principais_brs": [116],
        "pedagios": 12,
        "pontos_risco": [
            {"nome": "Região de Queluz", "coords": (-22.5320, -44.7736), "risco": 0.8},
            {"nome": "Serra das Araras", "coords": (-22.7039, -43.6828), "risco": 0.6},
            {"nome": "Dutra - Jacareí", "coords": (-23.3055, -45.9663), "risco": 0.7}
        ]
    },
    ("São Paulo", "Belo Horizonte"): {
        "distancia": 586,
        "tempo_medio": "7h15min",
        "principais_brs": [381],
        "pedagios": 8,
        "pontos_risco": [
            {"nome": "Região de Poços de Caldas", "coords": (-21.7887, -46.5651), "risco": 0.5},
            {"nome": "Fernão Dias - Atibaia", "coords": (-23.1169, -46.5500), "risco": 0.6}
        ]
    },
    ("São Paulo", "Campinas"): {
        "distancia": 96,
        "tempo_medio": "1h20min",
        "principais_brs": [348],
        "pedagios": 3,
        "pontos_risco": [
            {"nome": "Região de Jundiaí", "coords": (-23.1864, -46.8842), "risco": 0.4}
        ]
    },
    ("Rio de Janeiro", "Belo Horizonte"): {
        "distancia": 441,
        "tempo_medio": "6h00min",
        "principais_brs": [40],  # BR-040 corrigido
        "pedagios": 6,
        "pontos_risco": [
            {"nome": "BR-040 Juiz de Fora", "coords": (-21.7642, -43.3503), "risco": 0.5},
            {"nome": "Região de Petrópolis", "coords": (-22.5097, -43.1756), "risco": 0.6}
        ]
    }
}

# 📊 Função para carregar e processar dados do DataTran
@st.cache_data
def carregar_datatran():
    """Carrega dados do arquivo datatran2025.zip automaticamente"""
    try:
        # Primeiro, tentar carregar do arquivo local no projeto
        if os.path.exists('datatran2025.zip'):
            with zipfile.ZipFile('datatran2025.zip') as zip_file:
                for filename in zip_file.namelist():
                    if filename.endswith(('.csv', '.xlsx')):
                        with zip_file.open(filename) as file:
                            if filename.endswith('.csv'):
                                # Tentar diferentes encodings para CSV
                                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'utf-8-sig']
                                
                                for encoding in encodings:
                                    try:
                                        file.seek(0)
                                        df = pd.read_csv(file, encoding=encoding, sep=';')
                                        st.success(f"✅ DataTran carregado automaticamente (encoding: {encoding})")
                                        return df
                                    except UnicodeDecodeError:
                                        continue
                                    except Exception:
                                        try:
                                            file.seek(0)
                                            df = pd.read_csv(file, encoding=encoding, sep=',')
                                            st.success(f"✅ DataTran carregado automaticamente (encoding: {encoding})")
                                            return df
                                        except:
                                            continue
                            else:
                                df = pd.read_excel(file)
                                st.success("✅ DataTran carregado automaticamente (Excel)")
                                return df
        
        # Se não encontrou arquivo local, tentar do upload
        if 'datatran2025.zip' in st.session_state:
            with zipfile.ZipFile(st.session_state['datatran2025.zip']) as zip_file:
                for filename in zip_file.namelist():
                    if filename.endswith(('.csv', '.xlsx')):
                        with zip_file.open(filename) as file:
                            if filename.endswith('.csv'):
                                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'utf-8-sig']
                                for encoding in encodings:
                                    try:
                                        file.seek(0)
                                        df = pd.read_csv(file, encoding=encoding, sep=';')
                                        st.success(f"✅ DataTran carregado do upload (encoding: {encoding})")
                                        return df
                                    except UnicodeDecodeError:
                                        continue
                                    except Exception:
                                        try:
                                            file.seek(0)
                                            df = pd.read_csv(file, encoding=encoding, sep=',')
                                            st.success(f"✅ DataTran carregado do upload (encoding: {encoding})")
                                            return df
                                        except:
                                            continue
                            else:
                                df = pd.read_excel(file)
                                st.success("✅ DataTran carregado do upload (Excel)")
                                return df
        
        st.warning("⚠️ Arquivo datatran2025.zip não encontrado - usando dados simulados")
        return None
        
    except Exception as e:
        st.error(f"Erro ao carregar DataTran: {e}")
        return None

# 🔍 Função para geocodificar endereços usando Nominatim (gratuito)
@st.cache_data(ttl=3600)  # Cache por 1 hora
def geocodificar_endereco(endereco):
    """Converte endereço em coordenadas usando Nominatim (OpenStreetMap)"""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': f"{endereco}, Brasil",
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        headers = {
            'User-Agent': 'Sistema-Rotas-App/1.0'  # Nominatim exige User-Agent
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                resultado = data[0]
                return {
                    'lat': float(resultado['lat']),
                    'lon': float(resultado['lon']),
                    'display_name': resultado['display_name'],
                    'cidade': resultado.get('address', {}).get('city', endereco),
                    'status': 'sucesso'
                }
        
        return {'status': 'erro', 'message': 'Endereço não encontrado'}
        
    except Exception as e:
        return {'status': 'erro', 'message': f'Erro na geocodificação: {str(e)[:50]}...'}

# 🗺️ Função para obter rota real seguindo estradas
@st.cache_data(ttl=3600)  # Cache por 1 hora
def obter_rota_real_estradas(origem_coords, destino_coords):
    """Obtém rota real seguindo estradas usando OpenRouteService (gratuito)"""
    try:
        # Usar OpenRouteService (5000 requests/dia gratuitos)
        # Alternativa: usar OSRM (completamente gratuito)
        
        # OSRM (Open Source Routing Machine) - Completamente gratuito
        url = "http://router.project-osrm.org/route/v1/driving/"
        coords = f"{origem_coords[1]},{origem_coords[0]};{destino_coords[1]},{destino_coords[0]}"
        params = {
            'overview': 'full',
            'geometries': 'geojson',
            'steps': 'true'
        }
        
        response = requests.get(f"{url}{coords}", params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if data['code'] == 'Ok' and len(data['routes']) > 0:
                route = data['routes'][0]
                
                # Extrair coordenadas da rota
                coordinates = route['geometry']['coordinates']
                # OSRM retorna [lon, lat], precisamos [lat, lon] para folium
                rota_coords = [(coord[1], coord[0]) for coord in coordinates]
                
                return {
                    'coordenadas': rota_coords,
                    'distancia_real': round(route['distance'] / 1000, 1),  # metros para km
                    'tempo_real': round(route['duration'] / 60, 0),  # segundos para minutos
                    'status': 'sucesso',
                    'fonte': 'OSRM (estradas reais)'
                }
        
        # Fallback: se OSRM falhar, tentar GraphHopper (também gratuito)
        return obter_rota_graphhopper(origem_coords, destino_coords)
        
    except Exception as e:
        return {
            'status': 'erro',
            'message': f'Erro no roteamento: {str(e)[:50]}...',
            'coordenadas': [origem_coords, destino_coords],  # Linha reta como fallback
            'distancia_real': None,
            'tempo_real': None
        }

@st.cache_data(ttl=3600)
def obter_rota_graphhopper(origem_coords, destino_coords):
    """Fallback usando GraphHopper (também gratuito, mas com limite menor)"""
    try:
        url = "https://graphhopper.com/api/1/route"
        params = {
            'point': [f"{origem_coords[0]},{origem_coords[1]}", f"{destino_coords[0]},{destino_coords[1]}"],
            'vehicle': 'car',
            'locale': 'pt-BR',
            'calc_points': 'true',
            'type': 'json'
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if len(data['paths']) > 0:
                path = data['paths'][0]
                
                # Decodificar coordenadas (GraphHopper usa encoding especial)
                points = path.get('points', {})
                if 'coordinates' in points:
                    # Coordenadas já decodificadas
                    coordinates = points['coordinates']
                    rota_coords = [(coord[1], coord[0]) for coord in coordinates]  # [lon,lat] -> [lat,lon]
                else:
                    # Usar apenas origem e destino
                    rota_coords = [origem_coords, destino_coords]
                
                return {
                    'coordenadas': rota_coords,
                    'distancia_real': round(path['distance'] / 1000, 1),
                    'tempo_real': round(path['time'] / 60000, 0),  # ms para minutos
                    'status': 'sucesso',
                    'fonte': 'GraphHopper (estradas reais)'
                }
    
    except Exception:
        pass
    
    # Último fallback: linha reta
    return {
        'status': 'fallback',
        'coordenadas': [origem_coords, destino_coords],
        'distancia_real': None,
        'tempo_real': None,
        'fonte': 'Linha reta (fallback)'
    }
def criar_rota_personalizada(origem_coords, destino_coords, origem_nome, destino_nome):
    """Calcula rota real seguindo estradas entre coordenadas personalizadas"""
    
    # Obter rota real seguindo estradas
    rota_real = obter_rota_real_estradas(origem_coords, destino_coords)
    
    if rota_real['status'] == 'sucesso':
        # Usar dados reais da API de roteamento
        distancia = rota_real['distancia_real']
        tempo_minutos = rota_real['tempo_real']
        tempo_formatado = f"{int(tempo_minutos // 60)}h{int(tempo_minutos % 60)}min" if tempo_minutos >= 60 else f"{int(tempo_minutos)}min"
        coordenadas_rota = rota_real['coordenadas']
        fonte_info = rota_real['fonte']
    else:
        # Fallback: cálculo manual (Haversine)
        from math import radians, cos, sin, asin, sqrt
        
        def haversine(lon1, lat1, lon2, lat2):
            lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * asin(sqrt(a))
            r = 6371  # Raio da Terra em km
            return c * r
        
        distancia = round(haversine(origem_coords[1], origem_coords[0], destino_coords[1], destino_coords[0]), 1)
        tempo_estimado = distancia / 60  # Velocidade média urbana 60 km/h
        tempo_formatado = f"{int(tempo_estimado)}h{int((tempo_estimado % 1) * 60)}min"
        coordenadas_rota = [origem_coords, destino_coords]  # Linha reta
        fonte_info = "Estimativa (linha reta)"
    
    return {
        'distancia': distancia,
        'tempo_estimado': tempo_formatado,
        'origem_nome': origem_nome,
        'destino_nome': destino_nome,
        'origem_coords': origem_coords,
        'destino_coords': destino_coords,
        'coordenadas_rota': coordenadas_rota,  # Coordenadas da rota real
        'fonte_roteamento': fonte_info,
        'personalizada': True
    }
# 🔍 Função para gerar explicação inteligente do risco
def gerar_explicacao_risco(ponto_risco, df_datatran=None):
    """Gera explicação detalhada baseada nos dados REAIS do DataTran"""
    
    risco = ponto_risco.get("risco", 0.3)
    detalhes = ponto_risco.get("detalhes", {})
    nome = ponto_risco.get("nome", "Ponto de Risco")
    
    # Análise REAL dos dados do DataTran
    fatores_identificados = []
    tipo_problema = "trânsito/acidentes"  # Padrão: problemas de trânsito
    recomendacoes = []
    
    # 1. ANÁLISE DE MORTALIDADE/GRAVIDADE
    mortos = detalhes.get('mortos', 0)
    feridos_graves = detalhes.get('feridos_graves', 0)
    feridos_leves = detalhes.get('feridos_leves', 0)
    total_feridos = detalhes.get('feridos', feridos_graves + feridos_leves)
    
    if mortos > 0:
        fatores_identificados.append(f"💀 {mortos} morte(s) em acidentes de trânsito")
        tipo_problema = "acidentes fatais"
        recomendacoes.append("🚨 ATENÇÃO MÁXIMA: Local com acidentes mortais")
    
    if feridos_graves > 0:
        fatores_identificados.append(f"🏥 {feridos_graves} ferido(s) grave(s)")
        recomendacoes.append("⚠️ Risco alto de acidentes severos")
    
    if feridos_leves > 0:
        fatores_identificados.append(f"🩹 {feridos_leves} ferido(s) leve(s)")
    
    # 2. ANÁLISE DO TIPO DE ACIDENTE
    tipo_acidente = str(detalhes.get('tipo_acidente', '')).lower()
    if tipo_acidente and tipo_acidente != 'n/a':
        fatores_identificados.append(f"💥 Tipo: {detalhes.get('tipo_acidente', 'N/A')}")
        
        if any(palavra in tipo_acidente for palavra in ['tombamento', 'capotamento']):
            recomendacoes.append("🔄 CUIDADO: Curvas perigosas ou velocidade excessiva")
            recomendacoes.append("🐌 Reduzir velocidade significativamente")
        elif any(palavra in tipo_acidente for palavra in ['colisão', 'choque']):
            recomendacoes.append("👀 ATENÇÃO: Manter distância segura")
            recomendacoes.append("🚦 Cuidado em cruzamentos e ultrapassagens")
        elif 'atropelamento' in tipo_acidente:
            recomendacoes.append("🚶 PERIGO: Área com pedestres")
            recomendacoes.append("👀 Atenção redobrada para pessoas na via")
    
    # 3. ANÁLISE DA CAUSA DO ACIDENTE
    causa_acidente = str(detalhes.get('causa_acidente', '')).lower()
    if causa_acidente and causa_acidente != 'n/a':
        if any(palavra in causa_acidente for palavra in ['velocidade', 'excesso']):
            fatores_identificados.append("🏎️ Causa: Velocidade excessiva")
            recomendacoes.append("🐌 REDUZIR VELOCIDADE obrigatoriamente")
        elif any(palavra in causa_acidente for palavra in ['sono', 'fadiga', 'cansaço']):
            fatores_identificados.append("😴 Causa: Sono/fadiga do condutor")
            recomendacoes.append("☕ Fazer pausas frequentes para descanso")
        elif any(palavra in causa_acidente for palavra in ['chuva', 'pista molhada']):
            fatores_identificados.append("🌧️ Causa: Condições climáticas adversas")
            recomendacoes.append("🌧️ Cuidado extra em dias chuvosos")
        elif any(palavra in causa_acidente for palavra in ['ultrapassagem', 'conversão']):
            fatores_identificados.append("🔄 Causa: Manobras perigosas")
            recomendacoes.append("🚫 Evitar ultrapassagens arriscadas")
    
    # 4. ANÁLISE DE CONDIÇÕES DA VIA
    condicao_meteorologica = str(detalhes.get('condicao_metereologica', '')).lower()
    if 'chuva' in condicao_meteorologica:
        fatores_identificados.append("🌧️ Acidentes em condições de chuva")
        recomendacoes.append("☔ Extremo cuidado em dias chuvosos")
    
    tipo_pista = str(detalhes.get('tipo_pista', '')).lower()
    if 'simples' in tipo_pista:
        fatores_identificados.append("🛣️ Pista simples (mão dupla)")
        recomendacoes.append("↔️ Atenção: ultrapassagens em pista dupla")
    elif 'dupla' in tipo_pista:
        fatores_identificados.append("🛣️ Pista dupla")
    
    # 5. CLASSIFICAÇÃO DE RISCO BASEADA EM DADOS REAIS
    if risco >= 0.8:
        classificacao = "🔴 CRÍTICO"
        explicacao_geral = f"Este local tem ALTÍSSIMA incidência de acidentes de trânsito"
        if mortos > 0:
            explicacao_geral += f" com {mortos} morte(s) registrada(s)"
    elif risco >= 0.6:
        classificacao = "🟠 ALTO RISCO"
        explicacao_geral = f"Este local apresenta ALTO índice de acidentes"
        explicacao_geral += f" ({total_feridos} vítimas registradas)" if total_feridos > 0 else ""
    elif risco >= 0.4:
        classificacao = "🟡 RISCO MODERADO"
        explicacao_geral = f"Este local tem ocorrências moderadas de acidentes"
    else:
        classificacao = "🟢 RISCO BAIXO"
        explicacao_geral = f"Este local tem baixo histórico de acidentes"
    
    # 6. RECOMENDAÇÕES ESPECÍFICAS PARA TRÂNSITO (não criminalidade)
    recomendacoes_gerais = []
    
    if risco >= 0.7:
        recomendacoes_gerais.extend([
            "🚨 LOCAL PERIGOSO - máxima atenção",
            "🐌 Velocidade reduzida obrigatória",
            "👥 Evitar viajar com sono ou cansaço",
            "📱 GPS ativo para rotas alternativas"
        ])
    elif risco >= 0.5:
        recomendacoes_gerais.extend([
            "⚠️ Atenção redobrada necessária",
            "🚗 Manter veículo em perfeito estado",
            "👀 Não usar celular ao dirigir",
            "⛽ Combustível suficiente"
        ])
    else:
        recomendacoes_gerais.extend([
            "✅ Trânsito relativamente seguro",
            "🚗 Precauções normais de direção",
            "📍 Respeitar sinalização local"
        ])
    
    # 7. MONTAR EXPLICAÇÃO FOCADA EM DADOS REAIS
    explicacao_completa = f"""
<div style='max-width: 400px; font-size: 12px; line-height: 1.4;'>
    <h4 style='margin: 5px 0; color: #333;'>📍 {nome}</h4>
    <h5 style='margin: 5px 0;'>{classificacao} - Índice: {risco:.2f}</h5>
    
    <p style='margin: 5px 0; font-weight: bold; color: #d63384;'>{explicacao_geral}</p>
    
    <h6 style='margin: 8px 0 3px 0; color: #dc3545;'>📊 DADOS IDENTIFICADOS:</h6>
    <ul style='margin: 0; padding-left: 15px; font-size: 11px;'>
"""
    
    # Adicionar fatores reais identificados
    if fatores_identificados:
        for fator in fatores_identificados[:5]:  # Limitar para não ficar muito grande
            explicacao_completa += f"<li>{fator}</li>"
    else:
        explicacao_completa += "<li>📈 Baseado em análise estatística regional</li>"
    
    # Adicionar informações da localização
    municipio = detalhes.get('municipio', 'N/A')
    if municipio != 'N/A':
        explicacao_completa += f"<li>📍 Município: {municipio}</li>"
    
    explicacao_completa += f"""
    </ul>
    
    <h6 style='margin: 8px 0 3px 0; color: #fd7e14;'>⚠️ PRECAUÇÕES RECOMENDADAS:</h6>
    <ul style='margin: 0; padding-left: 15px; font-size: 11px;'>
"""
    
    # Combinar recomendações específicas e gerais
    todas_recomendacoes = recomendacoes + recomendacoes_gerais
    for rec in todas_recomendacoes[:6]:  # Máximo 6 recomendações
        explicacao_completa += f"<li>{rec}</li>"
    
    explicacao_completa += f"""
    </ul>
    
    <div style='margin: 8px 0; padding: 5px; background: #f8f9fa; border-left: 3px solid #0d6efd;'>
        <strong>💡 SOBRE OS DADOS:</strong><br>
        <span style='font-size: 10px;'>
        Análise baseada em registros reais de acidentes do DataTran/PRF. 
        Este local apresenta padrão de <strong>{tipo_problema}</strong> que requer atenção especial.
        </span>
    </div>
</div>
"""
    
    return explicacao_completa
def calcular_pontos_risco_reais(df_datatran, rota_info):
    """Calcula pontos de risco baseado nos dados reais do DataTran"""
    pontos_risco = []
    
    if df_datatran is not None:
        # Filtrar acidentes nas BRs da rota
        for br in rota_info["principais_brs"]:
            acidentes_br = df_datatran[df_datatran['br'] == br]
            
            if not acidentes_br.empty:
                # Agrupar por coordenadas aproximadas para criar clusters de risco
                for _, acidente in acidentes_br.sample(min(10, len(acidentes_br))).iterrows():
                    # Verificar se as coordenadas são válidas
                    lat = acidente.get('latitude')
                    lon = acidente.get('longitude')
                    
                    # Validar coordenadas
                    if (pd.notna(lat) and pd.notna(lon) and 
                        isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and
                        -90 <= lat <= 90 and -180 <= lon <= 180):
                        
                        # Calcular nível de risco baseado na gravidade
                        risco = 0.3  # Base
                        if 'mortos' in acidente and pd.notna(acidente['mortos']) and acidente['mortos'] > 0:
                            risco += 0.4
                        if 'feridos_graves' in acidente and pd.notna(acidente['feridos_graves']) and acidente['feridos_graves'] > 0:
                            risco += 0.2
                        if 'condicao_metereologica' in acidente and pd.notna(acidente['condicao_metereologica']):
                            if 'chuva' in str(acidente['condicao_metereologica']).lower():
                                risco += 0.1
                        
                        pontos_risco.append({
                            "nome": f"BR-{br} KM {acidente.get('km', '?')}",
                            "coords": (float(lat), float(lon)),  # Garantir que são float
                            "risco": min(risco, 1.0),
                            "detalhes": {
                                "municipio": str(acidente.get('municipio', 'N/A'))[:50],  # Limitar tamanho
                                "tipo_acidente": str(acidente.get('tipo_acidente', 'N/A'))[:50],
                                "mortos": int(acidente.get('mortos', 0)) if pd.notna(acidente.get('mortos')) else 0,
                                "feridos": int(acidente.get('feridos', 0)) if pd.notna(acidente.get('feridos')) else 0
                            }
                        })
    
    # Se não tem dados reais suficientes, usar pontos simulados da rota
    if len(pontos_risco) < 2:
        pontos_risco.extend(rota_info.get("pontos_risco", []))
    
    return pontos_risco

# 🗺️ Função para criar mapa interativo
def criar_mapa_rotas(rotas_selecionadas, mostrar_riscos, df_datatran):
    """Cria mapa com múltiplas rotas e pontos de risco"""
    
    # Centro do Brasil (aproximadamente)
    mapa = folium.Map(
        location=[-23.5505, -46.6333],
        zoom_start=6,
        tiles="OpenStreetMap",
        width='100%',  # Largura total disponível
        height='100%'  # Altura total disponível
    )
    
def criar_mapa_rotas(rotas_selecionadas, mostrar_riscos, df_datatran):
    """Cria mapa com múltiplas rotas e pontos de risco"""
    
    # Centro do Brasil (aproximadamente)
    mapa = folium.Map(
        location=[-23.5505, -46.6333],
        zoom_start=6,
        tiles="OpenStreetMap",
        width='100%',  # Largura total disponível
        height='100%'  # Altura total disponível
    )
    
    # Cores para diferentes rotas
    cores_rotas = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#FF9FF3']
    
    for i, rota in enumerate(rotas_selecionadas):
        cor_rota = cores_rotas[i % len(cores_rotas)]
        
        # Verificar se é rota personalizada
        if rota == 'PERSONALIZADA' and 'rota_personalizada' in st.session_state:
            rota_pers = st.session_state['rota_personalizada']
            
            # Usar coordenadas da rota real se disponível
            if 'coordenadas_rota' in rota_pers and len(rota_pers['coordenadas_rota']) > 2:
                # Rota real seguindo estradas
                coordenadas_rota = rota_pers['coordenadas_rota']
                popup_texto = f"<b>ROTA PERSONALIZADA</b><br>" \
                             f"{rota_pers['origem_nome']} → {rota_pers['destino_nome']}<br>" \
                             f"📏 {rota_pers['distancia']} km<br>" \
                             f"⏱️ {rota_pers['tempo_estimado']}<br>" \
                             f"🛣️ {rota_pers.get('fonte_roteamento', 'Rota real')}<br>" \
                             f"🚗 Seguindo estradas"
            else:
                # Fallback: linha reta
                coordenadas_rota = [rota_pers['origem_coords'], rota_pers['destino_coords']]
                popup_texto = f"<b>ROTA PERSONALIZADA</b><br>" \
                             f"{rota_pers['origem_nome']} → {rota_pers['destino_nome']}<br>" \
                             f"📏 {rota_pers['distancia']} km<br>" \
                             f"⏱️ {rota_pers['tempo_estimado']}<br>" \
                             f"📐 Linha reta (estimativa)"
            
            # Adicionar linha da rota personalizada
            folium.PolyLine(
                locations=coordenadas_rota,
                color=cor_rota,
                weight=4,
                opacity=0.8,
                popup=popup_texto
            ).add_to(mapa)
            
            # Marcadores para rota personalizada
            folium.Marker(
                location=rota_pers['origem_coords'],
                popup=f"<b>🏁 ORIGEM</b><br>{rota_pers['origem_nome']}",
                icon=folium.Icon(color='blue', icon='play')
            ).add_to(mapa)
            
            folium.Marker(
                location=rota_pers['destino_coords'],
                popup=f"<b>🎯 DESTINO</b><br>{rota_pers['destino_nome']}",
                icon=folium.Icon(color='green', icon='stop')
            ).add_to(mapa)
            
        else:
            # Rota pré-definida
            origem, destino = rota
            rota_info = ROTAS_POSSIVEIS.get((origem, destino))
            if not rota_info:
                continue
                
            # Adicionar linha da rota
            folium.PolyLine(
                locations=[CIDADES_BASE[origem]["coords"], CIDADES_BASE[destino]["coords"]],
                color=cor_rota,
                weight=6,
                opacity=0.8,
                popup=f"<b>{origem} → {destino}</b><br>"
                      f"📏 {rota_info['distancia']} km<br>"
                      f"⏱️ {rota_info['tempo_medio']}<br>"
                      f"🛣️ BR-{rota_info['principais_brs']}<br>"
                      f"💰 {rota_info['pedagios']} pedágios"
            ).add_to(mapa)
            
            # Marcadores das cidades
            for cidade in [origem, destino]:
                cidade_info = CIDADES_BASE[cidade]
                icon_color = 'green' if cidade == destino else 'blue'
                
                folium.Marker(
                    location=cidade_info["coords"],
                    popup=f"<b>{cidade}</b><br>"
                          f"👥 {cidade_info['pop']:,} hab<br>"
                          f"⚠️ Risco base: {cidade_info['risco_base']:.1f}",
                    icon=folium.Icon(color=icon_color, icon='info-sign')
                ).add_to(mapa)
            
            # Adicionar pontos de risco se ativado
            if mostrar_riscos:
                pontos_risco = calcular_pontos_risco_reais(df_datatran, rota_info)
                
                for ponto in pontos_risco:
                    # Tamanho da bolha baseado no nível de risco
                    raio = 5 + (ponto["risco"] * 15)  # 5-20px
                    
                    # Cor da bolha baseada no risco
                    if ponto["risco"] >= 0.7:
                        cor_bolha = '#FF0000'  # Vermelho forte
                    elif ponto["risco"] >= 0.5:
                        cor_bolha = '#FF6600'  # Laranja
                    else:
                        cor_bolha = '#FFD700'  # Amarelo
                    
                    # Criar popup com detalhes
                    popup_content = f"<b>⚠️ {ponto['nome']}</b><br>"
                    popup_content += f"🔥 Nível de Risco: {ponto['risco']:.2f}<br>"
                    
                    if 'detalhes' in ponto:
                        detalhes = ponto['detalhes']
                        popup_content += f"📍 {detalhes.get('municipio', 'N/A')}<br>"
                        popup_content += f"💥 {detalhes.get('tipo_acidente', 'N/A')}<br>"
                        if detalhes.get('mortos', 0) > 0:
                            popup_content += f"💀 Mortos: {detalhes['mortos']}<br>"
                        if detalhes.get('feridos', 0) > 0:
                            popup_content += f"🏥 Feridos: {detalhes['feridos']}<br>"
                    
                    folium.CircleMarker(
                        location=ponto["coords"],
                        radius=raio,
                        popup=popup_content,
                        color='darkred',
                        fillColor=cor_bolha,
                        fillOpacity=0.7,
                        weight=2
                    ).add_to(mapa)
    
    return mapa

# 🌤️ Configuração da API climática
# Busca a chave nos secrets do Streamlit Cloud
try:
    WEATHER_API_KEY = st.secrets["WEATHER_API_KEY"]
except KeyError:
    WEATHER_API_KEY = None
    st.error("⚠️ WEATHER_API_KEY não encontrada nos secrets do Streamlit Cloud")

@st.cache_data(ttl=1800)  # Cache por 30 minutos
def obter_clima_atual(cidade):
    """Obtém condições climáticas atuais usando WeatherAPI"""
    
    if not WEATHER_API_KEY:
        # Se não tem API key configurada, usar dados simulados
        condicoes = ['Ensolarado', 'Parcialmente nublado', 'Nublado', 'Chuva leve', 'Chuva forte']
        temperatura = random.randint(18, 32)
        condicao = random.choice(condicoes)
        
        return {
            "temperatura": temperatura,
            "condicao": condicao,
            "umidade": random.randint(40, 80),
            "vento_kph": random.randint(5, 25),
            "risco_climatico": 0.7 if 'forte' in condicao else 0.3 if 'Chuva' in condicao else 0.1,
            "api_status": "⚠️ API key não configurada - dados simulados"
        }
    
    try:
        # URL da WeatherAPI (weatherapi.com)
        url = f"http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHER_API_KEY,
            'q': f"{cidade}, Brasil",
            'lang': 'pt',
            'aqi': 'no'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extrair dados relevantes
            current = data['current']
            condicao = current['condition']['text']
            temperatura = current['temp_c']
            umidade = current['humidity']
            vento_kph = current['wind_kph']
            
            # Calcular risco climático baseado nas condições
            risco_climatico = 0.1  # Base
            
            # Aumentar risco por condições adversas
            condicao_lower = condicao.lower()
            if any(palavra in condicao_lower for palavra in ['chuva forte', 'tempestade', 'temporal']):
                risco_climatico += 0.7
            elif any(palavra in condicao_lower for palavra in ['chuva', 'chuvisco', 'garoa']):
                risco_climatico += 0.4
            elif any(palavra in condicao_lower for palavra in ['nevoeiro', 'neblina', 'cerração']):
                risco_climatico += 0.5
            elif 'nublado' in condicao_lower:
                risco_climatico += 0.1
                
            # Ajustar por vento forte
            if vento_kph > 50:
                risco_climatico += 0.3
            elif vento_kph > 30:
                risco_climatico += 0.1
                
            # Ajustar por umidade muito alta
            if umidade > 85:
                risco_climatico += 0.1
            
            return {
                "temperatura": temperatura,
                "condicao": condicao,
                "umidade": umidade,
                "vento_kph": vento_kph,
                "risco_climatico": min(risco_climatico, 1.0),
                "api_status": "✅ Dados reais da WeatherAPI"
            }
        
        elif response.status_code == 401:
            st.error("🔑 API key inválida ou expirada")
        elif response.status_code == 403:
            st.error("🚫 Cota da API esgotada")
        else:
            st.warning(f"⚠️ API retornou erro {response.status_code}")
            
    except requests.exceptions.Timeout:
        st.warning("⏱️ Timeout na API climática - usando dados simulados")
    except requests.exceptions.RequestException as e:
        st.warning(f"🌐 Erro na conexão com API: {str(e)[:50]}...")
    except Exception as e:
        st.warning(f"❌ Erro inesperado: {str(e)[:50]}...")
    
    # Fallback: dados simulados se API falhar
    condicoes = ['Ensolarado', 'Parcialmente nublado', 'Nublado', 'Chuva leve', 'Chuva forte']
    temperatura = random.randint(18, 32)
    condicao = random.choice(condicoes)
    
    return {
        "temperatura": temperatura,
        "condicao": condicao,
        "umidade": random.randint(40, 80),
        "vento_kph": random.randint(5, 25),
        "risco_climatico": 0.7 if 'forte' in condicao else 0.3 if 'Chuva' in condicao else 0.1,
        "api_status": "⚠️ Dados simulados (API indisponível)"
    }

# 🎛️ Interface Principal
st.markdown('<div class="main-header"><h1>🛣️ Sistema Inteligente de Rotas</h1><p>Análise avançada de riscos com dados reais do DataTran</p></div>', unsafe_allow_html=True)

# Sidebar para controles
with st.sidebar:
    # Upload opcional (só se não encontrar arquivo local)
    if not os.path.exists('datatran2025.zip'):
        st.markdown("### 📁 Upload de Dados (Opcional)")
        
        uploaded_file = st.file_uploader(
            "Faça upload do datatran2025.zip (opcional)",
            type=['zip'],
            help="Se não carregar, o sistema tentará usar o arquivo local do projeto"
        )
        
        if uploaded_file:
            st.session_state['datatran2025.zip'] = uploaded_file
            st.success("✅ Arquivo carregado com sucesso!")
        
        st.markdown("---")
    
    st.markdown("### 🎯 Rota Personalizada")
    
    # Inicializar lista de rotas selecionadas
    rotas_selecionadas = []
    
    st.markdown("**Digite os endereços de origem e destino:**")
    
    endereco_origem = st.text_input(
        "🏁 Endereço de Origem",
        placeholder="Ex: Rua das Flores, 123, São Paulo, SP",
        help="Digite o endereço completo (rua, número, cidade, estado)"
    )
    
    endereco_destino = st.text_input(
        "🎯 Endereço de Destino", 
        placeholder="Ex: Avenida Copacabana, 456, Rio de Janeiro, RJ",
        help="Digite o endereço completo (rua, número, cidade, estado)"
    )
    
    if endereco_origem and endereco_destino:
        if st.button("🔍 Buscar Rota Personalizada", type="primary"):
            with st.spinner("Geocodificando endereços..."):
                # Geocodificar origem
                result_origem = geocodificar_endereco(endereco_origem)
                result_destino = geocodificar_endereco(endereco_destino)
                
                if result_origem['status'] == 'sucesso' and result_destino['status'] == 'sucesso':
                    # Criar rota personalizada
                    rota_personalizada = criar_rota_personalizada(
                        (result_origem['lat'], result_origem['lon']),
                        (result_destino['lat'], result_destino['lon']),
                        result_origem['cidade'],
                        result_destino['cidade']
                    )
                    
                    # Salvar na sessão
                    st.session_state['rota_personalizada'] = rota_personalizada
                    st.session_state['enderecos_geocodificados'] = {
                        'origem': result_origem,
                        'destino': result_destino
                    }
                    
                    st.success(f"✅ Rota encontrada: {rota_personalizada['distancia']} km, {rota_personalizada['tempo_estimado']}")
                    
                else:
                    if result_origem['status'] == 'erro':
                        st.error(f"❌ Origem: {result_origem['message']}")
                    if result_destino['status'] == 'erro':
                        st.error(f"❌ Destino: {result_destino['message']}")
    
    # Checkbox para incluir rota personalizada se existir
    if 'rota_personalizada' in st.session_state:
        rota_pers = st.session_state['rota_personalizada']
        incluir_personalizada = st.checkbox(
            f"✅ Incluir rota: {rota_pers['origem_nome']} → {rota_pers['destino_nome']} ({rota_pers['distancia']} km)",
            value=True
        )
        
        if incluir_personalizada:
            rotas_selecionadas.append('PERSONALIZADA')
    
    st.markdown("---")
    
    st.markdown("### 🗺️ Configurações do Mapa")
    
    # Toggle para mostrar riscos
    mostrar_riscos = st.toggle(
        "🔥 Exibir Pontos de Risco",
        value=True,  # Ativado por padrão
        help="Ativa/desativa as bolhas de risco baseadas nos dados do DataTran"
    )
    
    if mostrar_riscos:
        st.markdown("🔴 **Modo Risco Ativado**")
        st.markdown("**📊 Interpretação das Bolhas:**")
        st.markdown("• **Tamanho**: Proporcional ao índice de acidentes")
        st.markdown("• **🔴 Vermelho**: Crítico (>0.7) - Local com muitos acidentes/mortes")
        st.markdown("• **🟠 Laranja**: Alto (0.5-0.7) - Acidentes frequentes") 
        st.markdown("• **🟡 Amarelo**: Moderado (<0.5) - Ocorrências ocasionais")
        st.markdown("**💡 Passe o mouse para ver resumo rápido**")
        st.markdown("**🖱️ Clique nas bolhas para análise detalhada**")
        st.markdown("**ℹ️ Base: Acidentes de trânsito reais (DataTran/PRF)**")

# Conteúdo principal
if not rotas_selecionadas:
    st.warning("⚠️ Selecione pelo menos uma rota na barra lateral para visualizar o mapa.")
    
    # Mostrar exemplo de como usar
    with st.expander("💡 Como usar este sistema"):
        st.markdown("""
        ### 🎯 **Opções de Rota:**
        
        **1. 🏢 Cidades Pré-definidas:**
        - Selecione uma ou mais rotas entre cidades principais
        - Dados otimizados com informações de BRs, pedágios e tempos
        
        **2. 📍 Endereços Personalizados:**
        - Digite qualquer endereço do Brasil
        - Sistema faz geocodificação automática
        - Calcula distância e tempo estimado
        
        ### 🔥 **Visualização de Riscos:**
        - Ative o toggle "Exibir Pontos de Risco"
        - Bolhas vermelhas mostram locais perigosos
        - Baseado em dados reais de acidentes
        - Clique nas bolhas para ver detalhes
        
        ### 📊 **Dados:**
        - Upload do datatran2025.zip para dados reais
        - Integração com WeatherAPI para clima
        - Análise inteligente de múltiplos fatores
        """)
    
    st.stop()

# Carregar dados do DataTran
df_datatran = carregar_datatran()

if df_datatran is not None:
    st.info(f"📊 Dados carregados: {len(df_datatran):,} registros de acidentes")
else:
    st.warning("⚠️ Usando dados simulados. Faça upload do datatran2025.zip para análise real.")

# Métricas das rotas selecionadas
if rotas_selecionadas:
    st.markdown("### 📊 Resumo das Rotas Selecionadas")

    # Preparar dados para métricas
    metricas_rotas = []
    
    for rota in rotas_selecionadas:
        if rota == 'PERSONALIZADA' and 'rota_personalizada' in st.session_state:
            rota_pers = st.session_state['rota_personalizada']
            metricas_rotas.append({
                'nome': f"{rota_pers['origem_nome']} → {rota_pers['destino_nome']}",
                'distancia': rota_pers['distancia'],
                'tempo': rota_pers['tempo_estimado'],
                'tipo': 'personalizada'
            })
        else:
            # Rota pré-definida (tupla)
            origem, destino = rota
            rota_info = ROTAS_POSSIVEIS[(origem, destino)]
            metricas_rotas.append({
                'nome': f"{origem} → {destino}",
                'distancia': rota_info['distancia'],
                'tempo': rota_info['tempo_medio'],
                'tipo': 'predefinida'
            })
    
    # Exibir métricas
    cols = st.columns(min(len(metricas_rotas), 4))
    for i, metrica in enumerate(metricas_rotas):
        with cols[i % 4]:
            emoji = "🎯" if metrica['tipo'] == 'personalizada' else "🏢"
            st.metric(
                label=f"{emoji} {metrica['nome']}",
                value=f"{metrica['distancia']} km",
                delta=f"{metrica['tempo']}"
            )

# Mapa principal
st.markdown("### 🗺️ Mapa Interativo de Rotas")

mapa = criar_mapa_rotas(rotas_selecionadas, mostrar_riscos, df_datatran)
mapa_data = st_folium(mapa, width=1400, height=700, returned_objects=["last_object_clicked"])

# Análise detalhada das rotas
if rotas_selecionadas:
    st.markdown("### 📈 Análise Detalhada")
    
    # Preparar tabs só para rotas personalizadas
    tab_names = []
    tab_data = []
    
    for rota in rotas_selecionadas:
        if rota == 'PERSONALIZADA' and 'rota_personalizada' in st.session_state:
            rota_pers = st.session_state['rota_personalizada']
            tab_names.append(f"{rota_pers['origem_nome']} → {rota_pers['destino_nome']}")
            tab_data.append({
                'tipo': 'personalizada',
                'dados': rota_pers
            })
    
    if tab_names:  # Só criar tabs se houver rotas personalizadas
        tabs = st.tabs(tab_names)
        
        for i, tab_info in enumerate(tab_data):
            with tabs[i]:
                # Rota personalizada
                rota_dados = tab_info['dados']
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**📍 Informações da Rota Personalizada**")
                    st.write(f"🏁 **Origem:** {rota_dados['origem_nome']}")
                    st.write(f"🎯 **Destino:** {rota_dados['destino_nome']}")
                    st.write(f"📏 **Distância:** {rota_dados['distancia']} km")
                    st.write(f"⏱️ **Tempo Estimado:** {rota_dados['tempo_estimado']}")
                    st.write(f"🛣️ **Roteamento:** {rota_dados.get('fonte_roteamento', 'Geocodificação')}")
                    
                    # Indicar se é rota real ou estimada
                    if 'coordenadas_rota' in rota_dados and len(rota_dados['coordenadas_rota']) > 2:
                        st.success("✅ Rota real seguindo estradas")
                        st.write(f"📍 **Pontos da rota:** {len(rota_dados['coordenadas_rota'])} coordenadas")
                    else:
                        st.info("📐 Estimativa em linha reta")
                
                with col2:
                    st.markdown("**🌤️ Condições Climáticas Reais**")
                    clima_origem = obter_clima_atual(rota_dados['origem_nome'])
                    clima_destino = obter_clima_atual(rota_dados['destino_nome'])
                    
                    # Mostrar informações detalhadas
                    st.write(f"🌡️ **{rota_dados['origem_nome']}:**")
                    st.write(f"   • {clima_origem['temperatura']}°C, {clima_origem['condicao']}")
                    st.write(f"   • 💧 Umidade: {clima_origem['umidade']}%")
                    st.write(f"   • 💨 Vento: {clima_origem['vento_kph']} km/h")
                    st.write(f"   • {clima_origem['api_status']}")
                    
                    st.write(f"🌡️ **{rota_dados['destino_nome']}:**")
                    st.write(f"   • {clima_destino['temperatura']}°C, {clima_destino['condicao']}")
                    st.write(f"   • 💧 Umidade: {clima_destino['umidade']}%")
                    st.write(f"   • 💨 Vento: {clima_destino['vento_kph']} km/h")
                    st.write(f"   • {clima_destino['api_status']}")
                    
                    # Análise de risco climático combinado
                    risco_climatico = (clima_origem['risco_climatico'] + clima_destino['risco_climatico']) / 2
                    
                    if risco_climatico > 0.6:
                        st.error(f"🔴 **Alto risco climático:** {risco_climatico:.2f}")
                        st.write("⚠️ Considere adiar a viagem ou usar rota alternativa")
                    elif risco_climatico > 0.3:
                        st.warning(f"🟡 **Risco climático moderado:** {risco_climatico:.2f}")
                        st.write("⚠️ Atenção redobrada e redução de velocidade")
                    else:
                        st.success(f"🟢 **Condições favoráveis:** {risco_climatico:.2f}")
                        st.write("✅ Condições ideais para viagem")
                
                with col3:
                    st.markdown("**⚠️ Análise de Riscos da Rota**")
                    
                    # Calcular pontos de risco para a rota personalizada
                    if 'coordenadas_rota' in rota_dados and df_datatran is not None:
                        pontos_risco = calcular_pontos_risco_rota_personalizada(
                            df_datatran, 
                            rota_dados.get('coordenadas_rota', [rota_dados['origem_coords'], rota_dados['destino_coords']]),
                            rota_dados['origem_nome'],
                            rota_dados['destino_nome']
                        )
                        
                        if pontos_risco:
                            risco_medio = np.mean([p["risco"] for p in pontos_risco])
                            pontos_criticos = len([p for p in pontos_risco if p["risco"] >= 0.7])
                            
                            st.metric("Risco Médio da Rota", f"{risco_medio:.2f}", f"{len(pontos_risco)} pontos identificados")
                            st.metric("Pontos Críticos", pontos_criticos)
                            
                            if risco_medio >= 0.7:
                                st.error("🔴 **Rota de Alto Risco**")
                                st.write("• Múltiplos acidentes registrados")
                                st.write("• Extrema cautela recomendada")
                            elif risco_medio >= 0.4:
                                st.warning("🟡 **Rota de Risco Moderado**")
                                st.write("• Alguns pontos de atenção")
                                st.write("• Precauções básicas necessárias")
                            else:
                                st.success("🟢 **Rota Relativamente Segura**")
                                st.write("• Poucos registros de acidentes")
                                st.write("• Direção defensiva recomendada")
                            
                            # Mostrar principais tipos de problemas encontrados
                            if pontos_risco:
                                tipos_acidentes = []
                                for ponto in pontos_risco:
                                    tipo = ponto.get('detalhes', {}).get('tipo_acidente', '')
                                    if tipo and tipo != 'N/A':
                                        tipos_acidentes.append(tipo)
                                
                                if tipos_acidentes:
                                    st.write("**⚠️ Principais riscos identificados:**")
                                    tipos_unicos = list(set(tipos_acidentes))[:3]  # Top 3
                                    for tipo in tipos_unicos:
                                        st.write(f"• {tipo}")
                        else:
                            st.info("📊 Nenhum ponto de risco específico identificado")
                            st.write("• Rota com baixo histórico de acidentes")
                            st.write("• Mantenha precauções normais de trânsito")
                    else:
                        st.info("📊 Análise baseada em estimativas")
                        # Risco estimado baseado na distância
                        risco_estimado = min(rota_dados['distancia'] / 1000, 0.8)
                        st.metric("Risco Estimado", f"{risco_estimado:.2f}", "baseado na distância")
                        
                        if risco_estimado >= 0.6:
                            st.warning("🟡 **Rota Longa** - Mais paradas recomendadas")
                        else:
                            st.success("🟢 **Rota Adequada**")

# Footer com informações
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    💡 <b>Sistema Inteligente de Rotas</b><br>
    Dados em tempo real • Análise preditiva • Rotas otimizadas<br>
    <small>Baseado em dados oficiais do DataTran e APIs climáticas</small>
</div>
""", unsafe_allow_html=True)
