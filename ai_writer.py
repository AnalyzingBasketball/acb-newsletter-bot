import pandas as pd
import os
import google.generativeai as genai
import sys

# Función para guardar log y salir sin romper el workflow
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

    # 3. PREPARAR DATOS
    top_players = df_week.sort_values('GmSc', ascending=False).head(3)
    top_text = "\n".join([f"- {row['Name']} ({row['Team']}): {row['PTS']}pts, {row['GmSc']} val" for i, row in top_players.iterrows()])
    
    shooters = df_week[(df_week['PTS'] >= 10)].sort_values('TS%', ascending=False).head(1)
    shooter_text = f"{shooters.iloc[0]['Name']} ({shooters.iloc[0]['TS%']}% TS)" if not shooters.empty else "N/A"

    prompt = f"""
    Escribe una newsletter de baloncesto ACB sobre la {ultima_jornada}.
    Destacados:
    {top_text}
    Eficiencia: {shooter_text}
    
    Usa formato Markdown. Título con emojis. Breve y directo.
    """

    # 4. INTENTO DE GENERACIÓN ROBUSTO
    # Primero intentamos con 'gemini-pro' (el estándar más compatible)
    nombre_modelo = 'gemini-pro'
    
    try:
        print(f"Intentando usar modelo: {nombre_modelo}...")
        model = genai.GenerativeModel(nombre_modelo)
        response = model.generate_content(prompt)
        contenido = response.text
        
        # ÉXITO
        mensaje_final = f"{contenido}\n\n_(Generado por {nombre_modelo})_"
        guardar_salida(mensaje_final)

    except Exception as e_gen:
        # SI FALLA, LISTAMOS LOS MODELOS DISPONIBLES PARA DIAGNÓSTICO
        print(f"⚠️ Falló {nombre_modelo}. Listando modelos disponibles...")
        
        lista_modelos = []
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    lista_modelos.append(m.name)
        except:
            lista_modelos = ["No se pudo obtener la lista"]

        mensaje_error = (
            f"# ⚠️ Error generando contenido\n\n"
            f"El modelo '{nombre_modelo}' falló: {e_gen}\n\n"
            f"**Modelos disponibles en tu cuenta:**\n"
            f"{chr(10).join(['- ' + m for m in lista_modelos])}"
        )
        guardar_salida(mensaje_error)

except Exception as e:
    guardar_salida(f"❌ Error crítico en el script: {e}")
