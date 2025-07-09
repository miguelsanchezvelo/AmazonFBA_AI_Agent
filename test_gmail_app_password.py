import smtplib
import os

EMAIL = input("Introduce tu email de Gmail: ").strip()
APP_PASSWORD = input("Introduce tu App Password de 16 caracteres: ").strip()

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
        server.starttls()
        server.login(EMAIL, APP_PASSWORD)
        print("¡Autenticación exitosa! La App Password funciona.")
except Exception as e:
    print("Fallo de autenticación:", e) 