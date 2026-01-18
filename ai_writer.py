import pandas as pd
import os
import google.generativeai as genai
import sys
import re
import numpy as np

# --- CONFIGURACIÓN ---
MODEL_NAME = "gemini-2.5-flash" 

def guardar_salida(mensaje, nombre_archivo="newsletter_borrador.md"):
    print(mensaje)
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(mensaje)
    sys.exit(0)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key: guardar_salida("❌ Error: Falta GEMINI_API_KEY.")

try:
    genai.configure(api_key=api_key)
except Exception as e:
    guardar_salida(f"❌ Error config Gemini: {e}")

FILE_PATH = "BoxScore_ACB_2025_Cumulative.csv"
if not os.path.exists(FILE_PATH): guardar_salida("❌ No hay CSV de datos.")

# --- HERRAMIENTAS DE FORMATO ---
def b(val, decimals=0, is_percent=False):
    """Formatea un número en negrita y maneja decimales/porcentajes."""
    if pd.isna(val) or val == np.inf or val == -np.inf:
        val = 0
    suffix = "%" if is_percent else ""
    if isinstance(val, (int, float)):
        if val % 1 == 0 and decimals == 0:
            return f"**{int(val)}**{suffix}"
        return f"**{val:.{decimals}f}**{suffix}"
    return f"**{val}**{suffix}"

# --- DICCIONARIO DE EQUIPOS ---
TEAM_MAP = {
    'UNI': 'Unicaja', 'SBB': 'Bilbao Basket', 'BUR': 'San Pablo Burgos', 'GIR': 'Bàsquet Girona',
    'TEN': 'La Laguna Tenerife', 'MAN': 'BAXI Manresa', 'LLE': 'Hiopos Lleida', 'BRE': 'Río Breogán',
    'COV': 'Covirán Granada', 'JOV': 'Joventut Badalona', 'RMB': 'Real Madrid', 'GCA': 'Dreamland Gran Canaria',
    'CAZ': 'Casademont Zaragoza', 'BKN': 'Baskonia', 'UCM': 'UCAM Murcia', 'MBA': 'MoraBanc Andorra',
    'VBC': 'Valencia Basket', 'BAR': 'Barça'
}
def get_team_name(abbr, use_full=True):
    return TEAM_MAP.get(abbr, abbr) if use_full else abbr

# --- CARGA Y PROCESAMIENTO ---
df = pd.read_csv(FILE_PATH)
cols_req = ['VAL', 'PTS', 'Reb_T', 'AST', 'Win', 'Game_Poss', 'TO', 'T2_M', 'T2_A', 'T3_M', 'T3_A', 'FT_A']
for col in cols_req:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    else:
        df[col] = 0

# Cálculos Manuales
df['FGA'] = df['T2_A'] + df['T3_A']
df['TS_Calc'] = np.where((df['FGA'] + 0.44 * df['FT_A']) > 0, 
                         df['PTS'] / (2 * (df['FGA'] + 0.44 * df['FT_A'])) * 100, 0)

# Ordenar jornadas
def extraer_numero_jornada(texto):
    match = re.search(r'\d+', str(texto))
    return int(match.group()) if match else 0
jornadas_unicas = sorted(df['Week'].unique(), key=extraer_numero_jornada)
ultima_jornada_label = jornadas_unicas[-1]
df_week = df[df['Week'] == ultima_jornada_label]
print(f"🤖 Procesando {ultima_jornada_label}...")

# --- PREPARACIÓN DE STRINGS (Aquí dejamos la inicial, la IA lo arreglará) ---

# 1. MVP
ganadores = df_week[df_week['Win'] == 1]
pool = ganadores if not ganadores.empty else df_week
mvp = pool.sort_values('VAL', ascending=False).iloc[0]
txt_mvp = f"{mvp['Name']} ({get_team_name(mvp['Team'])}): {b(mvp['VAL'])} VAL, {b(mvp['PTS'])} PTS."

# 2. DESTACADOS
resto = df_week[df_week['PlayerID'] != mvp['PlayerID']]
top_rest = resto.sort_values('VAL', ascending=False).head(3)
txt_rest = ""
for _, row in top_rest.iterrows():
    txt_rest += f"- {row['Name']} ({get_team_name(row['Team'])}): {b(row['VAL'])} VAL.\n"

# 3. EQUIPOS
team_agg = df_week.groupby('Team').agg({'PTS': 'sum', 'Game_Poss': 'mean', 'Reb_T': 'sum', 'AST': 'sum', 'TO': 'sum'}).reset_index()
team_agg['ORTG'] = (team_agg['PTS'] / team_agg['Game_Poss']) * 100
team_agg['AST_Ratio'] = (team_agg['AST'] / team_agg['Game_Poss']) * 100
team_agg['TO_Ratio'] = (team_agg['TO'] / team_agg['Game_Poss']) * 100

best_offense = team_agg.sort_values('ORTG', ascending=False).iloc[0]
best_passing = team_agg.sort_values('AST_Ratio', ascending=False).iloc[0]
most_careful = team_agg.sort_values('TO_Ratio', ascending=True).iloc[0]

txt_teams = f"""
- Mejor Ataque: {get_team_name(best_offense['Team'])} ({b(best_offense['ORTG'], 1)} pts/100).
- Fluidez: {get_team_name(best_passing['Team'])} ({b(best_passing['AST_Ratio'], 1)} ast/100).
- Control: {get_team_name(most_careful['Team'])} ({b(most_careful['TO_Ratio'], 1)} to/100).
"""

# 4. CONTEXTO
lider_ts = df_week[df_week['PTS'] >= 10].sort_values('TS_Calc', ascending=False).iloc[0]
lider_reb = df_week.sort_values('Reb_T', ascending=False).iloc[0]
txt_context = f"""
- Francotirador (TS%): {lider_ts['Name']} ({b(lider_ts['TS_Calc'], 1, True)}).
- Reboteador: {lider_reb['Name']} ({b(lider_reb['Reb_T'])}).
- Ritmo (Pace): {get_team_name(best_offense['Team'])} ({b(best_offense['Game_Poss'], 1)}).
"""

# 5. TENDENCIAS
txt_trends = ""
if len(jornadas_unicas) >= 1:
    last_3 = jornadas_unicas[-3:]
    df_last = df[df['Week'].isin(last_3)]
    cols_mean = ['VAL', 'PTS', 'TS_Calc']
    means = df_last.groupby(['Name', 'Team'])[cols_mean].mean().reset_index()
    hot = means.sort_values('VAL', ascending=False).head(5)
    for _, row in hot.iterrows():
        # Pasamos la inicial, la IA lo expandirá
        txt_trends += f"- {row['Name']} ({get_team_name(row['Team'], use_full=False)}): {b(row['VAL'], 1)} VAL, {b(row['PTS'], 1)} PTS.\n"

# --- 6. PROMPT CON "ORDEN DE HUMANIZACIÓN DE NOMBRES" ---
prompt = f"""
Actúa como Periodista de Baloncesto ACB. Escribe la crónica de la {ultima_jornada_label}.

DATOS CRUDOS (Atención: Los nombres vienen abreviados, ej: "A. Tomic"):
MVP: {txt_mvp}
DESTACADOS:
{txt_rest}
EQUIPOS:
{txt_teams}
CONTEXTO:
{txt_context}
TENDENCIAS:
{txt_trends}

INSTRUCCIONES OBLIGATORIAS:
1. **EXPANSIÓN DE NOMBRES (CRÍTICO)**: En los datos yo te paso iniciales (ej: "A. Tomic", "F. Campazzo"). **TÚ DEBES ESCRIBIR EL NOMBRE COMPLETO** en el texto basándote en tu conocimiento de la Liga ACB (ej: escribe "Ante Tomic", "Facundo Campazzo", "Joel Parra").
2. **ESTILO**: Narrativa densa en datos. Usa los números en negrita que te paso.
3. **EQUIPOS**: Nombres completos en la narración, siglas solo en listas.

ESTRUCTURA DEL INFORME:
## 🏀 Informe Semanal ACB: {ultima_jornada_label}

### 👑 El Protagonista
[Analiza al MVP usando su NOMBRE COMPLETO. Menciona sus stats y eficiencia.]

### 🚀 Radar de Rendimiento
[Párrafo sobre los otros destacados y el líder en eficiencia. Usa NOMBRES COMPLETOS.]

### 🧠 Pizarra Táctica
[Analiza a los mejores equipos (Ataque, Control, Ritmo).]

### 🔥 Tendencias (Últimas 3 jornadas)
[Lista de jugadores. AQUÍ TAMBIÉN INTENTA USAR EL NOMBRE COMPLETO si es posible, manteniendo el formato lista.]
{txt_trends}
"""

# --- 7. GENERACIÓN ---
try:
    print("🚀 Generando crónica con nombres completos...")
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt)
    texto_final = response.text
    texto_final = texto_final.replace(":\n-", ":\n\n-") # Fix listas
    guardar_salida(texto_final)
except Exception as e:
    guardar_salida(f"❌ Error Gemini: {e}")
