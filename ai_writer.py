import pandas as pd
import os
import google.generativeai as genai
import sys
import re
import numpy as np

# ==============================================================================
# 1. CONFIGURACIÓN
# ==============================================================================
MODEL_NAME = "gemini-2.5-flash"
FILE_PATH = "data/BoxScore_ACB_2025_Cumulative.csv"

# Diccionario de Equipos
TEAM_MAP = {
    'UNI': 'Unicaja', 'SBB': 'Bilbao Basket', 'BUR': 'San Pablo Burgos', 'GIR': 'Bàsquet Girona',
    'TEN': 'La Laguna Tenerife', 'MAN': 'BAXI Manresa', 'LLE': 'Hiopos Lleida', 'BRE': 'Río Breogán',
    'COV': 'Covirán Granada', 'JOV': 'Joventut Badalona', 'RMB': 'Real Madrid', 'GCA': 'Dreamland Gran Canaria',
    'CAZ': 'Casademont Zaragoza', 'BKN': 'Baskonia', 'UCM': 'UCAM Murcia', 'MBA': 'MoraBanc Andorra',
    'VBC': 'Valencia Basket', 'BAR': 'Barça'
}

# --- RED DE SEGURIDAD (CORRECCIONES VIP) ---
# Se aplica ANTES de la IA para garantizar 100% de acierto en los casos críticos
# que ya sabemos que fallan (Danko/Dusan, Francis/Fernando).
CORRECCIONES_VIP = {
    "F. Alonso": "Francis Alonso",
    "D. Brankovic": "Danko Brankovic",
    "M. Normantas": "Margiris Normantas",
    "A. Best": "Aaron Best",
    "C. Hunt": "Cameron Hunt",
    "T. Forrest": "Trent Forrest",
    "E. Happ": "Ethan Happ",
    "A. Tomic": "Ante Tomic"
}

# ==============================================================================
# 2. FUNCIONES AUXILIARES
# ==============================================================================
def guardar_salida(mensaje, nombre_archivo="newsletter_borrador.md"):
    print(mensaje)
    try:
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            f.write(mensaje)
        print(f"\n✅ Newsletter guardada: {nombre_archivo}")
    except Exception as e:
        print(f"❌ Error guardando archivo: {e}")
    sys.exit(0)

def b(val, decimals=0, is_percent=False):
    if pd.isna(val) or val == np.inf or val == -np.inf: val = 0
    suffix = "%" if is_percent else ""
    if isinstance(val, (int, float)):
        if val % 1 == 0 and decimals == 0: return f"**{int(val)}**{suffix}"
        return f"**{val:.{decimals}f}**{suffix}"
    return f"**{val}**{suffix}"

def get_team_name(abbr, use_full=True):
    return TEAM_MAP.get(abbr, abbr) if use_full else abbr

def extraer_numero_jornada(texto):
    match = re.search(r'\d+', str(texto))
    return int(match.group()) if match else 0

def clean_name(name_raw):
    """Si el nombre está en la lista VIP, lo corrige ya. Si no, lo deja para que la IA lo busque."""
    return CORRECCIONES_VIP.get(name_raw, name_raw)

# ==============================================================================
# 3. CARGA DE DATOS
# ==============================================================================
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key: guardar_salida("❌ Error: Falta GEMINI_API_KEY.")
genai.configure(api_key=api_key)

if not os.path.exists(FILE_PATH): guardar_salida("❌ No hay CSV.")
df = pd.read_csv(FILE_PATH)

cols_num = ['VAL', 'PTS', 'Reb_T', 'AST', 'Win', 'Game_Poss', 'TO', 'TS%', 'USG%']
for col in cols_num:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

jornadas_unicas = sorted(df['Week'].unique(), key=extraer_numero_jornada)
ultima_jornada_label = jornadas_unicas[-1]
df_week = df[df['Week'] == ultima_jornada_label]

print(f"🤖 Analizando {ultima_jornada_label}...")

# ==============================================================================
# 4. PREPARACIÓN DE DATOS (Aplicando Red de Seguridad)
# ==============================================================================
# A. MVP
ganadores = df_week[df_week['Win'] == 1]
pool = ganadores if not ganadores.empty else df_week
mvp = pool.sort_values('VAL', ascending=False).iloc[0]

mvp_name = clean_name(mvp['Name']) # Corrección automática aquí
txt_mvp = (f"{mvp_name} ({get_team_name(mvp['Team'])}): {b(mvp['VAL'])} VAL, "
           f"{b(mvp['PTS'])} PTS, {b(mvp['Reb_T'])} REB.")

# B. DESTACADOS
resto = df_week[df_week['PlayerID'] != mvp['PlayerID']]
top_rest = resto.sort_values('VAL', ascending=False).head(3)
txt_rest = ""
for _, row in top_rest.iterrows():
    r_name = clean_name(row['Name']) # Corrección automática aquí
    txt_rest += f"- {r_name} ({get_team_name(row['Team'])}): {b(row['VAL'])} VAL.\n"

# C. EQUIPOS
team_agg = df_week.groupby('Team').agg({
    'PTS': 'sum', 'Game_Poss': 'mean', 'Reb_T': 'sum', 'AST': 'sum', 'TO': 'sum'
}).reset_index()
team_agg['ORTG'] = (team_agg['PTS'] / team_agg['Game_Poss']) * 100
team_agg['AST_Ratio'] = (team_agg['AST'] / team_agg['Game_Poss']) * 100
team_agg['TO_Ratio'] = (team_agg['TO'] / team_agg['Game_Poss']) * 100

best_offense = team_agg.sort_values('ORTG', ascending=False).iloc[0]
best_passing = team_agg.sort_values('AST_Ratio', ascending=False).iloc[0]
most_careful = team_agg.sort_values('TO_Ratio', ascending=True).iloc[0]

txt_teams = f"""
- Mejor Ataque: {get_team_name(best_offense['Team'])} ({b(best_offense['ORTG'], 1)} pts/100).
- Fluidez: {get_team_name(best_passing['Team'])} ({b(best_passing['AST_Ratio'], 1)} ast/100).
- Control: {get_team_name(most_careful['Team'])} ({b(most_careful['TO_Ratio'], 1)} perdidas/100).
"""

# D. CONTEXTO
lider_ts = df_week[df_week['PTS'] >= 10].sort_values('TS%', ascending=False).iloc[0]
lider_usg = df_week.sort_values('USG%', ascending=False).iloc[0]
ts_name = clean_name(lider_ts['Name'])
usg_name = clean_name(lider_usg['Name'])

txt_context = f"""
- Francotirador (TS%): {ts_name} ({b(lider_ts['TS%'], 1, True)}).
- Dominador (USG%): {usg_name} ({b(lider_usg['USG%'], 1, True)} de uso).
"""

# E. TENDENCIAS
txt_trends = ""
if len(jornadas_unicas) >= 1:
    last_3 = jornadas_unicas[-3:]
    df_last = df[df['Week'].isin(last_3)]
    means = df_last.groupby(['Name', 'Team'])[['VAL', 'PTS', 'TS%']].mean().reset_index()
    hot = means.sort_values('VAL', ascending=False).head(5)
    for _, row in hot.iterrows():
        t_name = clean_name(row['Name']) # Corrección automática aquí
        txt_trends += (f"- {t_name} ({get_team_name(row['Team'], False)}): "
                       f"{b(row['VAL'], 1)} VAL, {b(row['PTS'], 1)} PTS.\n")

# ==============================================================================
# 5. GENERACIÓN IA (CON GOOGLE SEARCH ACTIVADO CORRECTAMENTE)
# ==============================================================================

prompt = f"""
Actúa como Periodista Deportivo ACB (Temporada 2025/2026).

DATOS A PROCESAR (Algunos nombres ya están corregidos, otros abreviados):
MVP: {txt_mvp}
DESTACADOS:
{txt_rest}
EQUIPOS:
{txt_teams}
CONTEXTO:
{txt_context}
TENDENCIAS:
{txt_trends}

INSTRUCCIONES DE VERIFICACIÓN (OBLIGATORIO):
1. **SI EL NOMBRE YA ESTÁ COMPLETO** (ej: "Francis Alonso", "Danko Brankovic"): Úsalo tal cual. NO lo cambies.
2. **SI EL NOMBRE ESTÁ ABREVIADO** (ej: "J. Smith"):
   - USA GOOGLE SEARCH: Busca `"Plantilla [Equipo] ACB 2025-2026"`.
   - Verifica el nombre completo real.
3. **REDACCIÓN**: Escribe una crónica densa en datos y profesional.

ESTRUCTURA:
## 🏀 Informe ACB: {ultima_jornada_label}

### 👑 El MVP
[Nombre completo verificado + Análisis]

### 🚀 Radar de Eficiencia
[Nombres completos verificados + Análisis]

### 🧠 Pizarra Táctica
[Equipos]

### 🔥 Tendencias (Últimas Jornadas)
{txt_trends}
"""

try:
    print("🚀 Generando crónica (Modo Híbrido: Python + Google Search)...")
    
    # --- CORRECCIÓN FINAL: LA CLAVE QUE PIDE TU ERROR ---
    tools_config = [
        {"google_search": {}} 
    ]
    
    model = genai.GenerativeModel(MODEL_NAME, tools=tools_config)
    
    response = model.generate_content(prompt)
    
    texto = response.text
    texto = texto.replace(":\n-", ":\n\n-")
    guardar_salida(texto)

except Exception as e:
    guardar_salida(f"❌ Error Gemini: {e}")
