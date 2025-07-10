import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from components.config import SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, NOTIFY_EMAIL_TO, NOTIFY_EMAIL_FROM

def send_error_notification(subject, body):
    # Controllo che tutte le variabili siano definite
    required_vars = {
        'SMTP_SERVER': SMTP_SERVER,
        'SMTP_PORT': SMTP_PORT,
        'SMTP_USER': SMTP_USER,
        'SMTP_PASSWORD': SMTP_PASSWORD,
        'NOTIFY_EMAIL_TO': NOTIFY_EMAIL_TO,
        'NOTIFY_EMAIL_FROM': NOTIFY_EMAIL_FROM,
    }
    missing = [k for k, v in required_vars.items() if not v]
    if missing:
        raise ValueError(f"Devi impostare queste variabili SMTP nel file .env: {', '.join(missing)}")

    recipients = [email.strip() for email in NOTIFY_EMAIL_TO.replace(';', ',').split(',') if email.strip()]
    msg = MIMEMultipart('alternative')
    msg['From'] = str(Header(NOTIFY_EMAIL_FROM, 'utf-8'))
    msg['To'] = str(Header(", ".join(recipients), 'utf-8'))
    msg['Subject'] = str(Header(subject, 'utf-8'))

    # Corpo testuale safe
    safe_body = body.replace('\r', '').replace('\0', '')
    msg.attach(MIMEText(safe_body, 'plain', 'utf-8'))


    try:
        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(NOTIFY_EMAIL_FROM, recipients, msg.as_string())
    except Exception as e:
        print(f"Errore nell'invio della notifica email: {e}")


def send_summary_notification(total, success, failed):
    """
    Invia una mail di riepilogo con il numero di mail totali, quelle elaborate con successo e quelle fallite.
    """
    required_vars = {
        'SMTP_SERVER': SMTP_SERVER,
        'SMTP_PORT': SMTP_PORT,
        'SMTP_USER': SMTP_USER,
        'SMTP_PASSWORD': SMTP_PASSWORD,
        'NOTIFY_EMAIL_TO': NOTIFY_EMAIL_TO,
        'NOTIFY_EMAIL_FROM': NOTIFY_EMAIL_FROM,
    }
    missing = [k for k, v in required_vars.items() if not v]
    if missing:
        raise ValueError(f"Devi impostare queste variabili SMTP nel file .env: {', '.join(missing)}")

    recipients = [email.strip() for email in NOTIFY_EMAIL_TO.replace(';', ',').split(',') if email.strip()]
    msg = MIMEMultipart('alternative')
    msg['From'] = str(Header(NOTIFY_EMAIL_FROM, 'utf-8'))
    msg['To'] = str(Header(", ".join(recipients), 'utf-8'))
    msg['Subject'] = str(Header("RIEPILOGO", 'utf-8'))

    body = (
        "*** RIEPILOGO ELABORAZIONE EMAIL ***\n\n"
        f"Totale email da elaborare: {total}\n"
        f"Email elaborate con successo: {success}\n"
        f"Email con errore: {failed}\n"
        "\n--------------------------------\n"
        "Operazione eseguita automaticamente dal sistema."
    )
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(NOTIFY_EMAIL_FROM, recipients, msg.as_string())
    except Exception as e:
        print(f"Errore nell'invio della notifica riepilogo: {e}") 