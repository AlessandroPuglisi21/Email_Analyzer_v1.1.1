import logging
import os
from datetime import datetime

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, 'log_generale.txt')
ERROR_LOG_FILE = os.path.join(LOG_DIR, 'log_errori.txt')
SECURITY_LOG_FILE = os.path.join(LOG_DIR, 'security_events.log')

logger = logging.getLogger('email_analyzer')
logger.setLevel(logging.INFO)

fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
fh.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

eh = logging.FileHandler(ERROR_LOG_FILE, encoding='utf-8')
eh.setLevel(logging.ERROR)
eh.setFormatter(formatter)
logger.addHandler(eh)

# Logger specifico per eventi di sicurezza
security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)
security_handler = logging.FileHandler(SECURITY_LOG_FILE, encoding='utf-8')
security_handler.setFormatter(logging.Formatter(
    '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
))
security_logger.addHandler(security_handler)

def log_info(msg):
    print(msg)
    logger.info(msg)

def log_error(msg):
    print(msg)
    logger.error(msg)

def log_security_event(event_type, details, severity="MEDIUM", send_notification=True):
    """
    Registra eventi di sicurezza e invia notifiche email se richiesto.
    
    Args:
        event_type: Tipo di evento ("DOS_ATTACK", "SUSPICIOUS_EMAIL", etc.)
        details: Dettagli dell'evento
        severity: Livello di gravità ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        send_notification: Se True, invia anche una notifica email
    """
    import logging
    from datetime import datetime
    
    # Setup del logger di sicurezza se non esiste
    security_logger = logging.getLogger('security')
    if not security_logger.handlers:
        security_handler = logging.FileHandler('logs/security_events.log', encoding='utf-8')
        security_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        security_handler.setFormatter(security_formatter)
        security_logger.addHandler(security_handler)
        security_logger.setLevel(logging.INFO)
    
    # Determina il livello di log
    log_levels = {
        "LOW": logging.INFO,
        "MEDIUM": logging.WARNING,
        "HIGH": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    log_level = log_levels.get(severity, logging.WARNING)
    
    # Messaggio di log
    log_message = f"[{event_type}] {severity} - {details}"
    security_logger.log(log_level, log_message)
    
    # Invia notifica email per eventi HIGH e CRITICAL
    if send_notification and severity in ["HIGH", "CRITICAL"]:
        try:
            from components.notification_utils import send_security_alert
            send_security_alert(event_type, details, severity)
        except Exception as e:
            log_error(f"Errore nell'invio della notifica di sicurezza: {e}")
    
    # Log anche nel log generale per eventi critici
    if severity == "CRITICAL":
        log_error(f"EVENTO CRITICO DI SICUREZZA: {log_message}")
