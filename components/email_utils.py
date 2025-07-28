import os
import extract_msg
from email import policy
from email.parser import BytesParser
import bleach
import re
from pathlib import Path

def validate_file_path(percorso_file):
    """
    Valida il percorso del file per prevenire accessi non autorizzati.
    - Verifica se il file esiste.
    - Controlla che sia un .msg o .eml.
    - Blocca file troppo grandi (oltre 50MB).
    """
    try:
        path = Path(percorso_file).resolve()  # Converte e risolve percorso assoluto

        if not path.exists():
            raise ValueError(f"File non trovato: {percorso_file}")

        if path.suffix.lower() not in ['.msg', '.eml']:
            raise ValueError(f"Estensione non supportata: {path.suffix}")

        if path.stat().st_size > 50 * 1024 * 1024:
            raise ValueError("File troppo grande (max 50MB)")

        return str(path)

    except Exception as e:
        log_error(f"❌ Validazione file fallita: {e}")
        raise

def estrai_testo_da_file(percorso_file):
    """
    Estrae i dati principali da un file email:
    - body (testo)
    - data
    - mittente
    - oggetto

    Gestisce sia file .msg (Outlook) che .eml (standard MIME).
    Pulisce l'HTML, rimuove i tag, limita la dimensione del body.
    """
    percorso_sicuro = validate_file_path(percorso_file)
    ext = os.path.splitext(percorso_file)[1].lower()

    if ext == '.msg':
        try:
            msg = extract_msg.Message(percorso_file)
            body = msg.body if msg.body else ""

            # Se body vuoto, prova con HTML
            if not body.strip() and hasattr(msg, 'htmlBody') and msg.htmlBody:
                body = bleach.clean(msg.htmlBody, tags=[], strip=True, strip_comments=True)

            # Pulisce comunque anche il body normale
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

            # Limita la dimensione del body a 1MB
            if len(dati["body"]) > 1000000:
                dati["body"] = dati["body"][:1000000]
                log_info("⚠️ Body email troncato per sicurezza")

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
                # Cerca testo semplice
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        try:
                            body = part.get_content(charset='utf-8')
                        except:
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break

                # Se non trovato, cerca HTML
                if body is None:
                    for part in msg.walk():
                        if part.get_content_type() == 'text/html':
                            body = bleach.clean(
                                part.get_payload(decode=True).decode('utf-8', errors='ignore'),
                                tags=[], strip=True, strip_comments=True
                            )
                            break
            else:
                try:
                    body = msg.get_content(charset='utf-8')
                except:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')

            # Pulisce ulteriormente
            if body:
                body = bleach.clean(body, tags=[], strip=True, strip_comments=True)

            dati = {
                "body": body or '',
                "date": msg.get('date', ''),
                "sender": msg.get('from', ''),
                "subject": msg.get('subject', '')
            }

            # Limita la dimensione del body a 1MB
            if len(dati["body"]) > 1000000:
                dati["body"] = dati["body"][:1000000]
                log_info("⚠️ Body email troncato per sicurezza")

            return dati

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
    Filtra il testo dell'email per:
    - Rimuovere disclaimer (es. "confidenziale", "privileged").
    - Eliminare link (http/https).
    - Ignorare righe vuote.
    """
    if not body or not isinstance(body, str):
        return ""

    # Rimuove disclaimer
    body = re.sub(
        r'(?i)(confidenziale|privileged|riservat[ao]|non autorizzat[ao]|this e-mail.*privileged|disclaimer\s*:).*?$',
        '',
        body,
        flags=re.DOTALL
    )

    # Rimuove link e righe vuote
    righe_filtrate = []
    for riga in body.splitlines():
        riga_strip = riga.strip()
        if riga_strip.startswith('http://') or riga_strip.startswith('https://'):
            continue
        if riga_strip:
            righe_filtrate.append(riga)

    return '\n'.join(righe_filtrate).strip()

def process_email(percorso_file, codici_barre=None):
    """
    Processa un file email:
    - Estrae i dati con sicurezza.
    - Pulisce il testo.
    - Costruisce un prompt per il modello AI.
    - Ritorna la risposta (presumibilmente JSON).
    """
    dati_email = estrai_testo_da_file(percorso_file)
    body = dati_email["body"]
    data_mail = dati_email["date"]
    mittente = dati_email["sender"]

    print("Body grezzo:", body)

    # Filtra e pulisce ulteriormente il testo
    body_filtrato = filtra_body_mail(body)
    print("Body filtrato:", body_filtrato)

    # Genera prompt per modello LLM
    prompt = genera_prompt(body_filtrato, data_mail, mittente, codici_barre)
    print("Prompt generato:", prompt)

    # Chiede al modello AI
    response = chiedi_al_modello(prompt)
    print("Risposta JSON:", response)

    return response
