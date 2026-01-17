import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import markdown
import sys
import pandas as pd
import requests

# --- 1. TUS ENLACES ---
# Enlace de tu logo en GitHub
URL_LOGO = "https://github.com/AnalyzingBasketball/acb-newsletter-bot/blob/main/logo.png?raw=true" 

# Enlace de tu página de suscripción en Wix
URL_SUSCRIPCION = "https://analyzingbasketball.wixsite.com/home/newsletter"
URL_HOME = "https://analyzingbasketball.wixsite.com/home"

# --- 2. CONFIGURACIÓN ---
gmail_user = os.environ.get("GMAIL_USER")
gmail_password = os.environ.get("GMAIL_PASSWORD")
url_suscriptores = os.environ.get("URL_SUSCRIPTORES")
webhook_make = os.environ.get("MAKE_WEBHOOK_URL")

if not gmail_user or not gmail_password:
    sys.exit("❌ Error: Faltan credenciales de Gmail.")

# --- 3. LEER EL INFORME GENERADO ---
if not os.path.exists("newsletter_borrador.md"):
    sys.exit("❌ No hay informe generado.")

with open("newsletter_borrador.md", "r", encoding="utf-8") as f:
    md_content = f.read()

# Preparamos el título y texto para LinkedIn
titulo_redes = md_content.split('\n')[0].replace('#', '').strip()
texto_linkedin = f"🏀 {titulo_redes}\n\n📊 Nuevo análisis de datos disponible.\nLee el informe completo y suscríbete aquí: {URL_SUSCRIPCION}\n\n#ACB #DataScouting #AnalyzingBasketball"

# --- 4. AUTOMATIZACIÓN LINKEDIN (VÍA MAKE) ---
if webhook_make:
    print("📡 Enviando datos a Make para LinkedIn...")
    try:
        requests.post(webhook_make, json={"texto": texto_linkedin})
        print("✅ Publicado en LinkedIn automáticamente.")
    except Exception as e:
        print(f"⚠️ Error conectando con Make: {e}")

# --- 5. ENVIAR NEWSLETTER A SUSCRIPTORES ---
print("📥 Preparando Newsletter...")
html_content = markdown.markdown(md_content)

plantilla = f"""
<html><body style='font-family: Helvetica, Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px;'>
<div style='background-color: #ffffff; max-width: 600px; margin: 0 auto; border: 1px solid #dddddd;'>
    
    <div style='background-color: #000000; padding: 30px 20px; text-align: center;'>
        <img src="{URL_LOGO}" alt="Analyzing Basketball" style="max-width: 150px; height: auto; display: block; margin: 0 auto;">
    </div>

    <div style='padding: 40px 30px; color: #333333; line-height: 1.6; font-size: 16px;'>
        {html_content}
    </div>

    <div style='background-color: #ffffff; padding: 20px; text-align: center; padding-bottom: 40px;'>
        <a href="{URL_SUSCRIPCION}" style='display: inline-block; background-color: #000000; color: #ffffff; padding: 14px 30px; text-decoration: none; font-weight: bold; font-size: 14px; letter-spacing: 1px;'>RECOMENDAR</a>
    </div>

    <div style='background-color: #f9f9f9; padding: 30px; text-align: center; border-top: 1px solid #eeeeee;'>
        <a href='{URL_HOME}' style='color: #000000; font-weight: bold; text-decoration: none; font-size: 14px; text-transform: uppercase;'>Analyzing Basketball</a>
        <p style='color: #999999; font-size: 11px; margin-top: 10px;'>&copy; 2026 AB</p>
    </div>

</div>
</body></html>
"""

# Obtener lista de emails (con protección anti-errores)
lista_emails = []
if url_suscriptores:
    try:
        # engine='python' y on_bad_lines='skip' evitan que falle si hay comas raras
        df = pd.read_csv(url_suscriptores, on_bad_lines='skip', engine='python')
        
        # Buscamos automáticamente la columna que tiene emails
        col = next((c for c in df.columns if "@" in str(df[c].iloc[0])), None)
        if col:
            lista_emails = df[col].dropna().unique().tolist()
    except Exception as e:
        print(f"⚠️ Nota: No se pudo leer la lista de suscriptores ({e}). Se enviará solo al admin.")

# Aseguramos que tú siempre recibes una copia (así ves cómo ha quedado)
if gmail_user not in lista_emails:
    lista_emails.append(gmail_user)

print(f"📧 Enviando newsletter a {len(lista_emails)} personas...")

# Iniciamos conexión con Gmail una sola vez
try:
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(gmail_user, gmail_password)

    for email in lista_emails:
        try:
            msg = MIMEMultipart()
            msg['From'] = f"Analyzing Basketball <{gmail_user}>"
            msg['To'] = email.strip()
            msg['Subject'] = f"🏀 Informe: {titulo_redes}"
            msg.attach(MIMEText(plantilla, 'html'))
            server.sendmail(gmail_user, email.strip(), msg.as_string())
        except Exception as e:
            print(f"❌ Error enviando a {email}: {e}")
            continue

    server.quit()
    print("✅ TODO COMPLETADO CON ÉXITO.")

except Exception as e:
    sys.exit(f"❌ Error crítico de conexión Gmail: {e}")
