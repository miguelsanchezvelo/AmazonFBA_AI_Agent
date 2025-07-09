import smtplib

print("Probando conexión a smtp.gmail.com:587 (STARTTLS)...")
try:
    server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
    server.starttls()
    print("Conexión a smtp.gmail.com:587 exitosa (STARTTLS)")
    server.quit()
except Exception as e:
    print("Fallo en smtp.gmail.com:587 (STARTTLS):", e)

print("\nProbando conexión a smtp.gmail.com:465 (SSL)...")
try:
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10)
    print("Conexión a smtp.gmail.com:465 exitosa (SSL)")
    server.quit()
except Exception as e:
    print("Fallo en smtp.gmail.com:465 (SSL):", e) 