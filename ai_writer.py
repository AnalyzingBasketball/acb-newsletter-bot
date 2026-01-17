import pandas as pd
import os
import google.generativeai as genai
import sys

# Función para guardar el resultado (o error) y que GitHub no se queje
def guardar_salida(mensaje, nombre_archivo="newsletter_borrador.md"):
    print(mensaje)
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(mensaje)
    sys.exit(0)

# 1. CONFIGURACIÓN
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    guardar_salida("❌ Error: No se encontró la GEMINI_API_KEY.")

try:
    genai.configure(api_key=api_key)
except Exception as e:
    guardar_salida(f"❌ Error configurando librería Gemini: {e}")

FILE_PATH = "data/BoxScore_ACB_2025_Cumulative.csv"

# 2. CARGAR DATOS
if not os.path.exists(FILE_PATH):
    guardar_salida(f"❌ Error: No existe el archivo {FILE_PATH}. Revisa el scraper.")

try:
    df = pd.read_csv(FILE_PATH)
    if 'Week' not in df.columns:
        guardar_salida("❌ El CSV no tiene columna 'Week'.")
        
    ultima_jornada = df['Week'].unique()[-1]
    df_week = df[df['Week'] == ultima_jornada]
    print(f"🤖 Analizando datos de: {ultima_jornada}")

    # 3. PREPARAR DATOS (Texto para la IA)
    top_players = df_week.sort_values('GmSc', ascending=False).head(3)
    # Creamos una lista formateada
    top_text = ""
    for i, row in top_players.iterrows():
        top_text += f"- {row['Name']} ({row['Team']}): {row['PTS']} pts, {row['Reb_T']} reb, {row['AST']} ast. Val: {row['VAL']}.\n"
    
    # Buscamos al tirador eficiente
    shooters = df_week[(df_week['PTS'] >= 10)].sort_values('TS%', ascending=False).head(1)
    shooter_text = f"{shooters.iloc[0]['Name']} ({shooters.iloc[0]['Team']})" if not shooters.empty else "N/A"
    shooter_stat = f"{shooters.iloc[0]['TS%']}% TS" if not shooters.empty else ""

    # 4. EL PROMPT (Instrucciones)
    prompt = f"""
    Actúa como un periodista deportivo experto en baloncesto ACB.
    Escribe una newsletter breve, emocionante y con emojis sobre la {ultima_jornada}.

    DATOS DE LA JORNADA:
    🔥 MVP y Destacados:
    {top_text}

    🎯 Jugador más eficiente (Francotirador):
    {shooter_text} con un {shooter_stat} de True Shooting.

    ESTRUCTURA OBLIGATORIA (Usa Markdown):
    # 🏀 Resumen de la {ultima_jornada}
    
    ### 👑 El MVP de la semana
    [Escribe un párrafo potente sobre el mejor jugador de la lista]

    ### 🚀 Actuaciones destacadas
    [Menciona brevemente a los otros dos jugadores top]

    ### 💎 El dato Moneyball
    [Una frase sobre la eficiencia del tirador mencionado]

    ¡Nos vemos la semana que viene!
    """

    # 5. GENERACIÓN CON GEMINI 2.5 FLASH
    # Usamos el nombre exacto que apareció en tu lista
    nombre_modelo = 'gemini-2.5-flash'
    
    print(f"⚡ Solicitando texto a {nombre_modelo}...")
    model = genai.GenerativeModel(nombre_modelo)
    response = model.generate_content(prompt)
    
    contenido = response.text
    
    # 6. GUARDAR ÉXITO
    guardar_salida(contenido)

except Exception as e:
    guardar_salida(f"❌ Error procesando el script: {e}")
