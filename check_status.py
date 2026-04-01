import requests
import os
import re
import datetime
import subprocess 
import time
import random

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
TEMPORADA = '2025'
COMPETICION = '1'
HORAS_BUFFER = 0    # En 0 porque ejecutamos una vez al día
LOG_FILE = "data/log.txt"
BUFFER_FILE = "data/buffer_control.txt"

# API Key y Headers (Ajustados con la información de tu Network tab)
API_KEY = '0dd94928-6f57-4c08-a3bd-b1b2f092976e'
HEADERS_API = {
    'X-APIKEY': API_KEY,
    'Accept': 'application/json',
    'Origin': 'https://www.acb.com',
    'Referer': 'https://www.acb.com/es/liga/calendario',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.4 Safari/605.1.15'
}

# ==============================================================================
# ZONA 1: FUNCIONES DE EXTRACCIÓN Y ESTADO
# ==============================================================================

def get_last_jornada_from_log():
    if not os.path.exists(LOG_FILE):
        return 0
    last_jornada = 0
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                match = re.search(r'Jornada\s*[:#-]?\s*(\d+)', line, re.IGNORECASE)
                if match:
                    num = int(match.group(1))
                    if num > last_jornada:
                        last_jornada = num
    except Exception as e:
        print(f"Error leyendo log: {e}")
        return 0
    return last_jornada

def get_game_ids(temp_id, comp_id, jornada_id):
    # Conectamos directamente a la API interna de la ACB (¡Adiós HTML!)
    url = f"https://api2.acb.com/api/seasondata/Competition/matches?competitionId={comp_id}"
    print(f"🔍 Consultando API ACB para Jornada {jornada_id}...")
    ids = []
    try:
        r = requests.get(url, headers=HEADERS_API, timeout=15)
        print(f"📡 Código de respuesta API: {r.status_code}")
        
        if r.status_code == 200:
            partidos = r.json()
            
            # Recorremos todos los partidos de la temporada
            for partido in partidos:
                # Si el partido coincide con la jornada que buscamos
                if str(partido.get('roundNumber')) == str(jornada_id):
                    game_id = partido.get('id')
                    if game_id:
                        ids.append(game_id)
            
            print(f"🎯 IDs encontrados para Jornada {jornada_id}: {ids}")
            return ids
        else:
            print(f"⚠️ La API devolvió un error inesperado. Contenido: {r.text[:200]}")
            return []

    except Exception as e: 
        print(f"❌ Error conectando con la API: {e}")
        return []

def is_game_finished(game_id):
    url = "https://api2.acb.com/api/matchdata/Result/boxscores"
    try:
        r = requests.get(url, params={'matchId': game_id}, headers=HEADERS_API, timeout=5)
        if r.status_code != 200: return False
        data = r.json()
        if 'teamBoxscores' not in data or len(data['teamBoxscores']) < 2: return False
        return True
    except: return False

# ==============================================================================
# ZONA 2: SECUENCIA DE ENVÍO
# ==============================================================================

def ejecutar_secuencia_completa(jornada):
    print(f"🔄 Iniciando secuencia completa para Jornada {jornada}...")

    # PASO 0: SCRAPER
    NOMBRE_SCRIPT_DATOS = "boxscore_ACB_headless.py"
    print(f"📥 0. Ejecutando {NOMBRE_SCRIPT_DATOS}...")
    try:
        subprocess.run(["python", NOMBRE_SCRIPT_DATOS], check=True, text=True)
        print("✅ Datos actualizados correctamente.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error crítico actualizando datos: {e}")
        return False

    # PASO 1: IA
    print("🤖 1. Ejecutando ai_writer.py...")
    try:
        subprocess.run(["python", "ai_writer.py"], check=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error crítico en ai_writer: {e}")
        return False

    # PASO 2: EMAIL
    print("📧 2. Ejecutando email_sender.py...")
    try:
        subprocess.run(["python", "email_sender.py"], check=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error crítico en email_sender: {e}")
        return False

# ==============================================================================
# MAIN (CON FACTOR HUMANO)
# ==============================================================================

def main():
    last_sent = get_last_jornada_from_log()
    target_jornada = last_sent + 1
    
    print(f"--- INICIO SCRIPT DE CONTROL ---")
    print(f"Revisando Jornada/Semana: {target_jornada}")

    game_ids = get_game_ids(TEMPORADA, COMPETICION, str(target_jornada))
    
    # 1. BLINDAJE: Si hay menos de 8 partidos, no hacemos nada.
    if len(game_ids) < 8:
        print(f"⚠️ Solo veo {len(game_ids)} partidos. Faltan datos o ha cambiado la web. No envío nada.")
        return

    # 2. COMPROBACIÓN: ¿Están todos acabados?
    finished_count = 0
    for gid in game_ids:
        if is_game_finished(gid):
            finished_count += 1
    
    print(f"📊 Estado: {finished_count}/{len(game_ids)} terminados.")

    if finished_count == len(game_ids) and len(game_ids) > 0:
        print("✅ Jornada terminada.")
        
        # --- EL TRUCO DEL FACTOR HUMANO ---
        minutos_espera = random.randint(5, 45)
        print(f"☕ Simulando comportamiento humano... Esperando {minutos_espera} minutos antes de enviar.")
        print("zzz...")
        
        time.sleep(minutos_espera * 60) # Pausa aleatoria
        
        print("⏰ ¡Despierta! Enviando ahora.")
        # ----------------------------------

        exito = ejecutar_secuencia_completa(target_jornada)
        
        if exito:
            fecha_log = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            linea_log = f"{fecha_log} : ✅ Jornada {target_jornada} completada y enviada.\n"
            
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(linea_log)
            
            # Limpieza por si acaso
            if os.path.exists(BUFFER_FILE):
                os.remove(BUFFER_FILE)
            print("🏁 Newsletter enviada con éxito.")

    else:
        print("⚽ Aún se está jugando o faltan datos.")

if __name__ == "__main__":
    main()
