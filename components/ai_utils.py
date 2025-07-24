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

def genera_prompt(testo_email, data_mail, mittente, codici_barre=None):
    codici_str = "\n".join([f"- {desc}: {codice}" for desc, codice in codici_barre.items()]) if codici_barre else "- Nessun codice a barre disponibile"
    prompt = f"""
Analizza la seguente email e restituisci i dati richiesti in formato JSON.

IMPORTANTE: La risposta DEVE essere un array JSON di oggetti, dove ogni oggetto ha questa struttura:
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

ISTRUZIONI FONDAMENTALI PER IL CAMPO "codice_barre":
1. PRIMA DI TUTTO, cerca nella mail un codice a barre esplicito, cioè una sequenza di 13 cifre consecutive (es: 1234567890123). Il codice a barre può essere presentato in vari modi, ad esempio:
   - Prodotto: NOME ARTICOLO - 1234567890123
   - Codice a barre: 1234567890123
   - Prodotto: 1234567890123 - NOME ARTICOLO
   - Codice a barre: 1234567890123
2. SE TROVI UN CODICE A BARRE DI 13 CIFRE NELLA MAIL, DEVI USARE SOLO QUELLO. NON DEVI MAI, IN NESSUN CASO, UTILIZZARE LA TABELLA DI CORRISPONDENZA O CERCARE ALTRI CODICI A BARRE IN BASE AL NOME O DESCRIZIONE.
3. SOLO ED ESCLUSIVAMENTE SE NON TROVI NESSUN CODICE A BARRE DI 13 CIFRE NELLA MAIL, allora puoi cercare nella tabella di corrispondenza fornita qui sotto, confrontando la descrizione/nome articolo:
{codici_str}
   - Se trovi una corrispondenza esatta, usa il relativo codice a barre.
   - Se non c’è una corrispondenza esatta, usa il codice della descrizione più simile.
   - Se non trovi alcuna corrispondenza attendibile, inserisci "NULL".
4. Ricorda: se hai trovato un codice a barre esplicito nella mail, IGNORA COMPLETAMENTE la tabella di corrispondenza e non cercare altri codici a barre.
5. NON aggiungere mai più di un codice a barre per articolo. Ogni articolo deve avere al massimo un solo codice a barre.
6. NON inventare codici a barre: se non trovi nulla, inserisci "NULL".

ESEMPI:
- Caso 1: La mail contiene "Codice a barre: 1234567890123" → Usa solo questo codice, ignora la tabella.
- Caso 2: La mail NON contiene nessun codice a barre di 13 cifre → Cerca nella tabella in base al nome articolo.
- Caso 3: La mail contiene sia un codice a barre di 13 cifre che una descrizione presente in tabella → Usa solo il codice trovato nella mail, ignora la tabella.

IMPORTANTE: NON AGGIUNGERE TESTO, COMMENTI O SPIEGAZIONI PRIMA O DOPO IL JSON.

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
