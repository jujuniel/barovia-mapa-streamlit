import streamlit as st
import datetime
import random
import heapq
import os
import glob
import re
import plotly.graph_objects as go
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
    .party-card {
        background-color: #27272a;
        border: 1px solid #3f3f46;
        border-radius: 6px;
        padding: 10px;
        text-align: center;
    }
    .alert-box {
        background-color: #450a0a;
        border: 2px solid #ef4444;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# CALENDAR CONSTANTS & SESSION STATE (Barovian Calendar)
# ---------------------------------------------------------
BAROVIAN_MOONS = [
    {"name": "Dekavr", "title": "Winter Moon", "season": "Inverno", "desc": "Início do inverno rigoroso nas montanhas Balinok."},
    {"name": "Yinyavr", "title": "Cold Moon", "season": "Inverno / Primavera", "desc": "Ventos congelantes e neve persistente."},
    {"name": "Fenravr", "title": "Wolf Moon", "season": "Primavera", "desc": "Alcateias de lobos caçam ativamente pelas estradas."},
    {"name": "Martavr", "title": "Raven Moon", "season": "Primavera", "desc": "Mês dos corvos e prenúncio de mudança no vale."},
    {"name": "Prylla", "title": "Rain Moon", "season": "Primavera / Verão", "desc": "Garoa constante e umidade vinda das montanhas."},
    {"name": "Mada", "title": "Maid Moon", "season": "Verão", "desc": "Dias ligeiramente mais claros, mas sem sol direto."},
    {"name": "Eyun", "title": "Summer Moon", "season": "Verão", "desc": "Aumento leve de temperatura e neblina densa nos lagos."},
    {"name": "Eyul", "title": "War Moon", "season": "Verão / Outono", "desc": "Memória das antigas batalhas de Strahd no vale."},
    {"name": "Ugavr", "title": "Wine Moon", "season": "Outono", "desc": "Época de colheita das uvas no vinhedo Mago dos Vinhos."},
    {"name": "Sintavr", "title": "Harvest Moon", "season": "Outono", "desc": "Preparação dos povoados para os meses frios."},
    {"name": "Ottyavr", "title": "Hunter's Moon", "season": "Outono / Inverno", "desc": "Temporada de caça intensa nos Bosques de Svalich."},
    {"name": "Neyavr", "title": "Rot Moon", "season": "Inverno", "desc": "Névoa fétida e podridão nos pântanos de Berez."}
]

if "cal_year" not in st.session_state:
    st.session_state["cal_year"] = 735
if "cal_moon_idx" not in st.session_state:
    st.session_state["cal_moon_idx"] = 3  # Martavr (Raven Moon)
if "cal_day" not in st.session_state:
    st.session_state["cal_day"] = 1
if "cal_hour" not in st.session_state:
    st.session_state["cal_hour"] = 8
if "cal_minute" not in st.session_state:
    st.session_state["cal_minute"] = 0
if "cal_second" not in st.session_state:
    st.session_state["cal_second"] = 0

# Travel & Encounter Session Tracking
if "travel_acc_min" not in st.session_state:
    st.session_state["travel_acc_min"] = 0
if "encounter_alert" not in st.session_state:
    st.session_state["encounter_alert"] = False

# XP Session State
if "party_xp" not in st.session_state:
    st.session_state["party_xp"] = {"Owen": 300, "Taketsu": 300, "Lony": 300, "Kael": 300}
if "xp_log" not in st.session_state:
    st.session_state["xp_log"] = []

XP_LEVELS = [
    (1, 0),
    (2, 300),
    (3, 900),
    (4, 2700),
    (5, 6500),
    (6, 14000),
    (7, 23000),
    (8, 34000),
    (9, 48000),
    (10, 64000),
    (11, 85000)
]

MONSTERS_DB = {
    "Plebeu Baroviano": {"cr": "0", "xp": 10},
    "Bandido Vistani": {"cr": "1/8", "xp": 25},
    "Galho Infectado (Twig Blight)": {"cr": "1/8", "xp": 25},
    "Esqueleto": {"cr": "1/4", "xp": 50},
    "Zumbi": {"cr": "1/4", "xp": 50},
    "Lobo": {"cr": "1/4", "xp": 50},
    "Enxame de Morcegos": {"cr": "1/4", "xp": 50},
    "Batedor Baroviano": {"cr": "1/2", "xp": 100},
    "Espeto Infectado (Needle Blight)": {"cr": "1/2", "xp": 100},
    "Cavaleiro Esquelético": {"cr": "1/2", "xp": 100},
    "Sombra (Shadow)": {"cr": "1/2", "xp": 100},
    "Lobo Atroaz (Dire Wolf)": {"cr": "1", "xp": 200},
    "Espantalho": {"cr": "1", "xp": 200},
    "Zumbi de Strahd": {"cr": "1", "xp": 200},
    "Aparição (Specter)": {"cr": "1", "xp": 200},
    "Carniçal (Ghoul)": {"cr": "1", "xp": 200},
    "Druida (Yester Hill)": {"cr": "2", "xp": 450},
    "Furioso (Berserker)": {"cr": "2", "xp": 450},
    "Homem-Corvo (Wereraven)": {"cr": "2", "xp": 450},
    "Fogo-Fátuo (Will-o'-Wisp)": {"cr": "2", "xp": 450},
    "Lobisomem": {"cr": "3", "xp": 700},
    "Fantasma": {"cr": "4", "xp": 1100},
    "Vampiro Cria (Vampire Spawn)": {"cr": "5", "xp": 1800},
    "Bruxa da Noite (Night Hag)": {"cr": "5", "xp": 1800},
    "Ressurgido (Revenant)": {"cr": "5", "xp": 1800},
    "Bruxa Baba Lysaga": {"cr": "11", "xp": 7200},
    "Conde Strahd von Zarovich": {"cr": "15", "xp": 13000},
    "Outro / Inimigo Personalizado": {"cr": "Custom", "xp": 0}
}

MILESTONES_DB = {
    "Escapar da Casa da Morte (Death House)": 500,
    "Localizar o Tomo de Strahd": 1000,
    "Localizar o Símbolo Sagrado do Corvo-Bondoso": 1000,
    "Localizar a Espada Solar (Sunsword)": 1500,
    "Aliança com os Vistani de Tser Pool / Madame Eva": 300,
    "Aliança com os Guardiões da Pena (Martikov)": 500,
    "Descobrir o Segredo das Bruxas no Velho Moedor de Ossos": 600,
    "Resolver a Crise Política de Vallaki": 800,
    "Restaurar o Vinhedo Mago dos Vinhos": 1000,
    "Purificar a Abadia de Santa Markovia em Krezk": 1000,
    "Descoberta de Segredo / Marco Livre": 0
}

def get_character_level(xp):
    current_lvl = 1
    for lvl, req in XP_LEVELS:
        if xp >= req:
            current_lvl = lvl
        else:
            break
    return current_lvl

def get_level_progress(xp):
    current_lvl = get_character_level(xp)
    if current_lvl >= 11:
        return current_lvl, 85000, 85000, 1.0, 0
    curr_req = dict(XP_LEVELS)[current_lvl]
    next_req = dict(XP_LEVELS)[current_lvl + 1]
    needed = next_req - xp
    progress = (xp - curr_req) / (next_req - curr_req)
    progress = min(max(progress, 0.0), 1.0)
    return current_lvl, curr_req, next_req, progress, needed

def get_moon_phase(day):
    """Returns the moon phase based on the 28-day Barovian cycle"""
    if day == 1:
        return "⚪ Lua Cheia (Full Moon)", "Os monstros de Baróvia e lobisomens estão extremamente ativos e agressivos."
    elif 2 <= day <= 7:
        return "🌖 Lua Minguante Gibosa", "A iluminação noturna começa a diminuir lentamente."
    elif 8 <= day <= 14:
        return "🌗 Quarto Minguante", "Noites de penumbra cinzenta no vale."
    elif day == 15:
        return "🌑 Lua Nova (New Moon)", "Escuridão absoluta. Bônus para furtividade e criaturas das sombras (ritual de Baba Lysaga)."
    elif 16 <= day <= 21:
        return "🌓 Quarto Crescente", "A luz prateada reaparece gradualmente no céu."
    else:
        return "🌔 Lua Crescente Gibosa", "Aproxima-se novamente a noite de Lua Cheia."

def advance_time(hours, minutes, seconds=0, is_travel=False):
    """Advances session state time and updates day/moon/year as needed"""
    total_sec = st.session_state["cal_second"] + seconds
    added_min_sec = total_sec // 60
    st.session_state["cal_second"] = total_sec % 60

    total_minutes = st.session_state["cal_minute"] + minutes + added_min_sec
    added_hours = hours + (total_minutes // 60)
    st.session_state["cal_minute"] = total_minutes % 60

    total_hours = st.session_state["cal_hour"] + added_hours
    added_days = total_hours // 24
    st.session_state["cal_hour"] = total_hours % 24

    if is_travel:
        elapsed_min = (hours * 60) + minutes + added_min_sec
        st.session_state["travel_acc_min"] += elapsed_min
        if st.session_state["travel_acc_min"] >= 30:
            st.session_state["encounter_alert"] = True

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
# LOCATIONS DATASET (Markers A to Z - User Custom Names)
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

MAP_COORDS = {
    "A": (1100, 360), "B": (1000, 370), "C": (900, 380), "D": (850, 460),
    "E": (830, 390), "F": (710, 390), "G": (670, 480), "H": (640, 320),
    "I": (710, 280), "J": (730, 230), "K": (750, 190), "L": (520, 210),
    "M": (480, 110), "N": (500, 310), "O": (600, 330), "P": (410, 370),
    "Q": (420, 470), "R": (270, 350), "S": (170, 250), "T": (470, 620),
    "U": (550, 560), "V": (330, 220), "W": (220, 480), "X": (580, 700),
    "Y": (130, 580), "Z": (120, 140)
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
        return "🌄 Alvorecer (Dawn)", "Luz fraca. A névoa fria se ergue dos solos de Baróvia.", "Baixo"
    elif 8 <= hour < 12:
        return "☁️ Manhã Pálida", "Luz pálida constante. O céu permanece cinzento e sem sol visível.", "Médio"
    elif 12 <= hour < 14:
        return "🌤️ Meio-Dia (Highsun)", "Céu pálido no ponto mais alto. Penumbra cinzenta.", "Médio"
    elif 14 <= hour < 18:
        return "🌫️ Tarde Fria", "Vento suave e queda leve de temperatura.", "Médio"
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

def parse_and_roll_dice(text):
    """Parses dice notations like 3d6, 1d6, 1d4+1, 2d4, 1d8, 1d4 and returns rolled total"""
    match = re.search(r'(\d+)d(\d+)(?:\+(\d+))?', text)
    if match:
        num_dice = int(match.group(1))
        dice_sides = int(match.group(2))
        bonus = int(match.group(3)) if match.group(3) else 0
        
        rolls = [random.randint(1, dice_sides) for _ in range(num_dice)]
        total = sum(rolls) + bonus
        rolls_str = " + ".join(str(r) for r in rolls)
        if bonus > 0:
            rolls_str += f" + {bonus}"
        return total, f"🎲 **Rolagem de Quantidade ({match.group(0)})**: `[{rolls_str}]` ➔ **{total} Inimigo(s)**"
    return 1, "🎲 **Quantidade Fixa**: **1 Inimigo / Evento**"

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
        (17, "1d6 Espantalhos perseguindo os后台."),
        (18, "1d8 Zumbis de Strahd trajando restos de fardas do castelo."),
        (19, "1 Fogo-Fátuo tentando atrair jogadores para o pântano."),
        (20, "1 Ressurgido ou o próprio Conde Strahd von Zarovich observando das sombras.")
    ]
}

# ---------------------------------------------------------
# APP UI & HEADER
# ---------------------------------------------------------
st.title("🏰 Mapa Interativo e Calculadora de Viagem — Baróvia")
st.caption("Ferramenta de navegação, calendário oficial, simulador de tempo D&D 5e e mapa interativo Plotly para A Maldição de Strahd")

# TOP CALENDAR QUICK-STATUS BADGE
curr_moon = BAROVIAN_MOONS[st.session_state["cal_moon_idx"]]
moon_phase_name, moon_phase_desc = get_moon_phase(st.session_state["cal_day"])
curr_time_str = f"{st.session_state['cal_hour']:02d}:{st.session_state['cal_minute']:02d}:{st.session_state['cal_second']:02d}"

st.markdown(f"""
<div class="metric-card">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h4 style="margin:0;">📅 Ano {st.session_state['cal_year']} AR | {curr_moon['name']} ({curr_moon['title']}) — Dia {st.session_state['cal_day']} de 28</h4>
            <p style="margin:2px 0 0 0;">⏰ <b>Horário:</b> {curr_time_str} | 🍂 <b>Estação:</b> {curr_moon['season']} | 🌙 <b>Fase da Lua:</b> {moon_phase_name}</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ENCOUNTER ALERT BANNER (If 30-min travel threshold reached)
if st.session_state.get("encounter_alert", False):
    st.markdown("""
    <div class="alert-box">
        <h3 style="margin:0; color:#ef4444;">🚨 ALERTA DE VIAGEM: 30 MINUTOS DECORRIDOS!</h3>
        <p style="margin:5px 0; font-size:16px;">O grupo caminhou por mais de 30 minutos na estrada de Baróvia. É necessário realizar um <b>Teste de Encontro Aleatório (d20)</b>!</p>
    </div>
    """, unsafe_allow_html=True)
    c_al1, c_al2 = st.columns([3, 1])
    with c_al1:
        if st.button("🎲 Rolar Teste de Encontro Agora (d20)", key="btn_alert_roll"):
            st.session_state["encounter_alert"] = False
            st.session_state["travel_acc_min"] = 0
            st.rerun()
    with c_al2:
        if st.button("❌ Dispensar Alerta", key="btn_alert_dismiss"):
            st.session_state["encounter_alert"] = False
            st.session_state["travel_acc_min"] = 0
            st.rerun()

# ---------------------------------------------------------
# SIDEBAR CONTROLS
# ---------------------------------------------------------
st.sidebar.header("⚙️ Parâmetros de Viagem")

hex_scale_choice = st.sidebar.selectbox("Escala do Hexágono:", ["1 Hex = 1.5 Milhas (Padrão Baróvia)", "1 Hex = 2.0 Milhas (Mapa Expandido)", "1 Hex = 0.25 Milhas (Oficial do Livro)"], index=0)
if "1.5" in hex_scale_choice:
    HEX_TO_MILES = 1.5
elif "2.0" in hex_scale_choice:
    HEX_TO_MILES = 2.0
else:
    HEX_TO_MILES = 0.25

origin_key = st.sidebar.selectbox("Ponto de Origem:", list(LOCATIONS.keys()), format_func=lambda x: LOCATIONS[x]["name"], index=4)  # E - Vila da Baróvia
dest_key = st.sidebar.selectbox("Ponto de Destino:", list(LOCATIONS.keys()), format_func=lambda x: LOCATIONS[x]["name"], index=5)    # F - Encruzilhada Rio Ivlis

pace = st.sidebar.radio("Ritmo de Viagem:", ["Normal (3 milhas/h)", "Rápido (4 milhas/h)", "Lento (2 milhas/h)"])
if "Normal" in pace:
    speed_mph = 3.0
    pace_note = "Sem modificadores de percepção. Chance Média-Alta de encontro."
elif "Rápido" in pace:
    speed_mph = 4.0
    pace_note = "Penalidade de -5 na Percepção Passiva e Teste de Exaustão. Chance Alta de encontro."
else:
    speed_mph = 2.0
    pace_note = "Permite mover-se em Furtividade. Chance Média-Baixa de encontro."

terrain = st.sidebar.selectbox("Modificador de Terreno:", ["Estrada Principal (1x)", "Terreno Difícil / Pântano (2x)", "Montanha / Neve (2.5x)"])
if "1x" in terrain:
    terrain_mult = 1.0
elif "2x" in terrain:
    terrain_mult = 2.0
else:
    terrain_mult = 2.5

march_mode = st.sidebar.radio("Modo de Marcha (D&D 5e):", ["Marcha Padrão (8h/dia + Pernoite de 16h)", "Marcha Contínua (Sem Pernoite)"])

st.sidebar.markdown("---")
st.sidebar.header("⏳ Controle Rápido de Tempo")
col_t1, col_t2 = st.sidebar.columns(2)
with col_t1:
    if st.button("➕ 1 Hora", key="sb_1h"):
        advance_time(1, 0)
        st.rerun()
    if st.button("☀️ Descanso Longo (8h)", key="sb_8h"):
        advance_time(8, 0)
        st.rerun()
with col_t2:
    if st.button("➕ 4 Horas", key="sb_4h"):
        advance_time(4, 0)
        st.rerun()
    if st.button("📅 Avançar 1 Dia", key="sb_1d"):
        advance_time(24, 0)
        st.rerun()

# ---------------------------------------------------------
# MAIN TABS LAYOUT
# ---------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🧭 Calculadora de Rota", 
    "⏱️ Relógio & Simulador D&D",
    "📅 Calendário de Baróvia", 
    "🎲 Tabela de Encontros", 
    "📊 Gestor de XP", 
    "📍 Marcadores & Mapa"
])

# ---------------------------------------------------------
# TAB 1: CALCULADORA DE ROTA (WITH PLOTLY INTERACTIVE MAP)
# ---------------------------------------------------------
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
            
            # Mists of Barovia Gate Detection
            passes_near_gates = any(node in ["A", "B"] for node in path)
            if passes_near_gates:
                st.error("🌫️ **PRESENÇA DAS BRUMAS MORTAIS DE BARÓVIA!** O trajeto passa próximo a **[A] Velha estrada Svalich** e **[B] Portões da Baróvia**. As Brumas Mágicas do Conde Strahd envolvem todas as fronteiras do vale. Tentar escapar pelas brumas sem a permissão do Conde provoca sufocamento mágico, desorientação e envenenamento, redirecionando os viajantes de volta para Baróvia.")

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
            
            # EXHAUSTION ROLLS SECTION
            st.markdown("---")
            st.subheader("🏋️ Testes de Resistência para Exaustão")
            
            has_exhaustion_risk = False
            
            if march_hours_total > 8.0 and "Contínua" in march_mode:
                has_exhaustion_risk = True
                extra_hours = int(march_hours_total - 8.0) + (1 if (march_hours_total - 8.0) % 1 > 0 else 0)
                st.warning(f"⚠️ **MARCHA FORÇADA (Mais de 8h de caminhada continuada)**: O trajeto exige **{march_h}h {march_m}min** de caminhada. O grupo ultrapassou o limite seguro de 8 horas diárias em **{extra_hours} hora(s) extra(s)**.")
                st.markdown("Cada personagem deve realizar um **Teste de Resistência de Constituição (Salvaguarda de CON)** para cada hora extra:")
                for ex_h in range(1, extra_hours + 1):
                    dc = 10 + ex_h
                    st.write(f"  * **{ex_h}ª Hora Extra (Hora {8 + ex_h} de marcha)** ➔ **CD {dc} de Constituição**. Falha: **+1 nível de Exaustão**.")
            
            if "Rápido" in pace:
                has_exhaustion_risk = True
                st.warning("⚡ **EXAUSTÃO POR RITMO RÁPIDO (4 milhas/h)**: Além de sofrer **-5 na Percepção Passiva**, manter o Ritmo Rápido por tempo prolongado impõe desgaste físico acelerado. O Mestre pode solicitar um **Teste de Constituição (CD 10)** para cada 4 horas de marcha rápida para evitar 1 nível de Exaustão.")

            if has_exhaustion_risk:
                if st.button("🎲 Rolar Teste de Resistência de Constituição (CON) do Grupo para Exaustão"):
                    st.markdown("#### 📊 Resultado dos Testes de Constituição (Exaustão):")
                    cols_ex = st.columns(4)
                    pcs_list = [("Owen", 2), ("Taketsu", 3), ("Lony", 1), ("Kael", 2)]
                    for idx, (name, con_mod) in enumerate(pcs_list):
                        roll_val = random.randint(1, 20)
                        tot_val = roll_val + con_mod
                        target_dc = 10 + (int(march_hours_total - 8.0) if march_hours_total > 8 else 0)
                        
                        with cols_ex[idx]:
                            if tot_val >= target_dc:
                                st.success(f"**{name}**: Rolou `{roll_val} + {con_mod} = {tot_val}` ➔ ✅ **Passou** (Sem exaustão)")
                            else:
                                st.error(f"**{name}**: Rolou `{roll_val} + {con_mod} = {tot_val}` ➔ ❌ **FALHOU!** (+1 Nível de Exaustão)")
            else:
                st.success("✅ **Caminhada Dentro do Limite Seguro**: Nenhuma rolagem de exaustão necessária (menos de 8h de marcha em ritmo normal/lento).")

            # Route Steps
            st.markdown("---")
            st.subheader("🛣️ Rota Recomendada")
            path_names = " ➔ ".join([f"**[{node}]** {LOCATIONS[node]['name'].split(' - ')[1]}" for node in path])
            st.info(f"Caminho: {path_names}")

            # Plotly Interactive Map Overlay
            st.markdown("---")
            st.subheader("🗺️ Traçado da Rota no Mapa Interativo de Baróvia")
            
            candidate_files = ["mapa_de_barovia.png", "mapa_de_barovia.PNG", "mapa de barovia.PNG", "mapa de barovia.png", "1.PNG", "1.png"]
            found_img_path = None
            for cand in candidate_files:
                if os.path.exists(cand):
                    found_img_path = cand
                    break
            if not found_img_path:
                for ext in ["*.png", "*.PNG", "*.jpg", "*.jpeg"]:
                    match = glob.glob(ext)
                    if match:
                        found_img_path = match[0]
                        break
                        
            if found_img_path:
                try:
                    img = Image.open(found_img_path)
                    width, height = img.size
                    
                    fig = go.Figure()
                    fig.add_layout_image(
                        dict(
                            source=img,
                            xref='x', yref='y',
                            x=0, y=height,
                            sizex=width, sizey=height,
                            sizing='stretch',
                            opacity=0.9,
                            layer='below'
                        )
                    )
                    
                    # Plot subtle background road connections
                    for n1, neighbors in GRAPH_HEXES.items():
                        if n1 in MAP_COORDS:
                            x1, y1 = MAP_COORDS[n1]
                            for n2, w, t_type in neighbors:
                                if n2 in MAP_COORDS and n1 < n2:
                                    x2, y2 = MAP_COORDS[n2]
                                    fig.add_trace(go.Scatter(
                                        x=[x1, x2],
                                        y=[height - y1, height - y2],
                                        mode='lines',
                                        line=dict(color='#52525b', width=2, dash='dot'),
                                        hoverinfo='none',
                                        showlegend=False
                                    ))
                                    
                    # Plot active Dijkstra route line
                    rx = [MAP_COORDS[node][0] for node in path if node in MAP_COORDS]
                    ry = [height - MAP_COORDS[node][1] for node in path if node in MAP_COORDS]
                    
                    fig.add_trace(go.Scatter(
                        x=rx, y=ry,
                        mode='lines+markers',
                        line=dict(color='#ef4444', width=6),
                        marker=dict(size=12, color='#f59e0b'),
                        name='Rota Traçada',
                        hoverinfo='text',
                        hovertext=[f"<b>Ponto [{n}]</b>: {LOCATIONS[n]['name']}" for n in path if n in LOCATIONS]
                    ))
                    
                    # Plot markers A to Z
                    all_x, all_y, all_txt, all_colors, all_symbols = [], [], [], [], []
                    
                    for k, coords in MAP_COORDS.items():
                        all_x.append(coords[0])
                        all_y.append(height - coords[1])
                        all_txt.append(f"<b>[{k}]</b> {LOCATIONS[k]['name']}<br><i>{LOCATIONS[k]['region']}</i><br>{LOCATIONS[k]['desc']}")
                        if k == origin_key:
                            all_colors.append('#22c55e')  # Green for Start
                            all_symbols.append('star')
                        elif k == dest_key:
                            all_colors.append('#dc2626')  # Red for End
                            all_symbols.append('diamond')
                        elif k in path:
                            all_colors.append('#f59e0b')  # Amber for Path
                            all_symbols.append('circle')
                        else:
                            all_colors.append('#71717a')  # Grey for Others
                            all_symbols.append('circle')
                            
                    fig.add_trace(go.Scatter(
                        x=all_x, y=all_y,
                        mode='markers+text',
                        marker=dict(size=16, color=all_colors, symbol=all_symbols, line=dict(width=2, color='#000000')),
                        text=[f"<b>{k}</b>" for k in MAP_COORDS.keys()],
                        textposition="top center",
                        textfont=dict(color='white', size=13),
                        hoverinfo='text',
                        hovertext=all_txt,
                        showlegend=False
                    ))
                    
                    fig.update_xaxes(range=[0, width], visible=False)
                    fig.update_yaxes(range=[0, height], visible=False)
                    fig.update_layout(
                        margin=dict(l=0, r=0, t=20, b=0),
                        height=680,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("📍 **Legenda do Mapa Interativo Plotly**: 🟢 **Verde (Estrela)** = Origem | 🔴 **Vermelho (Losango)** = Destino | 🟡 **Laranja** = Trajeto Conectado | ⚪ **Cinza** = Outros Marcadores")
                except Exception as ex:
                    st.error(f"Erro ao gerar mapa Plotly: {ex}")
            else:
                st.warning("Imagem `mapa_de_barovia.png` não encontrada localmente. Faça o upload no GitHub.")
            
            # Calendar Advance Action Button
            st.markdown("---")
            st.subheader("⏱️ Atualizar Calendário da Mesa")
            if st.button(f"🚀 Confirmar Viagem e Avançar Calendário (+{elapsed_h}h {elapsed_m}min)"):
                advance_time(elapsed_h, elapsed_m, is_travel=True)
                st.success("✅ Calendário e tempo de viagem atualizados com sucesso!")
                st.rerun()

# ---------------------------------------------------------
# TAB 2: RELÓGIO & SIMULADOR D&D 5E
# ---------------------------------------------------------
with tab2:
    st.subheader("⏱️ Relógio de Jogo e Simulador de Tempo D&D 5e")
    st.caption("Controle preciso do fluxo do tempo de jogo divididos nas três escalas fundamentais de Dungeons & Dragons 5a Edição.")
    
    # Active Status Box
    st.markdown(f"""
    <div style="background-color:#1c1917; border:2px solid #b91c1c; padding:20px; border-radius:8px; margin-bottom:20px;">
        <h3 style="margin-top:0; color:#ef4444;">⏱️ Relógio de Jogo Ativo</h3>
        <p style="font-size:18px;"><b>Horário Atual:</b> {curr_time_str}</p>
        <p style="font-size:18px;"><b>Fase Diurna:</b> {get_day_night_status(st.session_state['cal_hour'])[0]}</p>
        <p style="font-size:16px; margin-bottom:0;"><b>Data Baroviana:</b> Dia {st.session_state['cal_day']} de {curr_moon['name']} (Ano {st.session_state['cal_year']} AR)</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 1. Combat & Turn Scale (6 seconds)
    st.markdown("### ⚔️ 1. Escala de Combate (Rodadas e Turnos de 6 Segundos)")
    st.info("💡 **Regra D&D 5e**: Cada rodada de combate dura **6 segundos** no mundo de jogo (10 rodadas = 1 minuto). Use para contar a duração de magias de 1 minuto (*Benção*, *Escudo da Fé*, *Padrão Hipnótico*).")
    
    c_cb1, c_cb2, c_cb3 = st.columns(3)
    with c_cb1:
        if st.button("⚔️ +1 Rodada (+6 Segundos)", key="cb_6s"):
            advance_time(0, 0, seconds=6)
            st.rerun()
    with c_cb2:
        if st.button("⚔️ +5 Rodadas (+30 Segundos)", key="cb_30s"):
            advance_time(0, 0, seconds=30)
            st.rerun()
    with c_cb3:
        if st.button("⚔️ +10 Rodadas / 1 Minuto (+60 Segundos)", key="cb_60s"):
            advance_time(0, 1, seconds=0)
            st.rerun()
            
    st.markdown("---")
    
    # 2. Exploration Scale (Dungeons & Places - 10 minutes)
    st.markdown("### 🏰 2. Escala de Exploração (Turnos de Dungeon / 10 Minutos)")
    st.info("💡 **Regra D&D 5e**: A exploração de dungeons e busca por armadilhas é contada em **Turnos de Exploração de 10 minutos**. A cada turno, o Mestre verifica recursos (Tochas duram 60 min / 6 turnos) e rola testes de percepção e encontros em dungeons.")
    
    c_ex1, c_ex2, c_ex3 = st.columns(3)
    with c_ex1:
        if st.button("🗝️ +1 Turno de Exploração (+10 Minutos)", key="ex_10m"):
            advance_time(0, 10)
            st.rerun()
    with c_ex2:
        if st.button("🔦 +3 Turnos de Exploração (+30 Minutos)", key="ex_30m"):
            advance_time(0, 30)
            st.rerun()
    with c_ex3:
        if st.button("🕯️ +6 Turnos / Fim da Tocha (+1 Hora)", key="ex_1h"):
            advance_time(1, 0)
            st.rerun()
            
    st.markdown("---")
    
    # 3. Travel & Rest Scale (Hours & Days)
    st.markdown("### 🗺️ 3. Escala de Viagem & Descanso")
    st.info("💡 **Regra D&D 5e**: **Descanso Curto** = 1 hora (recupera PV com Dados de Vida). **Descanso Longo** = 8 horas (recupera todos os PV, slots de magia e metade dos Dados de Vida).")
    
    c_rs1, c_rs2, c_rs3, c_rs4 = st.columns(4)
    with c_rs1:
        if st.button("⌛ +30 Minutos de Viagem", key="travel_30m_tab2"):
            advance_time(0, 30, is_travel=True)
            st.rerun()
    with c_rs2:
        if st.button("🏕️ Descanso Curto (+1 Hora)", key="short_rest_tab2"):
            advance_time(1, 0)
            st.rerun()
    with c_rs3:
        if st.button("☀️ Descanso Longo (+8 Horas)", key="long_rest_tab2"):
            advance_time(8, 0)
            st.rerun()
    with c_rs4:
        if st.button("🌅 Avançar para o Próximo Dia (+24h)", key="next_day_tab2"):
            advance_time(24, 0)
            st.rerun()
            
    st.markdown("---")
    st.subheader("📊 Relógio de Viagem Acumulada e Alertas de Encontro")
    st.markdown(f"**Minutos de Viagem no Trecho Atual:** `{st.session_state['travel_acc_min']} min / 30 min`")
    st.progress(min(st.session_state["travel_acc_min"] / 30.0, 1.0))
    
    if st.session_state["travel_acc_min"] >= 30:
        st.error("🚨 **ATENÇÃO MESTRE:** 30 minutos de viagem acumulados! É hora de realizar o teste de encontro aleatório (d20)!")
        
    col_rst1, col_rst2 = st.columns(2)
    with col_rst1:
        if st.button("🎲 Rolar Teste de Encontro no d20", key="btn_enc_tab2"):
            st.session_state["travel_acc_min"] = 0
            st.session_state["encounter_alert"] = False
            st.rerun()
    with col_rst2:
        if st.button("🔄 Zerar Contador de Viagem", key="btn_zero_tab2"):
            st.session_state["travel_acc_min"] = 0
            st.session_state["encounter_alert"] = False
            st.success("Contador de minutos zerado!")
            st.rerun()

# ---------------------------------------------------------
# TAB 3: CALENDÁRIO DE BARÓVIA
# ---------------------------------------------------------
with tab3:
    st.subheader("📅 Painel do Calendário Oficial de Baróvia")
    st.caption("Baróvia utiliza um calendário próprio dividido em **12 Luas (meses)** de exatamente **28 Dias cada** (336 dias por ano).")
    
    # Active Date & Time Card
    st.markdown(f"""
    <div style="background-color:#1c1917; border:2px solid #b91c1c; padding:20px; border-radius:8px; margin-bottom:20px;">
        <h3 style="margin-top:0; color:#ef4444;">📜 Estado Atual do Tempo no Vale</h3>
        <p style="font-size:18px;"><b>Ano Baroviano:</b> {st.session_state['cal_year']} AR (Anno Baroviae)</p>
        <p style="font-size:18px;"><b>Mês Atual:</b> {curr_moon['name']} — <i>{curr_moon['title']}</i> ({curr_moon['season']})</p>
        <p style="font-size:18px;"><b>Dia do Mês:</b> Dia {st.session_state['cal_day']} de 28</p>
        <p style="font-size:18px;"><b>Horário Atual:</b> {curr_time_str}</p>
        <p style="font-size:18px;"><b>Fase da Lua:</b> {moon_phase_name}</p>
        <small style="color:#d1d5db;"><i>{moon_phase_desc}</i></small>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Custom Time Addition
    st.subheader("⏳ Avanço de Tempo Personalizado")
    col_custom1, col_custom2, col_custom3 = st.columns([2, 2, 2])
    with col_custom1:
        add_h = st.number_input("Horas a adicionar:", min_value=0, max_value=720, value=0, step=1, key="num_add_h")
    with col_custom2:
        add_m = st.number_input("Minutos a adicionar:", min_value=0, max_value=59, value=30, step=5, key="num_add_m")
    with col_custom3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Aplicar Avanço Personalizado", key="btn_apply_cust"):
            advance_time(int(add_h), int(add_m))
            st.success(f"Avançado {add_h}h {add_m}min no calendário!")
            st.rerun()
            
    st.markdown("---")
    
    # Manual Adjustement Section (For DM Override)
    with st.expander("🛠️ Ajuste Manual de Data/Hora (Apenas Mestre)"):
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            new_year = st.number_input("Ano AR:", min_value=1, max_value=1000, value=st.session_state["cal_year"], key="man_yr")
        with col_m2:
            new_moon_idx = st.selectbox("Mês / Lua:", list(range(12)), format_func=lambda idx: f"{BAROVIAN_MOONS[idx]['name']} ({BAROVIAN_MOONS[idx]['title']})", index=st.session_state["cal_moon_idx"], key="man_moon")
        with col_m3:
            new_day = st.number_input("Dia do Mês (1-28):", min_value=1, max_value=28, value=st.session_state["cal_day"], key="man_day")
        with col_m4:
            new_time = st.time_input("Horário do Dia:", datetime.time(st.session_state["cal_hour"], st.session_state["cal_minute"]), key="man_tm")
            
        if st.button("💾 Definir Data e Hora Manualmente", key="btn_man_set"):
            st.session_state["cal_year"] = int(new_year)
            st.session_state["cal_moon_idx"] = int(new_moon_idx)
            st.session_state["cal_day"] = int(new_day)
            st.session_state["cal_hour"] = new_time.hour
            st.session_state["cal_minute"] = new_time.minute
            st.session_state["cal_second"] = 0
            st.success("Data e hora atualizadas manualmente pelo Mestre!")
            st.rerun()

    st.markdown("---")
    
    # Reference Table for the 12 Moons of Barovia
    st.subheader("🌙 Tabela de Luas (Meses) de Baróvia")
    st.dataframe(
        [
            {
                "Nº": i + 1,
                "Nome": moon["name"],
                "Título Temático": moon["title"],
                "Estação Predominante": moon["season"],
                "Descrição / Características": moon["desc"]
            } for i, moon in enumerate(BAROVIAN_MOONS)
        ],
        use_container_width=True,
        hide_index=True
    )

# ---------------------------------------------------------
# TAB 4: TABELA E GERADOR DE ENCONTROS
# ---------------------------------------------------------
with tab4:
    st.subheader("🎲 Gerador & Tabela de Encontros Aleatórios de Baróvia")
    st.caption("Conforme as regras oficiais do Capítulo 2 de A Maldição de Strahd (D&D 5e)")
    
    # 1. Interactive Generator First
    st.markdown("### 🎲 Gerador Rápido de Encontro na Viagem")
    
    c_g1, c_g2 = st.columns(2)
    with c_g1:
        road_type = st.radio("Tipo de Local da Viagem:", ["Estrada Principal / Trilha", "Ermos Fechados / Floresta / Pântano"], key="rad_road_t")
    with c_g2:
        st.markdown("**🛡️ Percepção Passiva Atual dos Jogadores:**")
        pass_mod = -5 if "Rápido" in pace else 0
        st.caption(f"Owen: **{11 + pass_mod}** | Taketsu: **{12 + pass_mod}** | Lony: **{11 + pass_mod}** | Kael: **{12 + pass_mod}**" + (" *(Penalidade de -5 aplicada por Ritmo Rápido)*" if pass_mod < 0 else ""))

    if st.button("🎲 Rolar Teste de Encontro (d20)", key="btn_enc_d20"):
        roll = random.randint(1, 20)
        
        # Determine target threshold based on Pace & Location
        if "Rápido" in pace:
            target = 13 if "Estrada" in road_type else 10
            chance_lbl = "Alta (Ritmo Rápido)"
        elif "Normal" in pace:
            target = 15 if "Estrada" in road_type else 12
            chance_lbl = "Média-Alta (Ritmo Normal)"
        else:
            target = 17 if "Estrada" in road_type else 14
            chance_lbl = "Média-Baixa (Ritmo Lento)"
            
        is_night = (st.session_state["cal_hour"] < 6 or st.session_state["cal_hour"] >= 18)
        table_key = "night" if is_night else "day"
        
        if roll >= target:
            enc_roll = random.randint(1, 12) + random.randint(1, 8)
            matching_text = next((item[1] for item in RANDOM_ENCOUNTERS[table_key] if item[0] == enc_roll), "Inimigos aproximando-se.")
            qty_num, qty_msg = parse_and_roll_dice(matching_text)
            
            # Enemy Stealth Roll vs Party Passive Perception
            enemy_stealth = random.randint(1, 20) + 2
            
            st.error(f"🚨 **ENCONTRO ALEATÓRIO DETECTADO!** (Rolagem no d20: **{roll}** >= CD {target} — Chance {chance_lbl})")
            st.markdown(f"**Resultado da Tabela ({'Noturna' if is_night else 'Diurna'} - Rolagem {enc_roll}):**")
            st.warning(f"🧟 **{matching_text}**")
            st.info(qty_msg)
            
            # Ambush / Surprise Check
            st.markdown("#### 🕵️ Teste de Furtividade dos Inimigos vs. Percepção Passiva do Grupo:")
            st.write(f"Rolagem de Furtividade dos Inimigos: **{enemy_stealth}**")
            
            pcs_passives = [("Owen", 11 + pass_mod), ("Taketsu", 12 + pass_mod), ("Lony", 11 + pass_mod), ("Kael", 12 + pass_mod)]
            for pc_name, pc_pp in pcs_passives:
                if enemy_stealth > pc_pp:
                    st.error(f"🙈 **{pc_name}** (Percepção Passiva {pc_pp}) ➔ **SURPREENDIDO!** (Não pode agir na 1ª rodada)")
                else:
                    st.success(f"👁️ **{pc_name}** (Percepção Passiva {pc_pp}) ➔ **ALERTA!** Percebeu os inimigos a tempo")
        else:
            st.success(f"✅ **Caminho Tranquilo.** (Rolagem no d20: **{roll}** < CD {target} — Chance {chance_lbl}). Nenhum encontro hostil neste trecho.")
            
    st.markdown("---")
    
    # 2. Reference Tables
    st.subheader("📜 Tabelas de Referência Oficial (Capítulo 2 - Curse of Strahd)")
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

# ---------------------------------------------------------
# TAB 5: GESTOR & CALCULADOR DE XP
# ---------------------------------------------------------
with tab5:
    st.subheader("📊 Gestor e Calculador de Experiência (XP)")
    st.caption("Acompanhamento de XP individual e de grupo, evolução de níveis e registro de façanhas em Baróvia.")
    
    # 1. Party Status Cards
    st.markdown("### 🛡️ Status de Experiência dos Jogadores")
    cols = st.columns(4)
    pcs = ["Owen", "Taketsu", "Lony", "Kael"]
    
    for idx, pc in enumerate(pcs):
        xp_val = st.session_state["party_xp"].get(pc, 300)
        lvl, curr_req, next_req, progress, needed = get_level_progress(xp_val)
        
        with cols[idx]:
            st.markdown(f"""
            <div class="party-card">
                <h3 style="margin:0; color:#ef4444;">{pc}</h3>
                <p style="font-size:20px; margin:5px 0;"><b>Nível {lvl}</b></p>
                <p style="font-size:14px; margin:2px 0;"><b>{xp_val:,} XP</b></p>
                <p style="font-size:12px; color:#a1a1aa; margin:2px 0;">Próximo nível ({lvl+1}): {next_req:,} XP</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.progress(progress)
            
            if needed <= 0 and lvl < 11:
                st.success(f"🎉 **LEVEL UP!** Pronto p/ Nível {lvl+1}")
            elif lvl >= 11:
                st.info("🌟 **Nível Máximo Atingido!**")
            else:
                st.caption(f"Faltam **{needed:,} XP** para o Nível {lvl+1}")
                
    st.markdown("---")
    
    # 2. XP Addition Section
    st.subheader("➕ Conceder Experiência (XP)")
    
    xp_type = st.radio(
        "Selecione a Origem da Experiência:",
        ["⚔️ Combate / Inimigos Derrotados", "📜 Marco da História / Descoberta", "🌟 Bônus Individual (Roleplay & Ações Célebres)"],
        horizontal=True,
        key="rad_xp_src"
    )
    
    if "Combate" in xp_type:
        st.markdown("#### ⚔️ Cálculo de XP de Combate")
        
        xp_calc_mode = st.radio(
            "Modo de Distribuição de XP:",
            ["⚖️ Dividir XP do encontro entre os participantes (Regra Oficial D&D 5e)", "🎮 Conceder XP Total do encontro a cada participante (Estilo BG3)"],
            index=0,
            horizontal=False,
            key="rad_xp_mode"
        )
        
        c1, c2, c3 = st.columns([3, 2, 2])
        
        with c1:
            selected_monster = st.selectbox("Selecione o Inimigo:", list(MONSTERS_DB.keys()), key="sb_monster")
            
        if selected_monster == "Outro / Inimigo Personalizado":
            with c2:
                custom_m_name = st.text_input("Nome do Inimigo:", value="Criatura Desconhecida", key="tx_custom_m")
            with c3:
                custom_m_xp = st.number_input("XP por Unidade:", min_value=0, max_value=50000, value=100, step=50, key="num_custom_m_xp")
            m_xp_each = custom_m_xp
            m_label = custom_m_name
        else:
            m_data = MONSTERS_DB[selected_monster]
            m_xp_each = m_data["xp"]
            m_label = f"{selected_monster} (CR {m_data['cr']})"
            with c2:
                st.info(f"**Nível de Desafio (CR):** `{m_data['cr']}`")
            with c3:
                st.info(f"**XP Unitário:** `{m_xp_each} XP`")
                
        c_q1, c_q2 = st.columns([2, 3])
        with c_q1:
            qty = st.number_input("Quantidade de Inimigos:", min_value=1, max_value=100, value=1, step=1, key="num_m_qty")
        with c_q2:
            selected_pcs = st.multiselect("Jogadores Participantes do Combate:", pcs, default=pcs, key="ms_pcs_comb")
            
        total_combat_xp = m_xp_each * qty
        if "BG3" in xp_calc_mode or "Total" in xp_calc_mode:
            xp_per_pc = total_combat_xp
        else:
            xp_per_pc = int(total_combat_xp / len(selected_pcs)) if selected_pcs else 0
        
        st.markdown(f"**Total do Encontro:** `{total_combat_xp:,} XP` | **XP por Jogador ({len(selected_pcs)}):** `{xp_per_pc:,} XP`")
        
        if st.button("⚔️ Conceder XP de Combate", key="btn_grant_comb_xp"):
            if not selected_pcs:
                st.error("Selecione pelo menos um jogador para receber o XP!")
            else:
                for pc in selected_pcs:
                    st.session_state["party_xp"][pc] += xp_per_pc
                    
                log_entry = {
                    "data": f"Dia {st.session_state['cal_day']} - {st.session_state['cal_hour']:02d}:{st.session_state['cal_minute']:02d}",
                    "tipo": "⚔️ Combate",
                    "descricao": f"{qty}x {m_label} ({'Estilo BG3' if 'BG3' in xp_calc_mode else 'Divisão D&D 5e'})",
                    "xp_total": total_combat_xp,
                    "xp_por_pc": xp_per_pc,
                    "participantes": ", ".join(selected_pcs)
                }
                st.session_state["xp_log"].insert(0, log_entry)
                st.success(f"✅ Concedido {xp_per_pc:,} XP para {', '.join(selected_pcs)}!")
                st.rerun()

    elif "Marco" in xp_type:
        st.markdown("#### 📜 XP de Marcos da História e Descobertas")
        c1, c2 = st.columns([3, 2])
        
        with c1:
            selected_milestone = st.selectbox("Selecione o Marco / Conquista:", list(MILESTONES_DB.keys()), key="sb_milestone")
            
        if selected_milestone == "Descoberta de Segredo / Marco Livre":
            with c2:
                custom_ms_name = st.text_input("Descrição da Descoberta:", value="Segredo Revelado", key="tx_cust_ms_desc")
            ms_xp_each = st.number_input("XP por Jogador:", min_value=0, max_value=20000, value=500, step=100, key="num_cust_ms_xp")
            ms_label = custom_ms_name
        else:
            ms_xp_each = MILESTONES_DB[selected_milestone]
            ms_label = selected_milestone
            with c2:
                st.info(f"**XP por Jogador:** `{ms_xp_each} XP`")
                
        selected_pcs = st.multiselect("Jogadores que receberão o Marco:", pcs, default=pcs, key="ms_pcs_ms")
        
        if st.button("📜 Conceder XP de Marco", key="btn_grant_ms_xp"):
            if not selected_pcs:
                st.error("Selecione pelo menos um jogador para receber o XP!")
            else:
                for pc in selected_pcs:
                    st.session_state["party_xp"][pc] += ms_xp_each
                    
                log_entry = {
                    "data": f"Dia {st.session_state['cal_day']} - {st.session_state['cal_hour']:02d}:{st.session_state['cal_minute']:02d}",
                    "tipo": "📜 Marco / Descoberta",
                    "descricao": ms_label,
                    "xp_total": ms_xp_each * len(selected_pcs),
                    "xp_por_pc": ms_xp_each,
                    "participantes": ", ".join(selected_pcs)
                }
                st.session_state["xp_log"].insert(0, log_entry)
                st.success(f"✅ Concedido {ms_xp_each:,} XP de Marco para {', '.join(selected_pcs)}!")
                st.rerun()

    else:
        st.markdown("#### 🌟 Bônus Individual de Interpretação / Ação Notável")
        c1, c2, c3 = st.columns([2, 2, 3])
        
        with c1:
            target_pc = st.selectbox("Jogador:", pcs, key="sb_bonus_pc")
        with c2:
            bonus_xp = st.number_input("XP de Bônus:", min_value=10, max_value=5000, value=100, step=10, key="num_bonus_val")
        with c3:
            bonus_reason = st.text_input("Motivo / Façanha:", value="Excelente interpretação na sessão", key="tx_bonus_rsn")
            
        if st.button("🌟 Conceder Bônus Individual", key="btn_grant_bonus"):
            st.session_state["party_xp"][target_pc] += bonus_xp
            
            log_entry = {
                "data": f"Dia {st.session_state['cal_day']} - {st.session_state['cal_hour']:02d}:{st.session_state['cal_minute']:02d}",
                "tipo": "🌟 Bônus Individual",
                "descricao": f"Bônus para {target_pc}: {bonus_reason}",
                "xp_total": bonus_xp,
                "xp_por_pc": bonus_xp,
                "participantes": target_pc
            }
            st.session_state["xp_log"].insert(0, log_entry)
            st.success(f"✅ Concedido {bonus_xp:,} XP de Bônus para **{target_pc}**!")
            st.rerun()

    st.markdown("---")
    
    # 3. Log & Manual Adjustments
    st.subheader("📜 Histórico de Concessão de XP na Sessão")
    if st.session_state["xp_log"]:
        st.dataframe(
            st.session_state["xp_log"],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nenhum lançamento de XP realizado nesta sessão até o momento.")
        
    with st.expander("🛠️ Ajuste Manual de XP dos Jogadores (Mestre)"):
        m_c1, m_c2, m_c3, m_c4 = st.columns(4)
        with m_c1:
            man_owen = st.number_input("Owen XP:", min_value=0, max_value=200000, value=st.session_state["party_xp"]["Owen"], step=50, key="man_owen_xp")
        with m_c2:
            man_tak = st.number_input("Taketsu XP:", min_value=0, max_value=200000, value=st.session_state["party_xp"]["Taketsu"], step=50, key="man_tak_xp")
        with m_c3:
            man_lony = st.number_input("Lony XP:", min_value=0, max_value=200000, value=st.session_state["party_xp"]["Lony"], step=50, key="man_lony_xp")
        with m_c4:
            man_kael = st.number_input("Kael XP:", min_value=0, max_value=200000, value=st.session_state["party_xp"]["Kael"], step=50, key="man_kael_xp")
            
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("💾 Salvar Ajuste Manual de XP", key="btn_save_man_xp"):
                st.session_state["party_xp"]["Owen"] = man_owen
                st.session_state["party_xp"]["Taketsu"] = man_tak
                st.session_state["party_xp"]["Lony"] = man_lony
                st.session_state["party_xp"]["Kael"] = man_kael
                st.success("Valores de XP atualizados manualmente pelo Mestre!")
                st.rerun()
        with col_btn2:
            if st.button("🗑️ Limpar Histórico de Lançamentos", key="btn_clear_xp_log"):
                st.session_state["xp_log"] = []
                st.success("Histórico da sessão zerado!")
                st.rerun()

# ---------------------------------------------------------
# TAB 6: MARCADORES & VISUALIZADOR DO MAPA
# ---------------------------------------------------------
with tab6:
    st.subheader("📍 Catálogo de Locais de Baróvia (Marcadores A a Z)")
    selected_loc = st.selectbox("Selecione um local para detalhes:", list(LOCATIONS.keys()), format_func=lambda x: LOCATIONS[x]["name"], key="sb_loc_tab6")
    loc_data = LOCATIONS[selected_loc]
    st.markdown(f"### {loc_data['name']}")
    st.markdown(f"**Região Geográfica:** `{loc_data['region']}`")
    st.markdown(f"**Descrição:** {loc_data['desc']}")
    
    st.markdown("---")
    st.dataframe(
        [{"Marcador": k, "Nome": v["name"], "Região": v["region"], "Descrição": v["desc"]} for k, v in LOCATIONS.items()],
        use_container_width=True
    )
