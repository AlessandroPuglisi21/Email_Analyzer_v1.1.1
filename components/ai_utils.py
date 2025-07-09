from components.config import USA_LLM, GEMINI_API_KEY, OPENAI_API_KEY, COPILOTE_API_KEY, COPILOTE_ENDPOINT, COPILOTE_DEPLOYMENT_NAME
from components.logging_utils import log_error
import google.generativeai as genai
from openai import AzureOpenAI

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

def genera_prompt(testo_email, data_mail, mittente):
    prompt = f"""
Analizza la seguente email e restituisci i dati richiesti in formato JSON.

IMPORTANTE: La risposta DEVE essere un array JSON di oggetti, dove ogni oggetto ha questa struttura:
{{
    "data_mail": "data della mail in formato dd/MM/YYYY",
    "numero_ordine": "numero dell'ordine",
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
- Se il nome dell'articolo inizia con un codice tra parentesi tonde (ad esempio: (IDA 143009)), IGNORA questo codice e imposta il campo "articolo" solo con il testo che segue, senza parentesi e senza il codice. Esempio: per "(IDA 143009) A tavola da Eataly - Un esclusivo menu di 3 portate" il campo articolo deve essere "A tavola da Eataly - Un esclusivo menu di 3 portate".
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

IMPORTANTE SUL CODICE A BARRE:
- Se il campo "codice_barre" è gia stato trovato fermati qui altrimenti:
- Il codice a barre è un numero di 13 cifre.
- Se non lo trovi, usa "NULL".
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
