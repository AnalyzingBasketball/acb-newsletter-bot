import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import os
import markdown
import sys
import pandas as pd
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# --- 1. CONFIGURACIÓN ---
gmail_user = os.environ.get("GMAIL_USER")
gmail_password = os.environ.get("GMAIL_PASSWORD")
url_suscriptores = os.environ.get("URL_SUSCRIPTORES")
webhook_make = os.environ.get("MAKE_WEBHOOK_URL")

# ⚠️ PEGA AQUÍ EL ENLACE DE TU LOGO EN GITHUB (El que copiaste en el Paso 1)
URL_LOGO = "https://github.com/AnalyzingBasketball/acb-newsletter-bot/blob/main/logo.png?raw=true" 
# Ejemplo: "https://raw.githubusercontent.com/pepito/basket-stats/main/logo.jpg"

if not gmail_user or not gmail_password:
    sys.exit("❌ Error: Faltan credenciales de Gmail.")

# --- 2. LEER INFORME ---
if not os.path.exists("newsletter_borrador.md"):
    sys.exit("❌ No hay informe generado.")

with open("newsletter_borrador.md", "r", encoding="utf-8") as f:
    md_content = f.read()

titulo_redes = md_content.split('\n')[0].replace('#', '').strip()
texto_post = f"🏀 {titulo_redes}\n\n📊 Nuevo análisis disponible. Link en bio.\n\n#ACB #AnalyzingBasketball"

# --- 3. LINKEDIN (MAKE) ---
if webhook_make:
    try:
        requests.post(webhook_make, json={"texto": texto_post})
        print("✅ Señal enviada a Make.")
    except Exception as e:
        print(f"⚠️ Error Make: {e}")

# --- 4. GENERAR IMAGEN INSTAGRAM ---
print("🎨 Generando imagen Instagram...")
nombre_imagen = "post_instagram.jpg"
img = Image.new('RGB', (1080, 1080), color=(15, 15, 15))
draw = ImageDraw.Draw(img)
try:
    font = ImageFont.load_default()
except:
    font = ImageFont.load_default()

draw.text((100, 500), "NUEVO INFORME\nDISPONIBLE", fill=(255, 255, 255), font=font)
img.save(nombre_imagen)

# --- 5. ENVIAR A ADMIN (Pack Instagram) ---
msg_admin = MIMEMultipart()
msg_admin['From'] = gmail_user
msg_admin['To'] = gmail_user
msg_admin['Subject'] = "📸 Pack Instagram Listo"
msg_admin.attach(MIMEText(f"Texto para copiar:\n\n{texto_post}", 'plain'))
with open(nombre_imagen, 'rb') as f:
    msg_admin.attach(MIMEImage(f.read(), name="instagram.jpg"))

server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
server.login(gmail_user, gmail_password)
server.sendmail(gmail_user, gmail_user, msg_admin.as_string())

# --- 6. NEWSLETTER CON LOGO ---
print("📥 Enviando Newsletter con Logo...")
html_content = markdown.markdown(md_content)
link_share = "mailto:?subject=Informe Basket&body=Mira esto: https://analyzingbasketball.wixsite.com/home"

# 👇 AQUÍ ESTÁ EL CAMBIO DEL LOGO 👇
plantilla = f"""
<html><body style='font-family:Arial, sans-serif; background:#f4f4f4; padding:20px; margin:0;'>
<div style='background:#fff; max-width:600px; margin:0 auto; border-radius:8px; overflow:hidden; box-shadow:0 4px 10px rgba(0,0,0,0.1);'>
    
    <div style='background:#000; padding:30px 20px; text-align:center;'>
        <img src="{URL_LOGO}" alt="Analyzing Basketball" style="max-width: 150px; height: auto; display: block; margin: 0 auto;">
        <p style='color:#888; font-size:12px; text-transform:uppercase; letter-spacing:2px; margin-top:10px;'>Data Intelligence</p>
    </div>

    <div style='padding:30px; color:#333; line-height:1.6;'>
        {html_content}
    </div>

    <div style='background:#f9f9f9; padding:20px; text-align:center; border-top:1px solid #eee;'>
        <a href="{link_share}" style='display:inline-block; background:#25d366; color:#fff; padding:10px 20px; text-decoration:none; border-radius:5px; font-weight:bold; margin-bottom:10px;'>⏩ RECOMENDAR A UN AMIGO</a>
        <br>
        <a href='https://analyzingbasketball.wixsite.com/home' style='color:#0056b3; font-size:14px; text-decoration:none;'>Ver gráficos en la web</a>
    </div>

</div>
</body></html>
"""

# Leer suscriptores (Tu código anti-fallos)
lista_emails = []
if url_suscriptores:
    try:
        df = pd.read_csv(url_suscriptores, on_bad_lines='skip', engine='python')
        col = next((c for c in df.columns if "@" in str(df[c].iloc[0])), None)
        if col: lista_emails = df[col].dropna().unique().tolist()
    except: pass

if gmail_user not in lista_emails: lista_emails.append(gmail_user)

for email in lista_emails:
    msg = MIMEMultipart()
    msg['From'] = f"Analyzing Basketball <{gmail_user}>"
    msg['To'] = email.strip()
    msg['Subject'] = f"🏀 Informe: {titulo_redes}"
    msg.attach(MIMEText(plantilla, 'html'))
    server.sendmail(gmail_user, email.strip(), msg.as_string())

server.quit()
print("✅ TODO COMPLETADO.")
