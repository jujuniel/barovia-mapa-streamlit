import streamlit as st
import datetime
import random
import heapq
import os
import glob
from PIL import Image

# Set page configuration
st.set_page_config(
    page_title="Barovia Travel Calculator & Interactive Map",
    page_icon="🦇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Barovia / Curse of Strahd theme
st.markdown("""
<style>
    .main {
        background-color: #121212;
        color: #e0e0e0;
    }
    .stApp {
        background-color: #0e0e10;
    }
    h1, h2, h3 {
        color: #b91c1c !important;
        font-family: 'Cinzel', 'Georgia', serif;
    }
    .metric-card {
        background-color: #1f1f23;
        border-left: 4px solid #b91c1c;
        padding: 15px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .stButton>button {
        background-color: #7f1d1d;
        color: white;
        border-radius: 4px;
        border: 1px solid #b91c1c;
    }
    .stButton>button:hover {
        background-color: #991b1b;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Locations Dataset (Markers A to Z)
LOCATIONS = {
    "A": {"name": "A - Portão Leste de Baróvia (Gates of Barovia)", "region": "Svalich Woods", "desc": "Os portões de ferro forjado ladeados por estátuas sem cabeça que marcam a entrada do domínio de Strahd."},
    "B": {"name": "B - Estrada Velha Svalich (Old Svalich Road)", "region": "Old Svalich Road", "desc": "A principal via de terra e cascalho que corta o vale de Baróvia de leste a oeste."},
    "C": {"name": "C - Floresta de Svalich Leste (Svalich Woods)", "region": "Svalich Woods", "desc": "Bosques góticos densos com árvores morder-de-lobo e neblina impenetrável."},
    "D": {"name": "D - Rio Ivlis (River Ivlis)", "region": "River Ivlis", "desc": "Rio de águas escuras e geladas que corre da cachoeira até a borda do vale."},
    "E": {"name": "E - Vila de Baróvia (Village of Barovia)", "region": "Village of Barovia", "desc": "O assentamento oprimido à sombra do Castelo Ravenloft, lar de Ismark e Ireena Kolyana."},
    "F": {"name": "F - Acampamento Tser Pool (Tser Pool Encampment)", "region": "Tser Pool", "desc": "Acampamento dos Vistani às margens do lago, onde reside a Madame Eva."},
    "G": {"name": "G - Cachoeira Tser (Tser Falls)", "region": "Tser Falls", "desc": "Uma queda d'água rugidora de 160 metros com uma ponte de pedra que cruza o abismo."},
    "H": {"name": "H - Encruzilhada do Rio Ivlis (Crossroads)", "region": "Crossroads", "desc": "Entroncamento estratégico ligando a Vila de Baróvia, o Castelo Ravenloft e Vallaki."},
    "I": {"name": "I - Precipício de Ravenloft (Precipice)", "region": "Ravenloft", "desc": "A estrada sinuosa que sobe os penhascos em direção ao castelo do Conde."},
    "J": {"name": "J - Portões de Ravenloft (Gates of Ravenloft)", "region": "Ravenloft", "desc": "Os portões de ferro maciço que se abrem rangerosamente para visitantes do castelo."},
    "K": {"name": "K - Castelo Ravenloft (Castle Ravenloft)", "region": "Ravenloft", "desc": "A fortaleza sombria e imponente do Conde Strahd von Zarovich."},
    "L": {"name": "L - Lago Zarovich (Lake Zarovich)", "region": "Lake Zarovich", "desc": "Grande lago frio ao norte de Vallaki, cercado por névoa e montanhas."},
    "M": {"name": "M - Margem Norte do Lago Zarovich (Mad Mage Lair)", "region": "Lake Zarovich", "desc": "Encostas selvagens do Monte Baratok, abrigo de criaturas e do Mago Louco."},
    "N": {"name": "N - Cidade de Vallaki (Town of Vallaki)", "region": "Vallaki", "desc": "A maior cidade murada de Baróvia, governada pelo Vargas Vallakovich sob slogans de felicidade forçada."},
    "O": {"name": "O - Velho Moedor de Ossos (Old Bonegrinder)", "region": "Old Bonegrinder", "desc": "Moinho de vento decrépito no topo da colina, lar das bruxas do crepúsculo (Night Hags)."},
    "P": {"name": "P - Encruzilhada do Rio Luna (Luna Crossroads)", "region": "Luna River", "desc": "Ponto de bifurcação conectando Vallaki, Krezk, Berez e a Torre de Van Richten."},
    "Q": {"name": "Q - Torre de Van Richten (Van Richten's Tower)", "region": "Lake Baratok", "desc": "Torre mágica de quatro andares no Lago Baratok, protegida por um campo anti-magia."},
    "R": {"name": "R - Encruzilhada de Krezk (Krezk Pass)", "region": "Krezk Pass", "desc": "Entroncamento nas montanhas ocidentais que leva a Krezk, Vinhedo e Colina Yester."},
    "S": {"name": "S - Vila de Krezk (Village of Krezk)", "region": "Krezk", "desc": "Vila fortificada e isolada nas montanhas, famosa pela Abadia de Santa Markovia."},
    "T": {"name": "T - Argynvostholt e Lago Luna (Argynvostholt)", "region": "Argynvostholt", "desc": "A mansão fortificada em ruínas da antiga Ordem do Dragão de Prata."},
    "U": {"name": "U - Ruínas de Berez (Ruins of Berez)", "region": "Berez", "desc": "Povoado pantanoso abandonado e inundado, domínio da bruxa Baba Lysaga."},
    "V": {"name": "V - Lago Baratok (Lake Baratok)", "region": "Lake Baratok", "desc": "Lago isolado nas montanhas do noroeste de Baróvia."},
    "W": {"name": "W - Mago dos Vinhos (Wizard of Wines Winery)", "region": "Wizard of Wines", "desc": "O único vinhedo de Baróvia, fonte do vinho que sustenta o ânimo do povo do vale."},
    "X": {"name": "X - Templo de Âmbar e Monte Ghakis (Amber Temple)", "region": "Mount Ghakis", "desc": "Complexo antigo encravado nas neves do Monte Ghakis, prisão dos Poderes Sombrios."},
    "Y": {"name": "Y - Colina Yester (Yester Hill)", "region": "Yester Hill", "desc": "Muralha de pedra antiga e círculo druídico dedicado ao culto a Strahd."},
    "Z": {"name": "Z - Toca dos Lobisomens (Werewolf Den)", "region": "Svalich Woods West", "desc": "Caverna escondida nas florestas do noroeste, quartel-general da alcateia de Kiril."}
}

# Road Network Graph (distances in miles between connected nodes)
# 1 hex = 0.25 miles
GRAPH = {
    "A": [("B", 3.0, "road")],
    "B": [("A", 3.0, "road"), ("C", 1.5, "road"), ("D", 2.0, "road")],
    "C": [("B", 1.5, "road")],
    "D": [("B", 2.0, "road"), ("E", 2.0, "road")],
    "E": [("D", 2.0, "road"), ("F", 3.5, "road")],
    "F": [("E", 3.5, "road"), ("G", 2.0, "road")],
    "G": [("F", 2.0, "road"), ("H", 1.0, "road")],
    "H": [("G", 1.0, "road"), ("I", 1.5, "road"), ("O", 4.5, "road")],
    "I": [("H", 1.5, "road"), ("J", 1.0, "road")],
    "J": [("I", 1.0, "road"), ("K", 1.0, "road")],
    "K": [("J", 1.0, "road")],
    "O": [("H", 4.5, "road"), ("N", 3.0, "road")],
    "N": [("O", 3.0, "road"), ("L", 1.0, "road"), ("P", 2.5, "road")],
    "L": [("N", 1.0, "road"), ("M", 3.0, "difficult")],
    "M": [("L", 3.0, "difficult")],
    "P": [("N", 2.5, "road"), ("Q", 2.0, "road"), ("R", 4.0, "road"), ("U", 6.0, "difficult")],
    "Q": [("P", 2.0, "road"), ("V", 1.5, "road")],
    "R": [("P", 4.0, "road"), ("S", 1.5, "road"), ("V", 2.0, "road"), ("W", 3.5, "road"), ("T", 5.0, "road")],
    "S": [("R", 1.5, "road"), ("Z", 3.0, "difficult")],
    "Z": [("S", 3.0, "difficult")],
    "V": [("Q", 1.5, "road"), ("R", 2.0, "road")],
    "W": [("R", 3.5, "road"), ("Y", 4.5, "difficult")],
    "Y": [("W", 4.5, "difficult")],
    "U": [("P", 6.0, "difficult")],
    "T": [("R", 5.0, "road"), ("X", 8.0, "mountain")],
    "X": [("T", 8.0, "mountain")]
}

def dijkstra_path(start, end):
    queue = [(0, start, [])]
    seen = set()
    while queue:
        (cost, node, path) = heapq.heappop(queue)
        if node in seen:
            continue
        seen.add(node)
        path = path + [node]
        if node == end:
            return cost, path
        for neighbor, weight, terrain_type in GRAPH.get(node, []):
            if neighbor not in seen:
                heapq.heappush(queue, (cost + weight, neighbor, path))
    return float("inf"), []

def get_day_night_status(time_obj):
    hour = time_obj.hour
    if 6 <= hour < 8:
        return "🌄 Alvorada Nebulosa", "Luz fraca. A névoa fria se ergue dos solos de Baróvia.", "Baixo"
    elif 8 <= hour < 18:
        return "☁️ Dia Pálido", "Luz pálida constante. O céu permanece cinzento e sem sol visível.", "Médio"
    elif 18 <= hour < 20:
        return "🌆 Crepúsculo de Sangue", "Luz fraca. Sombras se alongam e a temperatura cai rapidamente.", "Alto"
    else:
        return "🌙 Noite Profunda", "Escuridão Total. As forças de Strahd e monstros vagam livremente.", "Muito Alto"

def get_weather(region, hour):
    if "Mountain" in region or region in ["Mount Ghakis", "Krezk Pass"]:
        return "❄️ Vento uivante e chuva congelante/neve. Visibilidade reduzida."
    elif "Svalich" in region or region in ["Svalich Woods", "Svalich Woods West"]:
        return "🌫️ Névoa espessa e garoa constante. Cheiro de agulhas de pinheiro e terra molhada."
    elif "Lake" in region or region in ["Lake Zarovich", "Lake Baratok"]:
        return "🌁 Brisa fria vinda da água e nevoeiro denso sobre as margens."
    elif region == "Berez":
        return "🌧️ Chuva torrencial sobre o pântano e lamaçal pesado."
    else:
        return "☁️ Tempo nublado, frio úmido e vento fraco intermitente."

# App UI
st.title("🏰 Mapa Interativo e Calculadora de Viagem — Baróvia")
st.caption("Ferramenta de navegação e simulação de deslocamento para A Maldição de Strahd (D&D 5e)")

# Sidebar Controls
st.sidebar.header("⚙️ Parâmetros de Viagem")

origin_key = st.sidebar.selectbox("Ponto de Origem:", list(LOCATIONS.keys()), format_func=lambda x: LOCATIONS[x]["name"], index=0)
dest_key = st.sidebar.selectbox("Ponto de Destino:", list(LOCATIONS.keys()), format_func=lambda x: LOCATIONS[x]["name"], index=4)

pace = st.sidebar.radio("Ritmo de Viagem:", ["Normal (3 milhas/h)", "Rápido (4 milhas/h)", "Lento (2 milhas/h)"])
if "Normal" in pace:
    speed_mph = 3.0
    pace_note = "Sem modificadores de percepção."
elif "Rápido" in pace:
    speed_mph = 4.0
    pace_note = "Penalidade de -5 na Percepção Passiva do grupo."
else:
    speed_mph = 2.0
    pace_note = "Permite mover-se em Furtividade."

terrain = st.sidebar.selectbox("Modificador de Terreno:", ["Estrada Principal (1x)", "Terreno Difícil / Pântano (2x)", "Montanha / Neve (2.5x)"])
if "1x" in terrain:
    terrain_mult = 1.0
elif "2x" in terrain:
    terrain_mult = 2.0
else:
    terrain_mult = 2.5

start_time = st.sidebar.time_input("Horário de Partida:", datetime.time(8, 0))

# Tabs Layout
tab1, tab2, tab3 = st.tabs(["🧭 Calculadora de Rota", "📍 Marcadores (A a Z)", "🗺️ Visualizador do Mapa"])

with tab1:
    if origin_key == dest_key:
        st.warning("⚠️ Selecione um destino diferente da origem para calcular a rota.")
    else:
        distance, path = dijkstra_path(origin_key, dest_key)
        
        if distance == float("inf"):
            st.error("Não foi encontrada uma rota conectada entre estes pontos.")
        else:
            total_hexes = int(distance / 0.25)
            effective_speed = speed_mph / terrain_mult
            travel_hours = distance / effective_speed
            
            hours_int = int(travel_hours)
            minutes_int = int((travel_hours - hours_int) * 60)
            
            start_datetime = datetime.datetime.combine(datetime.date.today(), start_time)
            arrival_datetime = start_datetime + datetime.timedelta(hours=hours_int, minutes=minutes_int)
            
            phase, phase_desc, hazard_level = get_day_night_status(arrival_datetime.time())
            destination_region = LOCATIONS[dest_key]["region"]
            weather = get_weather(destination_region, arrival_datetime.hour)
            
            # Metrics Overview
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Distância Total", f"{distance:.1f} milhas", f"{total_hexes} hexágonos")
            with col2:
                st.metric("Tempo de Viagem", f"{hours_int}h {minutes_int}min")
            with col3:
                st.metric("Horário de Chegada", arrival_datetime.strftime("%H:%M"))
            with col4:
                st.metric("Perigo na Chegada", hazard_level)
            
            st.markdown("---")
            
            # Journey Details
            st.subheader("📋 Resumo do Trajeto")
            c_a, c_b = st.columns(2)
            with c_a:
                st.markdown(f"**Origem:** {LOCATIONS[origin_key]['name']}")
                st.markdown(f"**Destino:** {LOCATIONS[dest_key]['name']}")
                st.markdown(f"**Ritmo & Terreno:** {pace} | {terrain}")
                st.caption(f"ℹ️ {pace_note}")
            with c_b:
                st.markdown(f"**Iluminação na Chegada:** {phase}")
                st.caption(phase_desc)
                st.markdown(f"**Clima Predominante:** {weather}")
            
            # Route Steps
            st.subheader("🛣️ Rota Recomendada")
            path_names = " ➔ ".join([f"**[{node}]** {LOCATIONS[node]['name'].split(' - ')[1]}" for node in path])
            st.info(f"Caminho: {path_names}")
            
            # Random Encounter Check
            st.subheader("🎲 Teste de Encontro Aleatório")
            if st.button("Rolar Encontro na Estrada (d20)"):
                roll = random.randint(1, 20)
                target = 18 if "Noite" in phase else 15
                if roll >= target:
                    st.error(f"🚨 **ENCONTRO ALEATÓRIO!** (Rolagem: {roll} >= {target}). Prepare o combate ou evento especial!")
                else:
                    st.success(f"✅ **Caminho Tranquilo.** (Rolagem: {roll} < {target}). Nenhum encontro hostil imediato.")

with tab2:
    st.subheader("📍 Catálogo de Locais de Baróvia (Marcadores A a Z)")
    selected_loc = st.selectbox("Selecione um local para detalhes:", list(LOCATIONS.keys()), format_func=lambda x: LOCATIONS[x]["name"])
    loc_data = LOCATIONS[selected_loc]
    st.markdown(f"### {loc_data['name']}")
    st.markdown(f"**Região:** `{loc_data['region']}`")
    st.markdown(f"**Descrição:** {loc_data['desc']}")
    
    st.markdown("---")
    st.dataframe(
        [{"Marcador": k, "Nome": v["name"], "Região": v["region"], "Descrição": v["desc"]} for k, v in LOCATIONS.items()],
        use_container_width=True
    )

with tab3:
    st.subheader("🖼️ Visualização do Mapa de Baróvia")
    
    # Candidate filenames to search for automatically
    candidate_files = [
        "mapa_de_barovia.png",
        "mapa_de_barovia.PNG",
        "mapa de barovia.PNG",
        "mapa de barovia.png",
        "1.PNG",
        "1.png",
        "mapa.png",
        "mapa.PNG",
        "mapa.jpg",
        "mapa_de_barovia.jpg"
    ]
    
    # Find any image files in the directory
    found_images = []
    for ext in ["*.png", "*.PNG", "*.jpg", "*.jpeg", "*.webp", "*.JPG"]:
        found_images.extend(glob.glob(ext))
        found_images.extend(glob.glob(f"**/{ext}", recursive=True))
    
    # Preserve order and deduplicate
    seen_imgs = set()
    unique_images = []
    for img_path in found_images:
        if img_path not in seen_imgs:
            seen_imgs.add(img_path)
            unique_images.append(img_path)
            
    selected_image_path = None
    
    # Check exact candidates first
    for cand in candidate_files:
        if os.path.exists(cand):
            selected_image_path = cand
            break
            
    # If no exact candidate matched, pick the first image found in directory
    if not selected_image_path and unique_images:
        selected_image_path = unique_images[0]
        
    if selected_image_path:
        try:
            image = Image.open(selected_image_path)
            st.success(f"📷 Imagem detectada e carregada: `{selected_image_path}`")
            st.image(image, caption=f"Mapa de Baróvia ({selected_image_path}) — Escala: 1 Hexágono = 0.25 milhas", use_column_width=True)
        except Exception as e:
            st.error(f"Erro ao abrir a imagem `{selected_image_path}`: {e}")
    else:
        st.warning("⚠️ Nenhuma imagem de mapa foi localizada automaticamente na pasta raiz do projeto.")
        
        st.markdown("""
        ### 🔍 Principais Motivos e Como Resolver:
        
        1. **Nome ou Extensão Diferente (Diferença de Maiúsculas/Minúsculas)**:
           - No Linux (usado pelo Streamlit Cloud), o nome é **estritamente sensível a maiúsculas/minúsculas**.
           - Se seu arquivo no computador se chama `mapa de barovia.PNG`, `mapa_de_barovia.PNG` ou `1.PNG`, altere o nome no GitHub para `mapa_de_barovia.png`.
        
        2. **Arquivo enviado dentro de uma subpasta**:
           - Certifique-se de que enviou a imagem diretamente na **raiz** do seu repositório (no mesmo nível onde está o arquivo `app.py`), e não dentro de pastas como `images/` ou `assets/`.
        
        3. **Extensão Oculta no Windows**:
           - No Windows, a extensão `.png` pode estar oculta, e ao salvar como `mapa_de_barovia.png`, o nome real fica `mapa_de_barovia.png.png`.
        """)
        
        st.markdown("---")
        st.markdown("**📁 Arquivos atualmente detectados na pasta do seu projeto:**")
        try:
            curr_files = os.listdir(".")
            st.code("\n".join(curr_files) if curr_files else "Nenhum arquivo encontrado")
        except Exception as ex:
            st.write(f"Não foi possível listar arquivos: {ex}")
