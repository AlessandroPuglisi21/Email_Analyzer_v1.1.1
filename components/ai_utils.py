import re
import html
from components.config import USA_LLM, GEMINI_API_KEY, OPENAI_API_KEY, COPILOTE_API_KEY, COPILOTE_ENDPOINT, COPILOTE_DEPLOYMENT_NAME
from components.logging_utils import log_error, log_security_event  # Ora funziona!
import google.generativeai as genai
from openai import AzureOpenAI

# Configurazione del modello LLM
if USA_LLM == "Gemini" and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
elif USA_LLM == "OpenAI" and OPENAI_API_KEY:
    import openai
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
elif USA_LLM == "Copilote" and COPILOTE_API_KEY and COPILOTE_ENDPOINT and COPILOTE_DEPLOYMENT_NAME:
    copilote_client = AzureOpenAI(
        api_key=COPILOTE_API_KEY,
        api_version="2024-12-01-preview",
        azure_endpoint=COPILOTE_ENDPOINT
    )
else:
    log_error(f"❌ Configurazione API non valida per il modello selezionato: {USA_LLM}")
    exit(1)

def sanitize_email_content_basic(content):
    """Sanitizzazione base per prevenire prompt injection"""
    if not content or not isinstance(content, str):
        return ""
    
    # Pattern pericolosi di base
    dangerous_patterns = [
        r'(?i)ignora.*(?:tutto|precedente|sopra|istruzioni)',
        r'(?i)nuove?\s+istruzioni?',
        r'(?i)system\s*:',
        r'(?i)assistant\s*:',
        r'(?i)ignore.*(?:all|previous|above|instructions)',
        r'(?i)new\s+instructions?',
        r'(?i)admin.*password',
        r'(?i)delete.*table',
        r'(?i)drop.*database'
    ]
    
    suspicious_patterns_found = []
    
    # Rimuovi pattern pericolosi
    for pattern in dangerous_patterns:
        if re.search(pattern, content):
            suspicious_patterns_found.append(pattern)
            # CAMBIATO: Ora usa severità HIGH per inviare notifiche email
            log_security_event(
                "PROMPT_INJECTION_ATTEMPT", 
                f"Pattern rilevato: {pattern[:30]}... nel contenuto email", 
                "HIGH"  # Cambiato da WARNING a HIGH
            )
            content = re.sub(pattern, '[RIMOSSO_PER_SICUREZZA]', content, flags=re.IGNORECASE)
    
    # Se sono stati trovati pattern sospetti, invia notifica specifica
    if suspicious_patterns_found:
        from components.notification_utils import send_suspicious_email_alert
        try:
            # Determina il livello di rischio
            risk_level = "HIGH" if len(suspicious_patterns_found) > 2 else "MEDIUM"
            
            # Invia notifica email specifica
            send_suspicious_email_alert(
                "Email in elaborazione",
                suspicious_patterns_found,
                risk_level
            )
        except Exception as e:
            log_security_event("NOTIFICATION_ERROR", f"Errore invio notifica: {e}", "ERROR")
    
    # Limita lunghezza
    if len(content) > 10000:
        content = content[:10000] + "[TRONCATO]"
        log_security_event("CONTENT_TRUNCATED", "Contenuto troncato per sicurezza", "INFO")
    
    return content

# Modifica la funzione esistente
def genera_prompt(testo_email, data_mail, mittente, codici_barre=None):
    # Sanitizza il contenuto email
    testo_email_sicuro = sanitize_email_content_basic(testo_email)
    
    # Log dell'operazione
    log_security_event(
        "PROMPT_GENERATION", 
        f"Mittente: {str(mittente)[:30]}, Lunghezza: {len(testo_email_sicuro)}"
    )
    
    # Estrai codici a barre di 13 cifre dal testo con regex
    barcodes = re.findall(r'\b80\d{11}\b', testo_email)
    if barcodes:
        codice_a_barre = barcodes[0]  # Usa il primo codice trovato
        instruzione_barcode = f"""
**Trovato codice a barre nel testo:** Usa '{codice_a_barre}' come valore per il campo 'codice_barre'. NON consultare la tabella di corrispondenza."""
    else:
        codici_str = "\n".join([f"- {desc}: {codice}" for desc, codice in codici_barre.items()]) if codici_barre else "- Nessun codice a barre disponibile"
        instruzione_barcode = f"""
**Nessun codice a barre trovato nel testo:** Usa la seguente tabella di corrispondenza per trovare il codice a barre corretto per ogni articolo:
{codici_str}
- La corrispondenza può essere approssimativa (non deve essere identica).
- Se non trovi una corrispondenza, imposta il campo 'codice_barre' a 'NULL'."""

    prompt = f"""
Analizza la seguente email e restituisci i dati richiesti in formato JSON.

IMPORTANTE: La risposta DEVE essere un array di UN SOLO oggetto JSON con questa struttura:
{{
    "data_mail": "data della mail in formato dd/MM/YYYY",
    "numero_ordine": "numero dell'ordine o numero prenotazione o numero richiesta", 
    "nome": "nome del cliente",
    "cognome": "cognome del cliente",
    "codice_fiscale": "codice fiscale",
    "telefono": "numero di telefono",
    "articolo": "nome dell'articolo o SKU",
    "prezzo": "prezzo unitario",
    "quantita": "quantità",
    "email": "email del cliente",
    "mittente": "mittente della mail",
    "codice_barre": "codice a barre dell'articolo"
}}

IMPORTANTE SULL'ESTRAZIONE DI NOME E COGNOME:
- Il campo "nome" deve contenere solo il nome di battesimo (es: "Mario")
- Il campo "cognome" deve contenere solo il cognome (es: "Rossi")
- NON invertire mai nome e cognome.
- Esempio corretto: "nome": "Mario", "cognome": "Rossi"
- Esempio SBAGLIATO: "nome": "Rossi", "cognome": "Mario"

IMPORTANTE SULL'ESTRAZIONE DEL NOME ARTICOLO:
- Se nell'email è presente una tabella con le colonne "Oggetto" e "SKU", il campo "articolo" deve essere valorizzato **sempre** con il valore della colonna "SKU" e **non** con quello della colonna "Oggetto".
- Se la colonna "SKU" non è presente, allora estrai il nome articolo come normalmente faresti (ad esempio dal testo o da altre colonne).
- Se il nome dell'articolo inizia con un codice tra parentesi tonde (ad esempio: (IDA 143009)), IGNORA questo codice e imposta il campo articolo solo con il testo che segue, senza parentesi e senza il codice. Esempio: per "(IDA 143009) A tavola da Eataly - Un esclusivo menu di 3 portate" il campo articolo deve essere "A tavola da Eataly - Un esclusivo menu di 3 portate".
Regole:
1. Se un campo non è presente, usa "NULL" come valore, tranne per il campo "prezzo": se non trovi il prezzo imposta 0 (zero).
2. Estrai la quantità così come la trovi. Se non la trovi, imposta 1.
3. Il prezzo è il prezzo totale. Usa la virgola (,) come separatore dei decimali. Se non lo trovi, metti 0.
5. La risposta DEVE essere un array JSON, anche se c'è un solo articolo.
6. Non aggiungere testo, commenti o spiegazioni prima o dopo il JSON.

IMPORTANTE SULLA QUANTITA:
- Se nel testo dell'email è presente la dicitura "Quantità: N" (dove N è un numero maggiore di 0), la quantità deve essere impostata a quel valore N.
- Lascia la quantità così come la trovi nel testo. 
- Il prezzo associato deve essere il prezzo totale. 
- Se non trovi una quantità esplicita, imposta "1" come valore predefinito.
- **CASO SPECIALE**: Se il nome dell'articolo contiene un pattern come "X 2" (es: "KIT PIZZA X 2"), questo fa parte del nome dell'articolo. Non usare questo valore come quantità e il nome articolo deve rimanere "KIT PIZZA X 2". Per la quantità comportati come sempre.
- **NUOVA REGOLA**: Se nel nome dell'articolo o nel testo compaiono espressioni come "Box per 2 persone", "Box per X persone", "Partecipanti: 2", "Partecipanti: X" non usare questo valore X come valore della quantità. Per la quantità comportati come sempre. 

**REGOLE GENERALI:**
1. Se un campo non è presente, usa "NULL" come valore, tranne per il campo "prezzo": se non trovi il prezzo

**IMPORTANTE SUL CODICE A BARRE:**
- Il codice a barre è un numero di **13 cifre**.
- **REGOLA PRIORITARIA:** PRIMA DI TUTTO, cerca nel testo dell'email un numero di 13 cifre
 che rappresenti il codice a barre. Se lo trovi, usa **ESCLUSIVAMENTE** il **primo numero di 13 cifre**
  che appare nel testo come valore del campo "codice_barre". **NON CONSULTARE MAI LA TABELLA** in questo caso.
{instruzione_barcode}

ALTRIMENTI  

**ESEMPI DI COMPORTAMENTO ATTESO:**
1. Email: "Prodotto: Widget A - 1234567890123"  
   Risultato: "codice_barre": "1234567890123" (usa il codice trovato, NON consulta la tabella)
2. Email: "Widget B" e nella tabella c’è "Widget B: 9876543210987"  
   Risultato: "codice_barre": "9876543210987" (nessun codice nel testo, cerca nella tabella)
3. Email: "Widget C" e non c’è corrispondenza nella tabella  
   Risultato: "codice_barre": "NULL" (nessun codice nel testo, nessuna corrispondenza)

**IMPORTANTE: NON AGGIUNGERE TESTO, COMMENTI O SPIEGAZIONI PRIMA O DOPO IL JSON.**

--- INIZIO EMAIL ---
Data: {data_mail}
Mittente: {mittente}
{testo_email}
--- FINE EMAIL ---
"""
    return prompt.strip()

def validate_ai_response(response, original_email_content):
    """Valida la risposta dell'AI per rilevare possibili compromissioni"""
    if not response:
        return False
    
    # Verifica che sia JSON valido
    try:
        import json
        data = json.loads(response)
        
        # Se è un array, prendi il primo elemento
        if isinstance(data, list):
            if len(data) == 0:
                log_security_event("EMPTY_AI_RESPONSE", "Array vuoto nella risposta AI", "ERROR")
                return False
            data = data[0]  # Prendi il primo elemento dell'array
        
        # Se non è un dizionario, è invalido
        if not isinstance(data, dict):
            log_security_event("INVALID_AI_RESPONSE", "Risposta non è un oggetto JSON valido", "ERROR")
            return False
            
    except json.JSONDecodeError as e:
        log_security_event("INVALID_AI_RESPONSE", f"Risposta non è JSON valido: {e}", "ERROR")
        return False
    
    # Verifica solo campi critici per sicurezza (non tutti i campi)
    # Almeno uno di questi deve essere presente per considerare la risposta valida
    critical_fields = ['numero_ordine', 'nome', 'cognome', 'email']
    has_critical_field = any(field in data and data[field] not in [None, '', 'NULL'] for field in critical_fields)
    
    if not has_critical_field:
        log_security_event("NO_CRITICAL_FIELDS", "Nessun campo critico trovato nella risposta", "WARNING")
        # Non bloccare, ma logga come warning
    
    # Verifica valori sospetti (solo per sicurezza)
    suspicious_values = [
        'admin', 'root', 'delete', 'drop', 'truncate', 
        'hacker', 'malicious', 'bypass', 'override',
        'ignore previous', 'new instructions', 'system:'
    ]
    
    suspicious_found = []
    for field, value in data.items():
        if isinstance(value, str) and value:
            for suspicious in suspicious_values:
                if suspicious.lower() in value.lower():
                    suspicious_found.append(f"{field}: {suspicious}")
                    # CAMBIATO: Ora usa severità CRITICAL per inviare notifiche immediate
                    log_security_event(
                        "SUSPICIOUS_AI_OUTPUT", 
                        f"Valore sospetto in {field}: {value[:50]}...", 
                        "CRITICAL"  # Mantiene CRITICAL per valori sospetti nell'output
                    )
    
    # Se trovati valori sospetti, invia notifica e blocca
    if suspicious_found:
        try:
            from components.notification_utils import send_suspicious_email_alert
            send_suspicious_email_alert(
                "Risposta AI compromessa",
                suspicious_found,
                "HIGH"
            )
        except Exception as e:
            log_security_event("NOTIFICATION_ERROR", f"Errore invio notifica: {e}", "ERROR")
        return False
    
    # Verifica che non ci siano istruzioni di sistema nella risposta
    response_lower = response.lower()
    system_patterns = [
        'ignore all previous',
        'new instructions',
        'system:',
        'assistant:',
        'user:'
    ]
    
    system_patterns_found = []
    for pattern in system_patterns:
        if pattern in response_lower:
            system_patterns_found.append(pattern)
            # CAMBIATO: Ora usa severità CRITICAL per inviare notifiche immediate
            log_security_event(
                "SYSTEM_INSTRUCTION_DETECTED", 
                f"Pattern di sistema rilevato: {pattern}", 
                "CRITICAL"  # Mantiene CRITICAL per istruzioni di sistema
            )
    
    # Se trovati pattern di sistema, invia notifica e blocca
    if system_patterns_found:
        try:
            from components.notification_utils import send_suspicious_email_alert
            send_suspicious_email_alert(
                "Risposta AI con istruzioni di sistema",
                system_patterns_found,
                "CRITICAL"
            )
        except Exception as e:
            log_security_event("NOTIFICATION_ERROR", f"Errore invio notifica: {e}", "ERROR")
        return False
    
    return True

def chiedi_al_modello(prompt):
    """Versione sicura della chiamata AI"""
    try:
        # Chiamata AI esistente
        if USA_LLM == "Gemini":
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                generation_config={"temperature": 0.1}
            )
            response = model.generate_content(prompt)
            raw_response = response.text
        elif USA_LLM == "OpenAI":
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000  # Limita output
            )
            raw_response = response.choices[0].message.content
        elif USA_LLM == "Copilote":
            response = copilote_client.chat.completions.create(
                model=COPILOTE_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": "Sei un estrattore di dati. Rispondi SOLO con JSON valido."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000  # Limita output
            )
            raw_response = response.choices[0].message.content
        
        # Log della risposta per debug
        log_security_event(
            "AI_RESPONSE_RECEIVED", 
            f"Lunghezza risposta: {len(raw_response) if raw_response else 0}", 
            "INFO"
        )
        
        # Validazione della risposta (più permissiva)
        if raw_response and validate_ai_response(raw_response, prompt):
            return raw_response
        else:
            log_security_event("AI_RESPONSE_REJECTED", "Risposta AI non valida o sospetta", "ERROR")
            return "{\"errore\": \"Risposta AI non valida\"}"
        
    except Exception as e:
        log_error(f"❌ Errore nella chiamata AI: {e}")
        log_security_event("AI_CALL_ERROR", str(e), "ERROR")
        return "{\"errore\": \"Errore nella chiamata AI\"}"

