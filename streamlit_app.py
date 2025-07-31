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
    """Carrega dados do arquivo datatran2025.zip com múltiplas tentativas de encoding"""
    try:
        # Tentar carregar o arquivo ZIP
        if 'datatran2025.zip' in st.session_state:
            with zipfile.ZipFile(st.session_state['datatran2025.zip']) as zip_file:
                # Procurar arquivo CSV ou Excel dentro do ZIP
                for filename in zip_file.namelist():
                    if filename.endswith(('.csv', '.xlsx')):
                        with zip_file.open(filename) as file:
                            if filename.endswith('.csv'):
                                # Tentar diferentes encodings para CSV
                                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'utf-8-sig']
                                
                                for encoding in encodings:
                                    try:
                                        # Reset file pointer
                                        file.seek(0)
                                        df = pd.read_csv(file, encoding=encoding, sep=';')
                                        st.success(f"✅ DataTran carregado com encoding: {encoding}")
                                        return df
                                    except UnicodeDecodeError:
                                        continue
                                    except Exception as e:
                                        # Tentar com separador diferente
                                        try:
                                            file.seek(0)
                                            df = pd.read_csv(file, encoding=encoding, sep=',')
                                            st.success(f"✅ DataTran carregado com encoding: {encoding}")
                                            return df
                                        except:
                                            continue
                                
                                # Se todos os encodings falharem
                                st.error("❌ Não foi possível decodificar o arquivo CSV. Verifique o formato.")
                                return None
                            else:
                                # Para arquivos Excel
                                df = pd.read_excel(file)
                                st.success("✅ DataTran carregado (Excel)")
                                return df
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

# 🗺️ Função para criar rota personalizada entre dois endereços
def criar_rota_personalizada(origem_coords, destino_coords, origem_nome, destino_nome):
    """Calcula distância e cria informações de rota entre coordenadas personalizadas"""
    from math import radians, cos, sin, asin, sqrt
    
    # Fórmula de Haversine para calcular distância
    def haversine(lon1, lat1, lon2, lat2):
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Raio da Terra em km
        return c * r
    
    distancia = haversine(origem_coords[1], origem_coords[0], destino_coords[1], destino_coords[0])
    tempo_estimado = distancia / 80  # Velocidade média 80 km/h
    
    return {
        'distancia': round(distancia, 1),
        'tempo_estimado': f"{int(tempo_estimado)}h{int((tempo_estimado % 1) * 60)}min",
        'origem_nome': origem_nome,
        'destino_nome': destino_nome,
        'origem_coords': origem_coords,
        'destino_coords': destino_coords,
        'personalizada': True
    }
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
                    if pd.notna(acidente.get('latitude')) and pd.notna(acidente.get('longitude')):
                        # Calcular nível de risco baseado na gravidade
                        risco = 0.3  # Base
                        if 'mortos' in acidente and acidente['mortos'] > 0:
                            risco += 0.4
                        if 'feridos_graves' in acidente and acidente['feridos_graves'] > 0:
                            risco += 0.2
                        if 'condicao_metereologica' in acidente and 'chuva' in str(acidente['condicao_metereologica']).lower():
                            risco += 0.1
                        
                        pontos_risco.append({
                            "nome": f"BR-{br} KM {acidente.get('km', '?')}",
                            "coords": (acidente['latitude'], acidente['longitude']),
                            "risco": min(risco, 1.0),
                            "detalhes": {
                                "municipio": acidente.get('municipio', 'N/A'),
                                "tipo_acidente": acidente.get('tipo_acidente', 'N/A'),
                                "mortos": acidente.get('mortos', 0),
                                "feridos": acidente.get('feridos', 0)
                            }
                        })
    
    # Se não tem dados reais, usar pontos simulados da rota
    if not pontos_risco:
        pontos_risco = rota_info.get("pontos_risco", [])
    
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
            
            # Adicionar linha da rota personalizada
            folium.PolyLine(
                locations=[rota_pers['origem_coords'], rota_pers['destino_coords']],
                color=cor_rota,
                weight=6,
                opacity=0.8,
                popup=f"<b>ROTA PERSONALIZADA</b><br>"
                      f"{rota_pers['origem_nome']} → {rota_pers['destino_nome']}<br>"
                      f"📏 {rota_pers['distancia']} km<br>"
                      f"⏱️ {rota_pers['tempo_estimado']}<br>"
                      f"🛣️ Rota personalizada"
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
    st.markdown("### 📁 Upload de Dados")
    
    uploaded_file = st.file_uploader(
        "Faça upload do datatran2025.zip",
        type=['zip'],
        help="Arquivo ZIP contendo dados do DataTran 2025"
    )
    
    if uploaded_file:
        st.session_state['datatran2025.zip'] = uploaded_file
        st.success("✅ Arquivo carregado com sucesso!")
    
    st.markdown("---")
    st.markdown("### 🎯 Rota Personalizada")
    
    # Opção entre rotas pré-definidas ou endereços personalizados
    modo_selecao = st.radio(
        "Como deseja definir a rota?",
        ["🏢 Cidades pré-definidas", "📍 Endereços personalizados"],
        horizontal=True
    )
    
    if modo_selecao == "📍 Endereços personalizados":
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
    
    # Seleção de múltiplas rotas
    st.markdown("**Selecione as rotas para análise:**")
    rotas_selecionadas = []
    
    for i, ((origem, destino), info) in enumerate(ROTAS_POSSIVEIS.items()):
        key = f"rota_{i}"
        if st.checkbox(f"{origem} → {destino} ({info['distancia']}km)", key=key):
            rotas_selecionadas.append((origem, destino))
    
    st.markdown("---")
    
    # Toggle para mostrar riscos
    mostrar_riscos = st.toggle(
        "🔥 Exibir Pontos de Risco",
        value=False,
        help="Ativa/desativa as bolhas vermelhas de risco no mapa"
    )
    
    if mostrar_riscos:
        st.markdown("🔴 **Modo Risco Ativado**")
        st.markdown("• Bolhas grandes = Alto risco")
        st.markdown("• Bolhas pequenas = Baixo risco")
        st.markdown("• Vermelho = Crítico (>0.7)")
        st.markdown("• Laranja = Alto (0.5-0.7)")
        st.markdown("• Amarelo = Moderado (<0.5)")

# Conteúdo principal
if not rotas_selecionadas:
    st.warning("⚠️ Selecione pelo menos uma rota na barra lateral para visualizar o mapa.")
    st.stop()

# Carregar dados do DataTran
df_datatran = carregar_datatran()

if df_datatran is not None:
    st.info(f"📊 Dados carregados: {len(df_datatran):,} registros de acidentes")
else:
    st.warning("⚠️ Usando dados simulados. Faça upload do datatran2025.zip para análise real.")

# Métricas das rotas selecionadas
st.markdown("### 📊 Resumo das Rotas Selecionadas")

cols = st.columns(min(len(rotas_selecionadas), 4))
for i, (origem, destino) in enumerate(rotas_selecionadas):
    rota_info = ROTAS_POSSIVEIS[(origem, destino)]
    
    with cols[i % 4]:
        st.metric(
            label=f"{origem} → {destino}",
            value=f"{rota_info['distancia']} km",
            delta=f"{rota_info['tempo_medio']}"
        )

# Mapa principal
st.markdown("### 🗺️ Mapa Interativo de Rotas")

mapa = criar_mapa_rotas(rotas_selecionadas, mostrar_riscos, df_datatran)
mapa_data = st_folium(mapa, width=1400, height=700, returned_objects=["last_object_clicked"])

# Análise detalhada das rotas
if rotas_selecionadas:
    st.markdown("### 📈 Análise Detalhada")
    
    tabs = st.tabs([f"{origem} → {destino}" for origem, destino in rotas_selecionadas])
    
    for i, (origem, destino) in enumerate(rotas_selecionadas):
        with tabs[i]:
            rota_info = ROTAS_POSSIVEIS[(origem, destino)]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**📍 Informações da Rota**")
                st.write(f"🏁 **Origem:** {origem}")
                st.write(f"🎯 **Destino:** {destino}")
                st.write(f"📏 **Distância:** {rota_info['distancia']} km")
                st.write(f"⏱️ **Tempo Médio:** {rota_info['tempo_medio']}")
                st.write(f"🛣️ **BR Principal:** {rota_info['principais_brs'][0]}")
                st.write(f"💰 **Pedágios:** {rota_info['pedagios']}")
            
            with col2:
                st.markdown("**🌤️ Condições Climáticas Reais**")
                clima_origem = obter_clima_atual(origem)
                clima_destino = obter_clima_atual(destino)
                
                # Mostrar informações detalhadas
                st.write(f"🌡️ **{origem}:**")
                st.write(f"   • {clima_origem['temperatura']}°C, {clima_origem['condicao']}")
                st.write(f"   • 💧 Umidade: {clima_origem['umidade']}%")
                st.write(f"   • 💨 Vento: {clima_origem['vento_kph']} km/h")
                st.write(f"   • {clima_origem['api_status']}")
                
                st.write(f"🌡️ **{destino}:**")
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
                st.markdown("**⚠️ Análise de Riscos**")
                pontos_risco = calcular_pontos_risco_reais(df_datatran, rota_info)
                
                if pontos_risco:
                    risco_medio = np.mean([p["risco"] for p in pontos_risco])
                    pontos_criticos = len([p for p in pontos_risco if p["risco"] >= 0.7])
                    
                    st.metric("Risco Médio", f"{risco_medio:.2f}", f"{len(pontos_risco)} pontos")
                    st.metric("Pontos Críticos", pontos_criticos)
                    
                    if risco_medio >= 0.7:
                        st.error("🔴 **Rota de Alto Risco**")
                    elif risco_medio >= 0.4:
                        st.warning("🟡 **Rota de Risco Moderado**")
                    else:
                        st.success("🟢 **Rota Segura**")
                else:
                    st.info("📊 Análise baseada em dados históricos")

# Footer com informações
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    💡 <b>Sistema Inteligente de Rotas</b><br>
    Dados em tempo real • Análise preditiva • Rotas otimizadas<br>
    <small>Baseado em dados oficiais do DataTran e APIs climáticas</small>
</div>
""", unsafe_allow_html=True)
