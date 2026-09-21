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
# Barovian Calendar: 12 Moons (Months) of 28 Days each
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
# Graph stores distance directly in HEXES between connected nodes.
# 1 hex = 1.5 miles.
# Ex: E -> F = 22 hexes = 33.0 miles.
# ---------------------------------------------------------
GRAPH_HEXES = {
    "A": [("B", 16, "road")],
    "B": [("A", 16, "road"), ("C", 10, "road"), ("D", 12, "road")],
    "C": [("B", 10, "road")],
    "D": [("B", 12, "road"), ("E", 12, "road")],
    "E": [("D", 12, "road"), ("F", 22, "road")],
    "F": [("E", 22, "road"), ("G", 14, "road")],
    "G": [("F", 14, "road"), ("H", 10, "road")],
    "H": [("G", 10, "road"), ("I", 10, "road"), ("O", 28, "road")],
    "I": [("H", 10, "road"), ("J", 8, "road")],
    "J": [("I", 8, "road"), ("K", 6, "road")],
    "K": [("J", 6, "road")],
    "O": [("H", 28, "road"), ("N", 22, "road")],
    "N": [("O", 22, "road"), ("L", 8, "road"), ("P", 20, "road")],
    "L": [("N", 8, "road"), ("M", 18, "difficult")],
    "M": [("L", 18, "difficult")],
    "P": [("N", 20, "road"), ("Q", 16, "road"), ("R", 26, "road"), ("U", 32, "difficult")],
    "Q": [("P", 16, "road"), ("V", 12, "road")],
    "R": [("P", 26, "road"), ("S", 10, "road"), ("V", 14, "road"), ("W", 22, "road"), ("T", 28, "road")],
    "S": [("R", 10, "road"), ("Z", 18, "difficult")],
    "Z": [("S", 18, "difficult")],
    "V": [("Q", 12, "road"), ("R", 14, "road")],
    "W": [("R", 22, "road"), ("Y", 26, "difficult")],
    "Y": [("W", 26, "difficult")],
    "U": [("P", 32, "difficult")],
    "T": [("R", 28, "road"), ("X", 45, "mountain")],
    "X": [("T", 45, "mountain")]
}

HEX_TO_MILES = 1.5  # 1 hex = 1.5 miles

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

# TOP CALENDAR QUICK-STATUS BADGE
curr_moon = BAROVIAN_MOONS[st.session_state["cal_moon_idx"]]
moon_phase_name, moon_phase_desc = get_moon_phase(st.session_state["cal_day"])
curr_time_str = f"{st.session_state['cal_hour']:02d}:{st.session_state['cal_minute']:02d}"

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

# ---------------------------------------------------------
# SIDEBAR CONTROLS
# ---------------------------------------------------------
st.sidebar.header("⚙️ Parâmetros de Viagem")

origin_key = st.sidebar.selectbox("Ponto de Origem:", list(LOCATIONS.keys()), format_func=lambda x: LOCATIONS[x]["name"], index=4)  # E - Village of Barovia
dest_key = st.sidebar.selectbox("Ponto de Destino:", list(LOCATIONS.keys()), format_func=lambda x: LOCATIONS[x]["name"], index=5)    # F - Tser Pool

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

st.sidebar.markdown("---")
st.sidebar.header("⏳ Controle Rápido de Tempo")
col_t1, col_t2 = st.sidebar.columns(2)
with col_t1:
    if st.button("➕ 1 Hora"):
        advance_time(1, 0)
        st.rerun()
    if st.button("☀️ Descanso Longo (8h)"):
        advance_time(8, 0)
        st.rerun()
with col_t2:
    if st.button("➕ 4 Horas"):
        advance_time(4, 0)
        st.rerun()
    if st.button("📅 Avançar 1 Dia"):
        advance_time(24, 0)
        st.rerun()

# ---------------------------------------------------------
# MAIN TABS LAYOUT
# ---------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🧭 Calculadora de Rota", 
    "📅 Calendário de Baróvia", 
    "🎲 Tabela de Encontros", 
    "📍 Marcadores (A a Z)", 
    "🗺️ Visualizador do Mapa"
])

# ---------------------------------------------------------
# TAB 1: CALCULADORA DE ROTA
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
            
            # Metrics Overview
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Distância Total", f"{total_miles:.1f} milhas", f"{total_hexes:.0f} hexágonos (1.5 mi/hex)")
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

# ---------------------------------------------------------
# TAB 2: CALENDÁRIO DE BARÓVIA (DEDICATED TAB)
# ---------------------------------------------------------
with tab2:
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
    
    # Time Advance Controls
    st.subheader("⏳ Avançar Tempo na Sessão")
    col_adv1, col_adv2, col_adv3, col_adv4 = st.columns(4)
    with col_adv1:
        if st.button("➕ 1 Hora", key="cal_tab_1h"):
            advance_time(1, 0)
            st.rerun()
    with col_adv2:
        if st.button("➕ 4 Horas", key="cal_tab_4h"):
            advance_time(4, 0)
            st.rerun()
    with col_adv3:
        if st.button("☀️ Descanso Longo (8h)", key="cal_tab_8h"):
            advance_time(8, 0)
            st.rerun()
    with col_adv4:
        if st.button("📅 Avançar 1 Dia", key="cal_tab_1d"):
            advance_time(24, 0)
            st.rerun()
            
    # Custom Time Addition
    st.markdown("#### Customizar Avanço de Tempo")
    col_custom1, col_custom2, col_custom3 = st.columns([2, 2, 2])
    with col_custom1:
        add_h = st.number_input("Horas a adicionar:", min_value=0, max_value=720, value=0, step=1)
    with col_custom2:
        add_m = st.number_input("Minutos a adicionar:", min_value=0, max_value=59, value=30, step=5)
    with col_custom3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Aplicar Avanço Personalizado"):
            advance_time(int(add_h), int(add_m))
            st.success(f"Avançado {add_h}h {add_m}min no calendário!")
            st.rerun()
            
    st.markdown("---")
    
    # Manual Adjustement Section (For DM Override)
    with st.expander("🛠️ Ajuste Manual de Data/Hora (Apenas Mestre)"):
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            new_year = st.number_input("Ano AR:", min_value=1, max_value=1000, value=st.session_state["cal_year"])
        with col_m2:
            new_moon_idx = st.selectbox("Mês / Lua:", list(range(12)), format_func=lambda idx: f"{BAROVIAN_MOONS[idx]['name']} ({BAROVIAN_MOONS[idx]['title']})", index=st.session_state["cal_moon_idx"])
        with col_m3:
            new_day = st.number_input("Dia do Mês (1-28):", min_value=1, max_value=28, value=st.session_state["cal_day"])
        with col_m4:
            new_time = st.time_input("Horário do Dia:", datetime.time(st.session_state["cal_hour"], st.session_state["cal_minute"]))
            
        if st.button("💾 Definir Data e Hora Manualmente"):
            st.session_state["cal_year"] = int(new_year)
            st.session_state["cal_moon_idx"] = int(new_moon_idx)
            st.session_state["cal_day"] = int(new_day)
            st.session_state["cal_hour"] = new_time.hour
            st.session_state["cal_minute"] = new_time.minute
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
    
    st.markdown("---")
    
    # Moon Phase Cycle Guide (28-day structure)
    st.subheader("🌕 Ciclo Lunar de 28 Dias (Fases da Lua)")
    st.markdown("""
    Cada mês em Baróvia segue estritamente a mesma progressão alinhada com as luas:
    
    * **Dia 01**: ⚪ **Lua Cheia (Full Moon)** — Pico de atividade licantrópica. Os lobisomens da alcateia de Kiril saem em caçadas violentas e monstros ganham bônus de agressividade.
    * **Dias 02 a 07**: 🌖 **Lua Minguante Gibosa** — Transição gradativa; iluminação noturna começa a diminuir.
    * **Dia 08**: 🌗 **Quarto Minguante** — Meia lua prateada visível entre as nuvens pesadas.
    * **Dias 09 a 14**: 🌑 **Minguante Final** — Noites cada vez mais escuras.
    * **Dia 15**: 🌑 **Lua Nova (New Moon)** — Escuridão total. Noite sagrada para Baba Lysaga em Berez (que se banha em sangue de bestas para manter sua juventude) e bônus de Furtividade para criaturas das sombras.
    * **Dias 16 a 21**: 🌓 **Quarto Crescente** — O brilho lunar volta gradualmente ao céu.
    * **Dias 22 a 28**: 🌔 **Lua Crescente Gibosa** — Aproximação da próxima noite de Lua Cheia.
    """)

# ---------------------------------------------------------
# TAB 3: TABELA DE ENCONTROS
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# TAB 4: MARCADORES (A A Z)
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# TAB 5: VISUALIZADOR DO MAPA
# ---------------------------------------------------------
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
            st.image(image, caption=f"Mapa de Baróvia ({selected_image_path}) — Escala: 1 Hexágono = 1.5 milhas", use_container_width=True)
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
