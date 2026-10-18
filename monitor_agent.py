import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types


# Citim datele sensibile din variabilele de mediu furnizate de GitHub
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_PASS = os.environ.get("GMAIL_PASS")

# Inițializare client Gemini


# ==========================================
# 1. CONFIGURARE & UNELTE (TOOLS)
# ==========================================

# A. Unealta pentru descărcat și curățat textul dintr-o pagină web
def fetch_website_text(url: str) -> str:
    """Descarcă o pagină web și returnează doar textul curățat, fără tag-uri HTML."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Eliminăm HTML-ul nefolositor cu BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Eliminăm scripturile și stilurile CSS
        for script in soup(["script", "style", "nav", "footer"]):
            script.extract()
            
        text = soup.get_text(separator=' ', strip=True)
        return text[:4000]  # Returnăm primele 4000 de caractere relevante
    except Exception as e:
        return f"Eroare la accesarea site-ului: {e}"

# B. Unealta pentru trimis e-mail (Folosind Gmail SMTP)
def send_email_alert(subject: str, body: str, recipient_email: str) -> str:
    """Trimite un e-mail de alertă către o adresă specificată."""
    # Configurare Gmail SMTP (Ideal folosește o 'App Password' generată din contul Google)
    sender_email = GMAIL_USER
    sender_password = GMAIL_PASS

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        return "E-mailul a fost trimis cu succes!"
    except Exception as e:
        return f"Eroare la trimiterea e-mailului: {e}"

# ==========================================
# 2. INIȚIALIZARE AGENT AI
# ==========================================

client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# 3. LOGICA DE MONITORIZARE
# ==========================================

def monitor_page(url_target: str, email_destinatar: str, fisier_salvare="last_state.txt"):
    print(f"Agentul verifică site-ul: {url_target}...")
    
    # Pasul A: Descarcă conținutul curent
    current_text = fetch_website_text(url_target)
    
    # Pasul B: Verifică dacă avem o versiune anterioară salvată
    if not os.path.exists(fisier_salvare):
        # Prima rulare: doar salvăm conținutul
        with open(fisier_salvare, "w", encoding="utf-8") as f:
            f.write(current_text)
        print("Prima verificare finalizată. Starea inițială a fost salvată.")
        return

    # Citim conținutul vechi
    with open(fisier_salvare, "r", encoding="utf-8") as f:
        previous_text = f.read()

    # Pasul C: AI-ul analizează dacă există o modificare semnificativă
    prompt = f"""
    Ești un agent de monitorizare. Compară conținutul vechi al unei pagini web cu cel nou.
    
    CONȚINUT VECHI:
    {previous_text}
    
    CONȚINUT NOU:
    {current_text}
    
    Sarcina ta:
    1. Determină dacă există modificări semnificative (ignoră mici schimbări de timestamp, reclame sau erori de formatare).
    2. Dacă EXISTĂ modificări importante, apelează unealta 'send_email_alert' pentru a trimite un e-mail la adresa {email_destinatar}.
       - Subiectul e-mailului trebuie să fie: "Alertă: Modificare detectată pe site!"
       - În corpul e-mailului, explică pe scurt CE s-a schimbat.
    3. Dacă NU există modificări importante, spune doar "Nicio modificare relevantă."
    """

    agent_chat = client.chats.create(
        model="gemini-3.8-flash",
        config=types.GenerateContentConfig(
            tools=[send_email_alert],
            temperature=0.1
        )
    )

    response = agent_chat.send_message(prompt)
    print("Rezultat Agent:", response.text)

    # Actualizăm starea salvată cu noul conținut
    with open(fisier_salvare, "w", encoding="utf-8") as f:
        f.write(current_text)

# ==========================================
# 4. EXECUTARE
# ==========================================
if __name__ == "__main__":
    URL = "https://lupucata.ro"  # Pune URL-ul pe care vrei să îl monitorizezi
    EMAIL = "lupucata@yahoo.com"
    
    monitor_page(URL, EMAIL)
