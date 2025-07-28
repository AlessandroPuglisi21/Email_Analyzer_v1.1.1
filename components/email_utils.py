import os
import extract_msg
from email import policy
from email.parser import BytesParser
import bleach
import re

def estrai_testo_da_file(percorso_file):
    """
    Estrae i dati (body, data, mittente, oggetto) da un file .msg o .eml.
    Per i file .msg, usa sia il body di testo che HTML, rimuovendo completamente i tag HTML.
    Per i file .eml, gestisce contenuti multipart, dando priorità al testo semplice.
    """
    ext = os.path.splitext(percorso_file)[1].lower()
    if ext == '.msg':
        try:
            msg = extract_msg.Message(percorso_file)
            # Prova a estrarre il body di testo, poi HTML se vuoto
            body = msg.body if msg.body else ""
            if not body.strip() and hasattr(msg, 'htmlBody') and msg.htmlBody:
                # Pulisci il contenuto HTML con bleach
                body = bleach.clean(
                    msg.htmlBody,
                    tags=[],  # Rimuove tutti i tag HTML
                    strip=True,
                    strip_comments=True
                )
            # Pulisci ulteriormente per rimuovere eventuali residui HTML
            if body:
                body = bleach.clean(body, tags=[], strip=True, strip_comments=True)
            dati = {
                "body": body or "",
                "date": msg.date or "",
                "sender": msg.sender or "",
                "subject": getattr(msg, "subject", "")
            }
            if hasattr(msg, 'close'):
                msg.close()
            return dati
        except Exception as e:
            print(f"Errore nell'estrazione del file .msg: {e}")
            return {
                "body": "",
                "date": "",
                "sender": "",
                "subject": ""
            }
    elif ext == '.eml':
        try:
            with open(percorso_file, 'rb') as f:
                msg = BytesParser(policy=policy.default).parse(f)
            body = None
            if msg.is_multipart():
                # Cerca prima il testo semplice
                for part in msg.walk():
                    ctype = part.get_content_type()
                    if ctype == 'text/plain':
                        try:
                            body = part.get_content(charset='utf-8')
                        except:
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                # Se non trovato, cerca HTML
                if body is None:
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        if ctype == 'text/html':
                            body = bleach.clean(
                                part.get_payload(decode=True).decode('utf-8', errors='ignore'),
                                tags=[],  # Rimuove tutti i tag HTML
                                strip=True,
                                strip_comments=True
                            )
                            break
            else:
                try:
                    body = msg.get_content(charset='utf-8')
                except:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            # Pulisci ulteriormente per rimuovere eventuali residui HTML
            if body:
                body = bleach.clean(body, tags=[], strip=True, strip_comments=True)
            date = msg.get('date', '')
            sender = msg.get('from', '')
            subject = msg.get('subject', '')
            return {
                "body": body or '',
                "date": date,
                "sender": sender,
                "subject": subject
            }
        except Exception as e:
            print(f"Errore nell'estrazione del file .eml: {e}")
            return {
                "body": "",
                "date": "",
                "sender": "",
                "subject": ""
            }
    else:
        raise ValueError(f"Formato file non supportato: {percorso_file}")

def filtra_body_mail(body):
    """
    Filtra il body dell'email, rimuovendo:
    - Disclaimer comuni (es. frasi con 'confidenziale', 'privileged', 'non autorizzata').
    - Link (http:// o https://).
    - Linee vuote o inutili.
    Mantiene il contenuto testuale, inclusi mittente e oggetto eventualmente presenti.
    """
    if not body or not isinstance(body, str):
        return ""

    # Rimuovi disclaimer comuni
    body = re.sub(
        r'(?i)(confidenziale|privileged|riservat[ao]|non autorizzat[ao]|this e-mail.*privileged|disclaimer\s*:).*?$',
        '',
        body,
        flags=re.DOTALL
    )

    # Rimuovi righe che sono solo link
    righe_filtrate = []
    for riga in body.splitlines():
        riga_strip = riga.strip()
        if riga_strip.startswith('http://') or riga_strip.startswith('https://'):
            continue
        if riga_strip:  # Ignora righe vuote
            righe_filtrate.append(riga)

    return '\n'.join(righe_filtrate).strip()

def process_email(percorso_file, codici_barre=None):
    """
    Processa un file email e genera il JSON usando il modello LLM.
    """
    # Estrai i dati dall'email
    dati_email = estrai_testo_da_file(percorso_file)
    body = dati_email["body"]
    data_mail = dati_email["date"]  
    mittente = dati_email["sender"]

    # Debug: stampa il body grezzo
    print("Body grezzo:", body)

    # Filtra il body
    body_filtrato = filtra_body_mail(body)
    print("Body filtrato:", body_filtrato)

    # Genera il prompt e chiedi al modello
    prompt = genera_prompt(body_filtrato, data_mail, mittente, codici_barre)
    print("Prompt generato:", prompt)
    response = chiedi_al_modello(prompt)
    print("Risposta JSON:", response)

    return response