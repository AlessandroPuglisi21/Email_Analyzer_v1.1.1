import re
from components.config import USA_LLM, GEMINI_API_KEY, OPENAI_API_KEY, COPILOTE_API_KEY, COPILOTE_ENDPOINT, COPILOTE_DEPLOYMENT_NAME
from components.logging_utils import log_error
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

def genera_prompt(testo_email, data_mail, mittente, codici_barre=None):
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

**IMPORTANTE:** La risposta DEVE essere un array JSON di oggetti, dove ogni oggetto ha questa struttura:
{{
    "data_mail": "data della mail in formato dd/MM/YYYY",
    "numero_ordine": "numero dell'ordine o numero prenotazione o numero richiesta", 
    "nome": "nome del cliente",
    "cognome": "cognome del cliente",
    "codice_fiscale": "codice fiscale",
    "telefono": "numero di telefono",
    "articolo": "nome dell'articolo o SK o prestazione",
    "prezzo": "prezzo unitario",
    "quantita": "quantità",
    "email": "email del cliente",
    "mittente": "mittente della mail",
    "codice_barre": "codice a barre dell'articolo"
}}

**IMPORTANTE SULL'ESTRAZIONE DI NOME E COGNOME:**
- Il campo "nome" deve contenere solo il nome di battesimo (es: "Mario")
- Il campo "cognome" deve contenere solo il cognome (es: "Rossi")
- NON invertire mai nome e cognome.
- Esempio corretto: "nome": "Mario", "cognome": "Rossi"
- Esempio SBAGLIATO: "nome": "Rossi", "cognome": "Mario"

**IMPORTANTE SULL'ESTRAZIONE DEL NOME ARTICOLO:**
- Se nell'email è presente una tabella con le colonne "Oggetto" e "SKU", il campo "articolo" deve essere valorizzato **sempre** con il valore della colonna "SKU" e **non** con quello della colonna "Oggetto".
- Se la colonna "SKU" non è presente, estrai il nome articolo come normalmente faresti (ad esempio dal testo o da altre colonne).
- Se il nome dell'articolo inizia con un codice tra parentesi tonde (ad esempio: (IDA 143009)), IGNORA questo codice e imposta il campo articolo solo con il testo che segue, senza parentesi e senza il codice. Esempio: per "(IDA 143009) A tavola da Eataly - Un esclusivo menu di 3 portate" il campo articolo deve essere "A tavola da Eataly - Un esclusivo menu di 3 portate".

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

def chiedi_al_modello(prompt):
    if USA_LLM == "Gemini":
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={"temperature": 0.1}
        )
        response = model.generate_content(prompt)
        return response.text
    elif USA_LLM == "OpenAI":
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        return response.choices[0].message.content
    elif USA_LLM == "Copilote":
        response = copilote_client.chat.completions.create(
            model=COPILOTE_DEPLOYMENT_NAME,
            messages=[{"role": "system", "content": "Sei un assistente utile."}, {"role": "user", "content": prompt}],
            temperature=0.1
        )
        return response.choices[0].message.content
    else:
        log_error(f"❌ Valore USA_LLM non valido: {USA_LLM}. Scegli tra 'Gemini', 'OpenAI', 'Copilote'.")
        return ""