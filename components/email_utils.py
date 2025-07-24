import os
import extract_msg
from email import policy
from email.parser import BytesParser

def estrai_testo_da_file(percorso_file):
    ext = os.path.splitext(percorso_file)[1].lower()
    if ext == '.msg':
        msg = extract_msg.Message(percorso_file)
        dati = {
            "body": msg.body,
            "date": msg.date,
            "sender": msg.sender,
            "subject": getattr(msg, "subject", "")
        }
        # Chiudo esplicitamente il file se il metodo close è disponibile
        if hasattr(msg, 'close'):
            msg.close()
        return dati
    elif ext == '.eml':
        with open(percorso_file, 'rb') as f:
            msg = BytesParser(policy=policy.default).parse(f)
        body = None
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == 'text/plain':
                    body = part.get_content()
                    break
            if body is None:
                for part in msg.walk():
                    ctype = part.get_content_type()
                    if ctype == 'text/html':
                        body = part.get_content()
                        break
        else:
            body = msg.get_content()
        date = msg.get('date', '')
        sender = msg.get('from', '')
        subject = msg.get('subject', '')
        return {
            "body": body or '',
            "date": date,
            "sender": sender,
            "subject": subject
        }
    else:
        raise ValueError(f"Formato file non supportato: {percorso_file}")

def filtra_body_mail(body):
    """
    Rimuove dal testo tutte le righe che:
    - sono solo link (iniziano con http:// o https://)
    - sono righe HTML (iniziano con < o contengono tag <...>)
    """
    if not body or not isinstance(body, str):
        return ""
    righe_filtrate = []
    for riga in body.splitlines():
        riga_strip = riga.strip()
        if riga_strip.startswith('http://') or riga_strip.startswith('https://'):
            continue
        if riga_strip.startswith('<') and riga_strip.endswith('>'):
            continue
        if '<' in riga_strip and '>' in riga_strip:
            continue
        righe_filtrate.append(riga)
    return '\n'.join(righe_filtrate)
