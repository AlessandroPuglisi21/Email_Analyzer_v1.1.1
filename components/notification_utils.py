import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from components.config import SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, NOTIFY_EMAIL_TO, NOTIFY_EMAIL_FROM

def send_error_notification(subject, body):
    msg = MIMEMultipart()
    msg['From'] = NOTIFY_EMAIL_FROM
    msg['To'] = NOTIFY_EMAIL_TO
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(NOTIFY_EMAIL_FROM, NOTIFY_EMAIL_TO, msg.as_string())
    except Exception as e:
        print(f"Errore nell'invio della notifica email: {e}") 