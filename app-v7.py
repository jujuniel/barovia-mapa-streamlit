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

# ---------------------------------------------------------
# CALENDAR CONSTANTS & SESSION STATE (Barovian Calendar)
# ---------------------------------------------------------
BAROVIAN_MOONS = [
    {"name": "Dekavr", "title": "Winter Moon", "season": "Inverno"},
    {"name": "Yinyavr", "title": "Cold Moon", "season": "Inverno / Primavera"},
    {"name": "Fenravr", "title": "Wolf Moon", "season": "Primavera"},
    {"name": "Martavr", "title": "Raven Moon", "season": "Primavera"},
    {"name": "Prylla", "title": "Rain Moon", "season": "Primavera / Verão"},
    {"name": "Mada", "title": "Maid Moon", "season": "Verão"},
    {"name": "Eyun", "title": "Summer Moon", "season": "Verão"},
    {"name": "Eyul", "title": "War Moon", "season": "Verão / Outono"},
    {"name": "Ugavr", "title": "Wine Moon", "season": "Outono"},
    {"name": "Sintavr", "title": "Harvest Moon", "season": "Outono"},
    {"name": "Ottyavr", "title": "Hunter's Moon", "season": "Outono / Inverno"},
    {"name": "Neyavr", "title": "Rot Moon", "season": "Inverno"}
]

if "cal_year" not in st.session_state:
    st.session_state["cal_year"] = 735
if "cal_moon_idx" not in st.session_state:
    st.session_state["cal_moon_idx"] = 3  # Martavr (Raven Moon) default
if "cal_day" not in st.session_state:
    st.session_state["cal_day"] = 1
if "cal_hour" not in st.session_state:
    st.session_state["cal_hour"] = 8
if "cal_minute" not in st.session_state:
    st.session_state["cal_minute"] = 0

def get_moon_phase(day):
    """Returns the moon phase based on the 28-day Barovian cycle"""
    if day == 1:
        return "⚪ Lua Cheia (Full Moon)", "Os monstros de Baróvia e lobisomens estão extremamente ativos."
    elif 2 <= day <= 7:
        return "🌖 Lua Minguante Gibosa", "A iluminação noturna começa a diminuir lentamente."
    elif 8 <= day <= 14:
        return "🌗 Quarto Minguante", "Noites mais escuras no vale."
    elif day == 15:
        return "🌑 Lua Nova (New Moon)", "Escuridão absoluta durante a noite. Bônus para furtividade e criaturas das sombras."
    elif 16 <= day <= 21:
        return "🌓 Quarto Crescente", "A luz prateada reaparece gradualmente no céu nublado."
    else:
        return "🌔 Lua Crescente Gibosa", "Aproxima-se novamente a noite de Lua Cheia."

def advance_time(hours, minutes):
    """Advances session state time and updates day/moon/year as needed"""
    total_minutes = st.session_state["cal_minute"] + minutes
    added_hours = hours + (total_minutes // 60)
    st.session_state["cal_minute"] = total_minutes % 60
    
    total_hours = st.session_state["cal_hour"] + added_hours
    added_days = total_hours // 24
    st.session_state["cal_hour"] = total_hours % 24
    
    if added_days > 0:
        current_day = st.session_state["cal_day"] + added_days
        while current_day > 28:
            current_day -= 28
            st.session_state["cal_moon_idx"] += 1
            if st.session_state["cal_moon_idx"] >= 12:
                st.session_state["cal_moon_idx"] = 0
                st.session_state["cal_year"] += 1
        st.session_state["cal_day"] = current_day

# ---------------------------------------------------------
# LOCATIONS DATASET (Markers A to Z - User Custom List)
# ---------------------------------------------------------
LOCATIONS = {
    "A": {"name": "A - Velha estrada Svalich", "region": "Svalich Woods East", "desc": "Estrada de terra e cascalho que dá acesso ao vale de Baróvia vinda das névoas orientais."},
    "B": {"name": "B - Portões da Baróvia", "region": "Svalich Woods East", "desc": "Os imponentes portões de ferro guardados por estátuas decapitadas que marcam a entrada oficial de Baróvia."},
    "C": {"name": "C - Floresta Svalich", "region": "Svalich Woods East", "desc": "Bosque antigo e fechado, envolto em névoa perpétua e árvores morder-de-lobo."},
    "D": {"name": "D - Rio Ivlis", "region": "River Ivlis", "desc": "Rio de águas escuras e geladas que corre paralelamente à estrada ao sul da Vila da Baróvia."},
    "E": {"name": "E - Vila da Baróvia", "region": "Village of Barovia", "desc": "O melancólico e oprimido povoado situado à sombra do Castelo Ravenloft, lar de Ismark e Ireena."},
    "F": {"name": "F - Encruzilhada do Rio Ivlis", "region": "Ivlis Crossroads", "desc": "Entroncamento chave onde a estrada se divide rumo ao Lago Tser, Castelo Ravenloft e Vallaki."},
    "G": {"name": "G - Acampamento do Lago Tser", "region": "Tser Pool", "desc": "O colorido e acolhedor acampamento dos Vistani à beira do lago, onde fica a tenda da Madame Eva."},
    "H": {"name": "H - Cachoeiras Tser", "region": "Tser Falls", "desc": "Umas impressionantes quedas d'água de 160 metros cruzadas por uma ponte de pedra que leva aos penhascos."},
    "I": {"name": "I - Carruagem Negra", "region": "Ravenloft Precipice", "desc": "O ponto de paragem no precipício onde a misteriosa carruagem sem condutor aguarda convidados de Strahd."},
    "J": {"name": "J - Portões de Ravenloft", "region": "Ravenloft Gates", "desc": "Os pesados portões de ferro que dão acesso ao pátio do castelo sobre o abismo."},
    "K": {"name": "K - Castelo Ravenloft", "region": "Castle Ravenloft", "desc": "A lendária e gótica fortaleza do Conde Strahd von Zarovich que domina todo o vale."},
    "L": {"name": "L - Lago Zarovich", "region": "Lake Zarovich", "desc": "Grande corpo de água escura e fria situado ao norte de Vallaki."},
    "M": {"name": "M - O mago louco do monte Barotok", "region": "Mount Baratok", "desc": "Nas encostas geladas do Monte Baratok, local do esconderijo do poderoso e amnésico Mago Louco."},
    "N": {"name": "N - Cidade de Vallaki", "region": "Town of Vallaki", "desc": "A maior comunidade murada de Baróvia, governada com mão de ferro sob a ilusão de felicidades compulsórias."},
    "O": {"name": "O - O velho Mói ossos", "region": "Old Bonegrinder", "desc": "Moinho de vento decadente construído no topo de uma colina, lar das terríveis bruxas do crepúsculo."},
    "P": {"name": "P - Encruzilhada do Rio Luna", "region": "Luna Crossroads", "desc": "Bifurcação estratégica que conecta Vallaki a Krezk, Argynvostholt, Berez e a Torre de Van Richten."},
    "Q": {"name": "Q - Argynvostholt", "region": "Argynvostholt", "desc": "A mansão fortificada em ruínas que serviu de quartel-general para a antiga Ordem do Dragão de Prata."},
    "R": {"name": "R - Encruzilhada do Rio Corvo", "region": "Raven River Crossroads", "desc": "Cruzamento nas terras ocidentais conectando o caminho para Krezk, o Vinhedo e as montanhas."},
    "S": {"name": "S - Krezk", "region": "Village of Krezk", "desc": "Comunidade fortificada nas montanhas ocidentais, coroada pela misteriosa Abadia de Santa Markovia."},
    "T": {"name": "T - Passagem Tsolenka", "region": "Tsolenka Pass", "desc": "Uma ponte de pedra e fortaleza em ruínas encravada nas alturas congeladas do Monte Ghakis."},
    "U": {"name": "U - Ruínas de Berez", "region": "Berez", "desc": "Povoado abandonado e submerso no pântano, dominado pela bruxa Baba Lysaga e sua cabana ambulante."},
    "V": {"name": "V - Torre de Van Richten", "region": "Lake Baratok", "desc": "Antiga torre de quatro andares no Lago Baratok, protegida por um poderoso campo anti-magia."},
    "W": {"name": "W - O mago dos vinhos", "region": "Wizard of Wines Winery", "desc": "O lendário vinhedo mantido pela família Martikov, única fonte do amado vinho de Baróvia."},
    "X": {"name": "X - O templo âmbar", "region": "Amber Temple", "desc": "Um antigo e secreto santuário oculto nas neves do Monte Ghakis, sarcófago dos Poderes Sombrios."},
    "Y": {"name": "Y - Colina D'antes", "region": "Yester Hill", "desc": "Um túmulo druídico e círculo de pedras sagrado no topo da colina, local de rituais profanos."},
    "Z": {"name": "Z - Covil dos Lobisomens", "region": "Svalich Woods West", "desc": "Caverna sombria e escondida nas florestas do noroeste, abrigo da matilha de Kiril."}
}

# ---------------------------------------------------------
# ROAD NETWORK GRAPH (Hex Distances between adjacent markers)
# ---------------------------------------------------------
GRAPH_HEXES = {
    "A": [("B", 8, "road")],
    "B": [("A", 8, "road"), ("C", 6, "road")],
    "C": [("B", 6, "road"), ("E", 10, "road")],
    "D": [("E", 4, "road")],
    "E": [("C", 10, "road"), ("D", 4, "road"), ("F", 16, "road")],
    "F": [("E", 16, "road"), ("G", 6, "road"), ("I", 12, "road"), ("O", 20, "road")],
    "G": [("F", 6, "road"), ("H", 8, "road")],
    "H": [("G", 8, "road"), ("I", 10, "road")],
    "I": [("F", 12, "road"), ("H", 10, "road"), ("J", 6, "road")],
    "J": [("I", 6, "road"), ("K", 6, "road")],
    "K": [("J", 6, "road")],
    "O": [("F", 20, "road"), ("N", 12, "road")],
    "N": [("O", 12, "road"), ("L", 4, "road"), ("P", 16, "road")],
    "L": [("N", 4, "road"), ("M", 16, "difficult")],
    "M": [("L", 16, "difficult")],
    "P": [("N", 16, "road"), ("V", 12, "road"), ("R", 16, "road"), ("Q", 14, "road"), ("U", 24, "difficult")],
    "Q": [("P", 14, "road"), ("U", 18, "difficult"), ("T", 22, "mountain")],
    "R": [("P", 16, "road"), ("V", 8, "road"), ("S", 10, "road"), ("W", 18, "road")],
    "S": [("R", 10, "road"), ("Z", 16, "difficult")],
    "Z": [("S", 16, "difficult")],
    "V": [("P", 12, "road"), ("R", 8, "road")],
    "W": [("R", 18, "road"), ("Y", 22, "difficult"), ("U", 28, "difficult")],
    "Y": [("W", 22, "difficult")],
    "U": [("P", 24, "difficult"), ("Q", 18, "difficult"), ("W", 28, "difficult")],
    "T": [("Q", 22, "mountain"), ("X", 36, "mountain")],
    "X": [("T", 36, "mountain")]
}

def dijkstra_path(start, end):
    queue = [(0, start, [])]
    seen = set()
    while queue:
        (cost_hexes, node, path) = heapq.heappop(queue)
        if node in seen:
            continue
        seen.add(node)
        path = path + [node]
        if node == end:
            return cost_hexes, path
        for neighbor, weight_hexes, terrain_type in GRAPH_HEXES.get(node, []):
            if neighbor not in seen:
                heapq.heappush(queue, (cost_hexes + weight_hexes, neighbor, path))
    return float("inf"), []

def get_day_night_status(hour):
    if 6 <= hour < 8:
        return "🌄 Alvorada Nebulosa", "Luz fraca. A névoa fria se ergue dos solos de Baróvia.", "Baixo"
    elif 8 <= hour < 18:
        return "☁️ Dia Pálido", "Luz pálida constante. O céu permanece cinzento e sem sol visível.", "Médio"
    elif 18 <= hour < 20:
        return "🌆 Crepúsculo de Sangue", "Luz fraca. Sombras se alongam e a temperatura cai rapidamente.", "Alto"
    else:
        return "🌙 Noite Profunda", "Escuridão Total. As forças de Strahd e monstros vagam livremente.", "Muito Alto"

def get_detailed_weather(region, hour):
    """Returns detailed weather description based on region and hour"""
    is_night = (hour < 6 or hour >= 18)
    
    if "Mountain" in region or region in ["Mount Ghakis", "Krezk Pass", "Amber Temple", "Tsolenka Pass"]:
        if is_night:
            return "🌨️ **Tempestade de Neve Severa**: Vento uivante congelante, neve intensa e frio extremo (-15°C). Visibilidade quase nula."
        else:
            return "❄️ **Frio Intenso e Vento Geado**: Neve fraca e rajadas de vento das montanhas Balinok. Névoa congelante."
    elif "Svalich" in region or region in ["Svalich Woods", "Svalich Woods West", "Svalich Woods East"]:
        if is_night:
            return "🌫️ **Névoa Negra e Garoa Fria**: Neblina impenetrável na altura dos joelhos. Barulho crepitante nos galhos."
        else:
            return "☁️ **Garoa Constante e Névoa Baixa**: Umidade alta, solo lamacento e cheiro forte de agulhas de pinheiro."
    elif "Lake" in region or region in ["Lake Zarovich", "Lake Baratok"]:
        if is_night:
            return "🌁 **Nevoeiro Aquático Denso**: Chuva fria sobre a superfície do lago e visibilidade reduzida a 3 metros."
        else:
            return "🌫️ **Brisa Fria e Névoa Rastejante**: Águas escuras espelhadas sob o céu cinzento e opaco."
    elif region == "Berez":
        return "🌧️ **Chuva Torrencial e Pântano**: Lamaçal pesado, nuvens de insetos famintos e névoa fétida de decomposição."
    else:
        if is_night:
            return "🌌 **Vento Gelado e Névoa Noturna**: Temperatura em queda livre, silêncio sepulcral interrompido por uivos distantes."
        else:
            return "☁️ **Céu Pálido e Carregado**: Cobertura contínua de nuvens cinzentas sem raio de sol direto."

# ---------------------------------------------------------
# RANDOM ENCOUNTER TABLES (Official Curse of Strahd Ch. 2)
# ---------------------------------------------------------
RANDOM_ENCOUNTERS = {
    "day": [
        (2, "3d6 Plebeus Barovianos assustados viajando pela estrada."),
        (3, "1d6 Batedores Barovianos patrulhando com bestas engatilhadas."),
        (4, "Armadilha de caça de ferro oculta sob agulhas de pinheiro (Sobrevivência CD 15 para detectar)."),
        (5, "Sepultura rasa profanada ao lado da estrada."),
        (6, "Trilha falsa criada por druidas levando a um fosso de estacas."),
        (7, "1d4+1 Bandidos Vistanis acampados fumando cachimbo (oferecem ser guias por 100 po)."),
        (8, "Cavaleiro Esquelético silencioso montado em um cavalo morto."),
        (9, "Bugiganga gótica abandonada na lama."),
        (10, "Pacote escondido embrulhado em couro em um tronco cavado."),
        (11, "1d4 Enxames de Morcegos (50%) ou 1 Homem-Corvo na forma de corvo (50%)."),
        (12, "1d6 Lobos Atrozes famintos rosnando na névoa."),
        (13, "3d6 Lobos cercando o grupo lentamente."),
        (14, "1d4 Furiosos druídicos gritando impropérios."),
        (15, "Cadáver recente de um Baroviano com marcas de garras e uma carta na mão."),
        (16, "1d6 Lobisomens na forma humana fingindo ser caçadores perdidos."),
        (17, "1 Druida com 2d6 Galhos Infectados e vegetação maligna."),
        (18, "2d4 Espetos Infectados surgindo da terra."),
        (19, "1d6 Espantalhos macabros criados por Baba Lysaga."),
        (20, "1 Ressurgido da Ordem do Dragão de Prata buscando vingança contra Strahd.")
    ],
    "night": [
        (2, "1 Fantasma de um aventureiro caído lamentando seu destino."),
        (3, "Armadilha de caça de ferro enferrujada oculta na escuridão."),
        (4, "Sepultura antiga com restos mortais em cota de malha."),
        (5, "Bugiganga amaldiçoada pulsando levemente."),
        (6, "Cadáver em decomposição exalando odor fétido."),
        (7, "Pacote escondido contendo suprimentos velhos."),
        (8, "Cavaleiro Esquelético em patrulha eterna."),
        (9, "1d8 Enxames de Morcegos cobrindo o céu noturno."),
        (10, "1d6 Lobos Atrozes gigantescos caçando na escuridão."),
        (11, "3d6 Lobos famintos uivando em coro."),
        (12, "1d4 Furiosos do culto druídico realizando um ritual."),
        (13, "1 Druida e 2d6 Galhos Infectados em emboscada."),
        (14, "2d4 Espetos Infectados rastejando no escuro."),
        (15, "1d6 Lobisomens na forma de lobo saltando dos arbustos."),
        (16, "3d6 Zumbis cambaleantes se arrastando em direção ao grupo."),
        (17, "1d6 Espantalhos perseguindo os viajantes."),
        (18, "1d8 Zumbis de Strahd trajando restos de fardas do castelo."),
        (19, "1 Fogo-Fátuo tentando atrair jogadores para o pântano."),
        (20, "1 Ressurgido ou o próprio Conde Strahd von Zarovich observando das sombras.")
    ]
}

# ---------------------------------------------------------
# APP UI & HEADER
# ---------------------------------------------------------
st.title("🏰 Mapa Interativo e Calculadora de Viagem — Baróvia")
st.caption("Ferramenta de navegação, calendário oficial e simulação de deslocamento para A Maldição de Strahd (D&D 5e)")

# ---------------------------------------------------------
# CALENDAR STATUS BAR (Top Section)
# ---------------------------------------------------------
curr_moon = BAROVIAN_MOONS[st.session_state["cal_moon_idx"]]
moon_phase_name, moon_phase_desc = get_moon_phase(st.session_state["cal_day"])
curr_time_str = f"{st.session_state['cal_hour']:02d}:{st.session_state['cal_minute']:02d}"

st.markdown(f"""
<div class="metric-card">
    <h4>📅 Calendário de Baróvia: Ano {st.session_state['cal_year']} AR | {curr_moon['name']} ({curr_moon['title']}) — Dia {st.session_state['cal_day']} / 28</h4>
    <p style="margin-bottom:0px;">⏰ <b>Horário Atual:</b> {curr_time_str} | 🍂 <b>Estação:</b> {curr_moon['season']} | 🌙 <b>Fase da Lua:</b> {moon_phase_name}</p>
    <small style="color:#aaa;"><i>{moon_phase_desc}</i></small>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# SIDEBAR CONTROLS
# ---------------------------------------------------------
st.sidebar.header("⚙️ Parâmetros de Viagem")

hex_scale_choice = st.sidebar.selectbox(
    "Escala por Hexágono:",
    ["1 Hexágono = 1.5 Milhas", "1 Hexágono = 2.0 Milhas", "1 Hexágono = 0.25 Milhas (Oficial CoS)"],
    index=0
)

if "1.5" in hex_scale_choice:
    HEX_TO_MILES = 1.5
elif "2.0" in hex_scale_choice:
    HEX_TO_MILES = 2.0
else:
    HEX_TO_MILES = 0.25

origin_key = st.sidebar.selectbox("Ponto de Origem:", list(LOCATIONS.keys()), format_func=lambda x: LOCATIONS[x]["name"], index=4)  # E - Vila da Baróvia
dest_key = st.sidebar.selectbox("Ponto de Destino:", list(LOCATIONS.keys()), format_func=lambda x: LOCATIONS[x]["name"], index=5)    # F - Encruzilhada do Rio Ivlis

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

march_mode = st.sidebar.radio("Modo de Marcha (D&D 5e):", ["Marcha Padrão (8h/dia + Pernoite de 16h)", "Marcha Contínua (Sem Pernoite)"])

# ---------------------------------------------------------
# MAIN TABS LAYOUT
# ---------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🧭 Calculadora de Rota", "📅 Calendário de Baróvia", "🎲 Tabela de Encontros", "📍 Marcadores (A a Z)", "🗺️ Visualizador do Mapa"])

with tab1:
    if origin_key == dest_key:
        st.warning("⚠️ Selecione um destino diferente da origem para calcular a rota.")
    else:
        total_hexes, path = dijkstra_path(origin_key, dest_key)
        
        if total_hexes == float("inf"):
            st.error("Não foi encontrada uma rota conectada entre estes pontos.")
        else:
            total_miles = total_hexes * HEX_TO_MILES
            effective_speed = speed_mph / terrain_mult
            march_hours_total = total_miles / effective_speed
            
            march_h = int(march_hours_total)
            march_m = int((march_hours_total - march_h) * 60)
            
            # Calculate arrival datetime & elapsed hours considering marching mode
            start_hour = st.session_state["cal_hour"]
            start_min = st.session_state["cal_minute"]
            
            if "Standard" in march_mode or "Padrão" in march_mode:
                full_days_march = int(march_hours_total // 8)
                rem_hours_march = march_hours_total % 8
                elapsed_hours_total = (full_days_march * 24.0) + rem_hours_march
            else:
                elapsed_hours_total = march_hours_total
                
            elapsed_h = int(elapsed_hours_total)
            elapsed_m = int((elapsed_hours_total - elapsed_h) * 60)
            
            # Calculate expected arrival time
            arrival_minute_sum = start_min + elapsed_m
            arrival_min = arrival_minute_sum % 60
            extra_h = arrival_minute_sum // 60
            
            arrival_hour_sum = start_hour + elapsed_h + extra_h
            arrival_hour = arrival_hour_sum % 24
            added_days = arrival_hour_sum // 24
            
            arrival_day = st.session_state["cal_day"] + added_days
            arrival_moon_idx = st.session_state["cal_moon_idx"]
            arrival_year = st.session_state["cal_year"]
            
            while arrival_day > 28:
                arrival_day -= 28
                arrival_moon_idx += 1
                if arrival_moon_idx >= 12:
                    arrival_moon_idx = 0
                    arrival_year += 1
                    
            arrival_moon_name = BAROVIAN_MOONS[arrival_moon_idx]["name"]
            phase, phase_desc, hazard_level = get_day_night_status(arrival_hour)
            destination_region = LOCATIONS[dest_key]["region"]
            weather = get_detailed_weather(destination_region, arrival_hour)
            
            # Metrics Overview
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Distância Total", f"{total_miles:.1f} milhas", f"{total_hexes:.0f} hexágonos ({HEX_TO_MILES} mi/hex)")
            with col2:
                st.metric("Tempo de Caminhada", f"{march_h}h {march_m}min", f"Tempo decorrido: {elapsed_h}h {elapsed_m}min")
            with col3:
                st.metric("Chegada Prevista", f"{arrival_hour:02d}:{arrival_min:02d}", f"Dia {arrival_day} de {arrival_moon_name}")
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
                if "Padrão" in march_mode:
                    st.info("⛺ **Modo de Marcha Padrão D&D 5e**: O grupo caminha 8 horas por dia e faz pernoite/descanso de 16h entre as jornadas.")
                else:
                    st.warning("⚡ **Modo Marcha Contínua**: O grupo caminha sem realizar pausa para pernoite.")
            with c_b:
                st.markdown(f"**Iluminação na Chegada:** {phase}")
                st.caption(phase_desc)
                st.markdown(f"**Clima Predominante:** {weather}")
            
            # Route Steps
            st.subheader("🛣️ Rota Recomendada")
            path_names = " ➔ ".join([f"**[{node}]** {LOCATIONS[node]['name'].split(' - ')[1]}" for node in path])
            st.info(f"Caminho: {path_names}")
            
            # Calendar Advance Action Button
            st.markdown("---")
            st.subheader("⏱️ Atualizar Calendário da Mesa")
            if st.button(f"🚀 Confirmar Viagem e Avançar Calendário (+{elapsed_h}h {elapsed_m}min)"):
                advance_time(elapsed_h, elapsed_m)
                st.success("✅ Calendário atualizado com sucesso!")
                st.rerun()

with tab2:
    st.subheader("📅 Controle do Calendário e Tempo de Baróvia")
    st.markdown("Gerencie a contagem de dias, fases da lua e eventos de tempo da sua campanha.")
    
    st.markdown("### ⏳ Avançar Tempo Manualmente")
    c_btn1, c_btn2, c_btn3, c_btn4 = st.columns(4)
    with c_btn1:
        if st.button("➕ 1 Hora", key="cal_add_1h"):
            advance_time(1, 0)
            st.rerun()
    with c_btn2:
        if st.button("➕ 4 Horas", key="cal_add_4h"):
            advance_time(4, 0)
            st.rerun()
    with c_btn3:
        if st.button("☀️ Descanso Longo (8h)", key="cal_add_8h"):
            advance_time(8, 0)
            st.rerun()
    with c_btn4:
        if st.button("📅 Avançar 1 Dia", key="cal_add_24h"):
            advance_time(24, 0)
            st.rerun()
            
    st.markdown("---")
    st.markdown("### ⏱️ Avançar Tempo Personalizado")
    col_custom_h, col_custom_m, col_custom_btn = st.columns([2, 2, 3])
    with col_custom_h:
        custom_hours = st.number_input("Horas:", min_value=0, max_value=500, value=2)
    with col_custom_m:
        custom_mins = st.number_input("Minutos:", min_value=0, max_value=59, value=0)
    with col_custom_btn:
        st.write("")
        st.write("")
        if st.button("⏩ Avançar Tempo Personalizado"):
            advance_time(custom_hours, custom_mins)
            st.success(f"Avançado {custom_hours}h {custom_mins}min!")
            st.rerun()

    st.markdown("---")
    with st.expander("🛠️ Ajuste Manual do Mestre (DM Override)"):
        st.caption("Ajuste data e hora diretamente se necessário:")
        over_year = st.number_input("Ano:", value=st.session_state["cal_year"])
        over_moon = st.selectbox("Mês / Lua:", range(12), format_func=lambda x: f"{BAROVIAN_MOONS[x]['name']} ({BAROVIAN_MOONS[x]['title']})", index=st.session_state["cal_moon_idx"])
        over_day = st.number_input("Dia (1 a 28):", min_value=1, max_value=28, value=st.session_state["cal_day"])
        over_hour = st.number_input("Hora (0 a 23):", min_value=0, max_value=23, value=st.session_state["cal_hour"])
        over_min = st.number_input("Minutos (0 a 59):", min_value=0, max_value=59, value=st.session_state["cal_minute"])
        if st.button("💾 Salvar Ajuste Manual"):
            st.session_state["cal_year"] = over_year
            st.session_state["cal_moon_idx"] = over_moon
            st.session_state["cal_day"] = over_day
            st.session_state["cal_hour"] = over_hour
            st.session_state["cal_minute"] = over_min
            st.success("Calendário atualizado manualmente!")
            st.rerun()

    st.markdown("---")
    st.markdown("### 📜 O Calendário Baroviano (12 Luas de 28 Dias)")
    st.dataframe(
        [{"Mês / Lua": m["name"], "Título": m["title"], "Estação": m["season"]} for m in BAROVIAN_MOONS],
        use_container_width=True,
        hide_index=True
    )

with tab3:
    st.subheader("🎲 Tabela de Encontros Aleatórios nas Estradas de Baróvia")
    st.caption("Conforme as regras oficiais do Capítulo 2 de A Maldição de Strahd (D&D 5e)")
    
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        st.markdown("### ☀️ Encontros Diurnos (d12 + d8)")
        st.dataframe(
            [{"Rolagem": f"{item[0]}", "Evento / Criatura": item[1]} for item in RANDOM_ENCOUNTERS["day"]],
            use_container_width=True,
            hide_index=True
        )
    with col_e2:
        st.markdown("### 🌙 Encontros Noturnos (d12 + d8)")
        st.dataframe(
            [{"Rolagem": f"{item[0]}", "Evento / Criatura": item[1]} for item in RANDOM_ENCOUNTERS["night"]],
            use_container_width=True,
            hide_index=True
        )
        
    st.markdown("---")
    st.subheader("🎲 Gerador Rápido de Encontro Aleatório")
    road_type = st.radio("Local da Viagem:", ["Estrada Principal (Encontro em 18-20)", "Ermos / Floresta Fechada (Encontro em 15-20)"])
    
    if st.button("Rolar Teste de Encontro (a cada 30 minutos de viagem)"):
        roll = random.randint(1, 20)
        target = 18 if "Estrada" in road_type else 15
        
        is_night = (st.session_state["cal_hour"] < 6 or st.session_state["cal_hour"] >= 18)
        table_key = "night" if is_night else "day"
        
        if roll >= target:
            enc_roll = random.randint(1, 12) + random.randint(1, 8)
            matching_enc = next((item[1] for item in RANDOM_ENCOUNTERS[table_key] if item[0] == enc_roll), "Nenhum encontro específico.")
            st.error(f"🚨 **ENCONTRO ALEATÓRIO!** (Rolagem no d20: **{roll}** >= {target})")
            st.markdown(f"**Resultado da Tabela ({'Noturna' if is_night else 'Diurna'} - Rolagem {enc_roll}):**")
            st.warning(f"🧟 **{matching_enc}**")
        else:
            st.success(f"✅ **Caminho Seguro.** (Rolagem no d20: **{roll}** < {target}). Nenhum encontro hostil neste trecho.")

with tab4:
    st.subheader("📍 Catálogo de Locais de Baróvia (Marcadores A a Z)")
    selected_loc = st.selectbox("Selecione um local para detalhes:", list(LOCATIONS.keys()), format_func=lambda x: LOCATIONS[x]["name"])
    loc_data = LOCATIONS[selected_loc]
    st.markdown(f"### {loc_data['name']}")
    st.markdown(f"**Região Geográfica:** `{loc_data['region']}`")
    st.markdown(f"**Descrição:** {loc_data['desc']}")
    
    st.markdown("---")
    st.dataframe(
        [{"Marcador": k, "Nome": v["name"], "Região": v["region"], "Descrição": v["desc"]} for k, v in LOCATIONS.items()],
        use_container_width=True
    )

with tab5:
    st.subheader("🖼️ Visualização do Mapa de Baróvia")
    
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
    
    found_images = []
    for ext in ["*.png", "*.PNG", "*.jpg", "*.jpeg", "*.webp", "*.JPG"]:
        found_images.extend(glob.glob(ext))
        found_images.extend(glob.glob(f"**/{ext}", recursive=True))
    
    seen_imgs = set()
    unique_images = []
    for img_path in found_images:
        if img_path not in seen_imgs:
            seen_imgs.add(img_path)
            unique_images.append(img_path)
            
    selected_image_path = None
    for cand in candidate_files:
        if os.path.exists(cand):
            selected_image_path = cand
            break
            
    if not selected_image_path and unique_images:
        selected_image_path = unique_images[0]
        
    if selected_image_path:
        try:
            image = Image.open(selected_image_path)
            st.success(f"📷 Imagem detectada e carregada: `{selected_image_path}`")
            st.image(image, caption=f"Mapa de Baróvia ({selected_image_path}) — Escala: 1 Hexágono = {HEX_TO_MILES} milhas", use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao abrir a imagem `{selected_image_path}`: {e}")
    else:
        st.warning("⚠️ Nenhuma imagem de mapa foi localizada automaticamente na pasta raiz do projeto.")
        st.markdown("---")
        st.markdown("**📁 Arquivos atualmente detectados na pasta do seu projeto:**")
        try:
            curr_files = os.listdir(".")
            st.code("\n".join(curr_files) if curr_files else "Nenhum arquivo encontrado")
        except Exception as ex:
            st.write(f"Não foi possível listar arquivos: {ex}")
