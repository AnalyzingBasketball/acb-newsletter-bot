import requests
import os
import re
import datetime
import subprocess 
import time
import random
from bs4 import BeautifulSoup

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
TEMPORADA = '2025'
COMPETICION = '1'
HORAS_BUFFER = 0    # En 0 porque ejecutamos una vez al día
LOG_FILE = "data/log.txt"
BUFFER_FILE = "data/buffer_control.txt"

# API Key y Headers
API_KEY = '0dd94928-6f57-4c08-a3bd-b1b2f092976e'
HEADERS_API = {
    'x-apikey': API_KEY,
    'origin': 'https://live.acb.com',
    'referer': 'https://live.acb.com/',
    'user-agent': 'Mozilla/5.0'
}

# ==============================================================================
# ZONA 1: FUNCIONES DE SCRAPING
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
    url = f"https://www.acb.com/resultados-clasificacion/ver/temporada_id/{temp_id}/competicion_id/{comp_id}/jornada_numero/{jornada_id}"
    ids = []
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        for a in soup.find_all('a', href=True):
            href = a['href'].lower()
            
            # 1. Filtramos que sea un enlace de un partido
            if "partido" in href:
                # 2. Buscamos el ID numérico (compatible con formato viejo y nuevo)
                match = re.search(r'(?:/id/|-)(\d+)(?:/|#|$|estadisticas)', href)
                
                if match:
                    try:
                        pid = int(match.group(1))
                        ids.append(pid)
                    except: 
                        pass
        return list(set(ids))
    except Exception as e: 
        print(f"Error extrayendo IDs: {e}")
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
        print(f"⚠️ Solo veo {len(game_ids)} partidos en el listado. Faltan datos o ha cambiado la web. No envío nada.")
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
