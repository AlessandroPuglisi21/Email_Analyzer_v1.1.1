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


def send_security_alert(alert_type, details, severity="HIGH"):
    """
    Invia una notifica email immediata per eventi di sicurezza critici.
    
    Args:
        alert_type: Tipo di alert ("DOS_ATTACK", "SUSPICIOUS_EMAIL", "PROMPT_INJECTION", etc.)
        details: Dettagli dell'evento di sicurezza
        severity: Livello di gravità ("LOW", "MEDIUM", "HIGH", "CRITICAL")
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
        print(f"⚠️ Impossibile inviare alert di sicurezza: variabili SMTP mancanti: {', '.join(missing)}")
        return False

    # Mapping dei tipi di alert
    alert_messages = {
        "DOS_ATTACK": "🚨 ATTACCO DOS RILEVATO",
        "SUSPICIOUS_EMAIL": "⚠️ EMAIL SOSPETTA RILEVATA",
        "PROMPT_INJECTION": "🔒 TENTATIVO DI PROMPT INJECTION",
        "RATE_LIMIT_EXCEEDED": "📊 LIMITE DI RICHIESTE SUPERATO",
        "INVALID_PATH_ACCESS": "🚫 TENTATIVO DI ACCESSO A PATH NON AUTORIZZATO",
        "SQL_INJECTION_ATTEMPT": "💉 TENTATIVO DI SQL INJECTION"
    }
    
    # Emoji per severità
    severity_icons = {
        "LOW": "🟡",
        "MEDIUM": "🟠", 
        "HIGH": "🔴",
        "CRITICAL": "💀"
    }
    
    alert_title = alert_messages.get(alert_type, f"⚠️ EVENTO DI SICUREZZA: {alert_type}")
    severity_icon = severity_icons.get(severity, "⚠️")
    
    recipients = [email.strip() for email in NOTIFY_EMAIL_TO.replace(';', ',').split(',') if email.strip()]
    msg = MIMEMultipart('alternative')
    msg['From'] = str(Header(NOTIFY_EMAIL_FROM, 'utf-8'))
    msg['To'] = str(Header(", ".join(recipients), 'utf-8'))
    msg['Subject'] = str(Header(f"[SECURITY ALERT] {severity_icon} {alert_title}", 'utf-8'))
    
    # Timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    body = f"""
🔐 === ALERT DI SICUREZZA EMAIL ANALYZER ===

{severity_icon} LIVELLO: {severity}
📅 TIMESTAMP: {timestamp}
🎯 TIPO EVENTO: {alert_type}

📋 DETTAGLI:
{details}

🔍 AZIONI CONSIGLIATE:
"""
    
    # Azioni specifiche per tipo di alert
    if alert_type == "DOS_ATTACK":
        body += """- Verificare i log per identificare l'origine dell'attacco
- Considerare l'implementazione di rate limiting più stringente
- Monitorare le risorse del sistema
"""
    elif alert_type == "SUSPICIOUS_EMAIL":
        body += """- Verificare manualmente il contenuto dell'email
- Controllare se l'email contiene pattern di phishing
- Aggiornare i filtri di sicurezza se necessario
"""
    elif alert_type == "PROMPT_INJECTION":
        body += """- Verificare immediatamente il contenuto dell'email
- Controllare se sono stati estratti dati errati
- Aggiornare i filtri di sanitizzazione
"""
    
    body += """

⚡ Questo è un alert automatico del sistema Email Analyzer.
🔒 Per la sicurezza, verificare sempre manualmente gli eventi critici.

--- 
Email Analyzer Security System
"""
    
    # Sanitizza il corpo
    safe_body = body.replace('\r', '').replace('\0', '')
    msg.attach(MIMEText(safe_body, 'plain', 'utf-8'))
    
    try:
        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(NOTIFY_EMAIL_FROM, recipients, msg.as_string())
        print(f"✅ Alert di sicurezza inviato: {alert_type} ({severity})")
        return True
    except Exception as e:
        print(f"❌ Errore nell'invio dell'alert di sicurezza: {e}")
        return False


def send_dos_attack_alert(source_info, request_count, time_window):
    """
    Notifica specifica per attacchi DoS rilevati.
    """
    details = f"""
🎯 SORGENTE: {source_info}
📊 RICHIESTE: {request_count} richieste in {time_window} secondi
⏰ SOGLIA SUPERATA: Sistema di rate limiting attivato

🔍 DETTAGLI TECNICI:
- Il sistema ha rilevato un numero anomalo di richieste
- Le richieste eccedenti sono state bloccate automaticamente
- Monitorare i log per ulteriori dettagli
"""
    
    return send_security_alert("DOS_ATTACK", details, "HIGH")


def send_suspicious_email_alert(file_path, suspicious_patterns, risk_level):
    """
    Notifica specifica per email sospette.
    """
    details = f"""
📁 FILE: {file_path}
🔍 PATTERN SOSPETTI RILEVATI:
{chr(10).join([f'  • {pattern}' for pattern in suspicious_patterns])}

⚠️ LIVELLO DI RISCHIO: {risk_level}

🔒 AZIONI AUTOMATICHE ESEGUITE:
- Contenuto sanitizzato prima dell'elaborazione
- Pattern pericolosi rimossi dal prompt
- Evento registrato nei log di sicurezza
"""
    
    severity = "CRITICAL" if risk_level == "HIGH" else "HIGH" if risk_level == "MEDIUM" else "MEDIUM"
    return send_security_alert("SUSPICIOUS_EMAIL", details, severity)