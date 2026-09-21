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
    .calendar-box {
        background-color: #1a1a1e;
        border: 2px solid #7f1d1d;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# CALENDAR CONSTANTS & SESSION STATE (Barovian Calendar)
# ---------------------------------------------------------
# Barovian Calendar: 12 Moons (Months) of 28 Days each
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

# Initialize Calendar State
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
# LOCATIONS DATASET (Markers A to Z)
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# ROAD NETWORK GRAPH
# Note: User requested 1 hex = 1.5 miles.
# Graph stores distance in HEXES between connected nodes.
# Distance in miles = hexes * 1.5 miles.
# ---------------------------------------------------------
GRAPH_HEXES = {
    "A": [("B", 2.0, "road")],           # 3.0 miles = 2 hexes
    "B": [("A", 2.0, "road"), ("C", 1.0, "road"), ("D", 1.33, "road")],
    "C": [("B", 1.0, "road")],
    "D": [("B", 1.33, "road"), ("E", 1.33, "road")],
    "E": [("D", 1.33, "road"), ("F", 2.33, "road")],
    "F": [("E", 2.33, "road"), ("G", 1.33, "road")],
    "G": [("F", 1.33, "road"), ("H", 0.67, "road")],
    "H": [("G", 0.67, "road"), ("I", 1.0, "road"), ("O", 3.0, "road")],
    "I": [("H", 1.0, "road"), ("J", 0.67, "road")],
    "J": [("I", 0.67, "road"), ("K", 0.67, "road")],
    "K": [("J", 0.67, "road")],
    "O": [("H", 3.0, "road"), ("N", 2.0, "road")],
    "N": [("O", 2.0, "road"), ("L", 0.67, "road"), ("P", 1.67, "road")],
    "L": [("N", 0.67, "road"), ("M", 2.0, "difficult")],
    "M": [("L", 2.0, "difficult")],
    "P": [("N", 1.67, "road"), ("Q", 1.33, "road"), ("R", 2.67, "road"), ("U", 4.0, "difficult")],
    "Q": [("P", 1.33, "road"), ("V", 1.0, "road")],
    "R": [("P", 2.67, "road"), ("S", 1.0, "road"), ("V", 1.33, "road"), ("W", 2.33, "road"), ("T", 3.33, "road")],
    "S": [("R", 1.0, "road"), ("Z", 2.0, "difficult")],
    "Z": [("S", 2.0, "difficult")],
    "V": [("Q", 1.0, "road"), ("R", 1.33, "road")],
    "W": [("R", 2.33, "road"), ("Y", 3.0, "difficult")],
    "Y": [("W", 3.0, "difficult")],
    "U": [("P", 4.0, "difficult")],
    "T": [("R", 3.33, "road"), ("X", 5.33, "mountain")],
    "X": [("T", 5.33, "mountain")]
}

HEX_TO_MILES = 1.5  # 1 hex = 1.5 miles (User requested)

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
    
    if "Mountain" in region or region in ["Mount Ghakis", "Krezk Pass", "Amber Temple"]:
        if is_night:
            return "🌨️ **Tempestade de Neve Severa**: Vento uivante congelante, neve intensa e frio extremo (-15°C). Visibilidade quase nula."
        else:
            return "❄️ **Frio Intenso e Vento Geado**: Neve fraca e rajadas de vento das montanhas Balinok. Névoa congelante."
    elif "Svalich" in region or region in ["Svalich Woods", "Svalich Woods West"]:
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
    1: ("Plebeus Barovianos (1d4)", "1d4 camponeses assustados carregando tochas ou tridentes procurando abrigo ou pessoas desaparecidas."),
    2: ("Batedores Barovianos (1d4)", "Caçadores de Baróvia armados com bestas leves procurando por aldeões perdidos."),
    3: ("Cadáver Encontrado", "Vocês encontram os restos mortais de um Baroviano massacrado por lobos ou um antigo aventureiro."),
    4: ("Cavaleiro Esquelético", "Um cavaleiro fantasmagórico e seu cavalo esquelético vagam em busca da saída de Baróvia."),
    5: ("Druida e Galhos Infectados", "Um druida insano adorador de Strahd acompanhado por galhos infectados (Twig Blights)."),
    6: ("Enxame de Corvos", "Centenas de corvos observam o grupo em silêncio. Podem ajudar o grupo se um combate começar."),
    7: ("Enxame de Morcegos", "Morcegos servos de Strahd descem dos céus atacando sem provocação."),
    8: ("Espantalho Assassino", "Um espantalho macabro com garras de lâminas enferrujadas enviado por Baba Lysaga ou pelas bruxas."),
    9: ("Lobos de Baróvia (2d6)", "Uma matilha de lobos famintos sob o comando de Strahd cercando o grupo."),
    10: ("Lobos Atrozes (1d4)", "Lobos gigantescos do tamanho de ursos emergindo da névoa com olhos vermelhos."),
    11: ("Lobisomens em Caça (1d4)", "Licantropos da alcateia de Kiril em forma humana ou lupina espreitando o grupo."),
    12: ("Pacote Escondido", "Um pacote de roupas barovianas ou suprimentos escondido em um tronco oco por um homem-corvo."),
    13: ("Ressurgido da Ordem do Dragão", "Um cavaleiro undead da Ordem do Dragão de Prata vagando em busca de lacaios de Strahd."),
    14: ("Sepultura Violada", "Um antigo túmulo na beira da estrada. Pode conter ossos de soldados ou armas antigas."),
    15: ("Trilha Falsa / Armadilha", "Uma trilha enganosa criada por druidas que leva a um fosso com estacas de madeira afiadas."),
    16: ("Zumbis de Baróvia (2d4)", "Corpos cambaleantes de antigos habitantes de Baróvia atraídos pelo cheiro de vivos."),
    17: ("Zumbis de Strahd (1d4)", "Antigos guardas de Ravenloft mortos-vivos segurando pedaços de farda esfarrapada."),
    18: ("Crias Vampíricas de Strahd (1d4)", "Vampiros servos de Strahd rastejando pelas árvores ou rochas em busca de sangue."),
    19: ("Rufiões Vistani", "Grupo de Vistani leais a Strahd tentando extorquir ou enganar os aventureiros."),
    20: ("Aparecimento / Ilusão de Strahd", "O próprio Conde Strahd von Zarovich aparece pessoalmente ou envia uma projeção para testar o grupo.")
}

def roll_encounter(is_wilderness, is_night):
    """Checks encounter roll based on CoS rules: check every 30m. Road: >=18, Wilderness: >=15."""
    target = 15 if is_wilderness else 18
    if is_night:
        target -= 2  # Night increases chance
        
    d20 = random.randint(1, 20)
    if d20 >= target:
        enc_id = random.randint(1, 20)
        enc_title, enc_desc = RANDOM_ENCOUNTERS[enc_id]
        return True, d20, target, enc_title, enc_desc
    else:
        return False, d20, target, "Nenhum Encontro", "A viagem prossegue sem incidentes hostis imediatos."

# ---------------------------------------------------------
# APP INTERFACE
# ---------------------------------------------------------
st.title("🏰 Mapa Interativo e Calculadora de Viagem — Baróvia")
st.caption("Ferramenta de navegação, calendário dinâmico e simulação de deslocamento para A Maldição de Strahd (D&D 5e)")

# Sidebar - Barovian Calendar Status
st.sidebar.header("📅 Calendário de Baróvia (Ano " + str(st.session_state["cal_year"]) + ")")

current_moon = BAROVIAN_MOONS[st.session_state["cal_moon_idx"]]
moon_phase_title, moon_phase_desc = get_moon_phase(st.session_state["cal_day"])

st.sidebar.markdown(f"""
<div class="calendar-box">
    <h3>{current_moon['name']} ({current_moon['title']})</h3>
    <h4>Dia {st.session_state['cal_day']} de 28 | Estação: {current_moon['season']}</h4>
    <p><b>Horário Atual:</b> {st.session_state['cal_hour']:02d}:{st.session_state['cal_minute']:02d}</p>
    <hr style="border-color:#7f1d1d;">
    <p><b>{moon_phase_title}</b><br><small>{moon_phase_desc}</small></p>
</div>
""", unsafe_allow_html=True)

# Calendar Controls
st.sidebar.subheader("⏳ Ações de Tempo e Descanso")
c_col1, c_col2 = st.sidebar.columns(2)
with c_col1:
    if st.button("➕ 1 Hora"):
        advance_time(1, 0)
        st.rerun()
    if st.button("☀️ Descanso Curto (1h)"):
        advance_time(1, 0)
        st.rerun()
with c_col2:
    if st.button("➕ 8 Horas"):
        advance_time(8, 0)
        st.rerun()
    if st.button("🌙 Descanso Longo (8h)"):
        advance_time(8, 0)
        st.rerun()

if st.sidebar.button("🏕️ Passar 1 Dia Inteiro Explorando / Parado"):
    advance_time(24, 0)
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Parâmetros de Rota")

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

# Tabs Layout
tab1, tab2, tab3, tab4 = st.tabs(["🧭 Calculadora de Rota", "🎲 Tabela de Encontros", "📍 Marcadores (A a Z)", "🗺️ Visualizador do Mapa"])

# CALCULATOR TAB
with tab1:
    if origin_key == dest_key:
        st.warning("⚠️ Selecione um destino diferente da origem para calcular a rota.")
    else:
        hexes_count, path = dijkstra_path(origin_key, dest_key)
        
        if hexes_count == float("inf"):
            st.error("Não foi encontrada uma rota conectada entre estes pontos.")
        else:
            # 1 hex = 1.5 miles (User constraint)
            distance_miles = hexes_count * HEX_TO_MILES
            effective_speed = speed_mph / terrain_mult
            travel_hours = distance_miles / effective_speed
            
            hours_int = int(travel_hours)
            minutes_int = int((travel_hours - hours_int) * 60)
            
            # Start time from calendar state
            start_hour = st.session_state["cal_hour"]
            start_min = st.session_state["cal_minute"]
            
            start_dt = datetime.datetime(st.session_state["cal_year"], st.session_state["cal_moon_idx"] + 1, st.session_state["cal_day"], start_hour, start_min)
            travel_delta = datetime.timedelta(hours=hours_int, minutes=minutes_int)
            arrival_dt = start_dt + travel_delta
            
            phase, phase_desc, hazard_level = get_day_night_status(arrival_dt.hour)
            destination_region = LOCATIONS[dest_key]["region"]
            weather_desc = get_detailed_weather(destination_region, arrival_dt.hour)
            
            # Metrics Overview
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Distância Total", f"{distance_miles:.1f} milhas", f"{hexes_count:.1f} hexágonos (Escala: 1 hex = 1.5 mi)")
            with col2:
                st.metric("Tempo de Viagem", f"{hours_int}h {minutes_int}min")
            with col3:
                st.metric("Horário de Chegada", arrival_dt.strftime("%H:%M"))
            with col4:
                st.metric("Perigo na Chegada", hazard_level)
            
            st.markdown("---")
            
            # Journey Details
            st.subheader("📋 Resumo do Trajeto e Clima")
            c_a, c_b = st.columns(2)
            with c_a:
                st.markdown(f"**Origem:** {LOCATIONS[origin_key]['name']}")
                st.markdown(f"**Destino:** {LOCATIONS[dest_key]['name']}")
                st.markdown(f"**Ritmo & Terreno:** {pace} | {terrain}")
                st.caption(f"ℹ️ {pace_note}")
            with c_b:
                st.markdown(f"**Iluminação na Chegada:** {phase}")
                st.caption(phase_desc)
                st.markdown(f"**Clima Predominante:** {weather_desc}")
            
            # Route Steps
            st.subheader("🛣️ Rota Recomendada")
            path_names = " ➔ ".join([f"**[{node}]** {LOCATIONS[node]['name'].split(' - ')[1]}" for node in path])
            st.info(f"Caminho: {path_names}")
            
            # Advance Time Button for travel
            st.markdown("---")
            st.subheader("⏱️ Atualizar Calendário com esta Viagem")
            st.write(f"Deseja avançar o calendário do jogo em **{hours_int} horas e {minutes_int} minutos** para simular o deslocamento do grupo?")
            if st.button("🚀 Confirmar e Avançar Tempo de Viagem no Calendário"):
                advance_time(hours_int, minutes_int)
                st.success(f"✅ Calendário atualizado! Novo horário: {st.session_state['cal_hour']:02d}:{st.session_state['cal_minute']:02d}, Dia {st.session_state['cal_day']}.")
                st.rerun()

# RANDOM ENCOUNTERS TAB
with tab4:
    pass  # We will populate tab2, tab3, tab4 cleanly below

# ENCOUNTERS TAB
with tab2:
    st.subheader("🎲 Tabela de Encontros Aleatórios das Rotas de Baróvia")
    st.write("Seguindo as regras oficiais de *A Maldição de Strahd*, realiza-se um teste a cada **30 minutos de viagem** (CD 18 na estrada, CD 15 no ermo/terreno difícil).")
    
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        st.markdown("### 🎲 Teste Rápido de Encontro")
        is_wild = st.checkbox("Viajando fora da estrada principal (Terreno Difícil/Ermo)?")
        is_night_time = (st.session_state["cal_hour"] < 6 or st.session_state["cal_hour"] >= 18)
        
        if st.button("🎯 Rolar Teste de Encontro (30 min)"):
            occurred, d20, target, title, desc = roll_encounter(is_wild, is_night_time)
            if occurred:
                st.error(f"🚨 **ENCONTRO ALEATÓRIO DETECTADO!**\n\n**Rolagem d20:** {d20} (Meta: {target})\n\n### ⚔️ {title}\n{desc}")
            else:
                st.success(f"✅ **Caminho Tranquilo.**\n\n**Rolagem d20:** {d20} (Meta: {target})\n\n{desc}")
                
    with col_e2:
        st.markdown("### 📜 Tabela Completa de Encontros Aleatórios (d20)")
        st.dataframe(
            [{"d20": k, "Encontro": v[0], "Descrição": v[1]} for k, v in RANDOM_ENCOUNTERS.items()],
            use_container_width=True,
            height=400
        )

# LOCATIONS CATALOG TAB
with tab3:
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

# MAP VIEWER TAB
with tab4:
    st.subheader("🗺️ Visualização do Mapa de Baróvia")
    
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
            st.image(image, caption=f"Mapa de Baróvia ({selected_image_path}) — Escala Atualizada: 1 Hexágono = 1.5 milhas", use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao abrir a imagem `{selected_image_path}`: {e}")
    else:
        st.warning("⚠️ Nenhuma imagem de mapa foi localizada automaticamente na pasta raiz do projeto.")
        st.markdown("📁 **Arquivos atualmente detectados no repositório:**")
        try:
            curr_files = os.listdir(".")
            st.code("\n".join(curr_files) if curr_files else "Nenhum arquivo encontrado")
        except Exception as ex:
            st.write(f"Não foi possível listar arquivos: {ex}")
