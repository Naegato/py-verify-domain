import os
import socket
import requests
import datetime
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv  # Import pour charger .env

# Charger les variables depuis le fichier .env
load_dotenv(dotenv_path=".env.local")

# Configuration
DOMAINS = os.getenv("DOMAINS").split(",")  # Liste des domaines
LOG_FILE = "monitoring.log"
MAIL_DELAY_FILE = "last_mail_time.txt"
MAIL_DELAY = 2.5 * 60 * 60  # 2h30 en secondes

# Fonction pour récupérer l'IP publique du serveur
def get_server_ip():
    try:
        response = requests.get("https://api64.ipify.org?format=text")
        response.raise_for_status()
        return response.text.strip()
    except requests.RequestException as e:
        write_log(f"Erreur lors de la récupération de l'IP du serveur : {e}")
        return None

# Fonction pour pinger un domaine
def ping_domain(domain):
    try:
        ip = socket.gethostbyname(domain)
        return ip, "OK"
    except socket.error as e:
        return None, f"Erreur : {e}"

# Fonction pour écrire dans le fichier log
def write_log(message):
    with open(LOG_FILE, "a") as log_file:
        log_file.write(f"{datetime.datetime.now()} - {message}\n")

# Fonction pour envoyer un email
def send_email(subject, body):
    try:
        email_sender = os.getenv("EMAIL_SENDER")
        email_receiver = os.getenv("EMAIL_RECIEVER")
        email_host = os.getenv("EMAIL_HOST")
        email_port = int(os.getenv("EMAIL_PORT"))
        email_user = os.getenv("EMAIL_USER")
        email_pass = os.getenv("EMAIL_PASS")

        write_log(f"Email envoyé : {email_sender} -> {email_receiver}")

        # msg = MIMEText(body)
        # msg["Subject"] = subject
        # msg["From"] = email_sender
        # msg["To"] = email_receiver
        #
        # with smtplib.SMTP_SSL(email_host, email_port) as server:
        #     server.login(email_user, email_pass)
        #     server.sendmail(email_sender, email_receiver, msg.as_string())
        write_log(f"Email envoyé")
    except Exception as e:
        write_log(f"Erreur d'envoi de mail : {e}")

# Fonction pour vérifier si un mail peut être envoyé
def can_send_email():
    try:
        if os.path.exists(MAIL_DELAY_FILE):
            with open(MAIL_DELAY_FILE, "r") as file:
                last_mail_time = float(file.read().strip())
                if (datetime.datetime.now().timestamp() - last_mail_time) < MAIL_DELAY:
                    return False
        return True
    except Exception as e:
        write_log(f"Erreur lors de la vérification du délai d'envoi : {e}")
        return True

# Fonction pour enregistrer l'heure du dernier mail
def update_last_mail_time():
    try:
        with open(MAIL_DELAY_FILE, "w") as file:
            file.write(str(datetime.datetime.now().timestamp()))
    except Exception as e:
        write_log(f"Erreur lors de la mise à jour de l'heure du dernier mail : {e}")

# Fonction principale
def main():
    server_ip = get_server_ip()
    if not server_ip:
        write_log("Impossible de récupérer l'IP du serveur.")
        return

    results = []
    anomalies = []

    # Ping chaque domaine
    for domain in DOMAINS:
        ip, status = ping_domain(domain)
        if ip:
            if ip == server_ip:
                results.append(f"{domain} - OK (IP: {ip})")
                write_log(f"{domain} - OK (IP: {ip})")
            else:
                anomalies.append(f"{domain}: IP serveur ({server_ip}) ≠ IP domaine ({ip})")
                write_log(f"{domain} - IP différente (Serveur: {server_ip}, Domaine: {ip})")
        else:
            anomalies.append(f"{domain}: {status}")
            write_log(f"{domain} - {status}")

    # Envoi d'un mail si anomalies détectées
    if anomalies and can_send_email():
        subject = "Alerte : Anomalies détectées sur les domaines"
        body = "Les anomalies suivantes ont été détectées :\n\n" + "\n".join(anomalies)
        send_email(subject, body)
        write_log(f"Mail envoyé avec les anomalies : {anomalies}")
        update_last_mail_time()
    elif anomalies:
        write_log("Anomalies détectées, mais délai d'envoi non respecté.")
    else:
        write_log("Aucune anomalie détectée.")

# Exécution du script
if __name__ == "__main__":
    main()
