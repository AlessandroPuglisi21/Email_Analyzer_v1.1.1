import os
import json
import csv
import time
from datetime import datetime
from components.logging_utils import log_info, log_error
from components.email_utils import estrai_testo_da_file, filtra_body_mail
from components.ai_utils import genera_prompt, chiedi_al_modello
from components.config import INSERISCI_IN_ORACLE, ORACLE_DSN, ORACLE_USER, ORACLE_PASSWORD
from components.oracle_utils import inserisci_dati_oracle

def elabora_file(percorso):
    try:
        log_info("\n" + "="*60)
        log_info(f"Inizio elaborazione file: {os.path.basename(percorso)}")
        dati = estrai_testo_da_file(percorso)
        log_info(f"Lunghezza body originale: {len(dati['body']) if dati['body'] else 0}")
        body_clean = ''.join(dati["body"].split()) if isinstance(dati["body"], str) and dati["body"] else ''
        log_info(f"Lunghezza body senza spazi: {len(body_clean)}")
        log_info(f"Primi 100 caratteri del body: {dati['body'][:100] if isinstance(dati['body'], str) and dati['body'] else ''}")
        if not body_clean:
            log_info(f"File {os.path.basename(percorso)} senza corpo: saltato.")
            return None
        prompt = genera_prompt(dati["body"] if isinstance(dati["body"], str) else '', dati["date"], dati["sender"])
        risposta = chiedi_al_modello(prompt)
        log_info(f"\n[DEBUG] Risposta LLM per {os.path.basename(percorso)}:\n{risposta}")
        log_info("\n🔍 Tentativo di parsing JSON...")
        risposta_pulita = risposta.strip()
        if risposta_pulita.startswith("```json"):
            risposta_pulita = risposta_pulita[7:]
        if risposta_pulita.startswith("```"):
            risposta_pulita = risposta_pulita[3:]
        if risposta_pulita.endswith("```"):
            risposta_pulita = risposta_pulita[:-3]
        risposta_pulita = risposta_pulita.strip()
        log_info("\n📝 Risposta pulita:")
        log_info(risposta_pulita)

        try:
            dati_estratti = json.loads(risposta_pulita)
            log_info("\n✅ JSON parsato con successo:")
            log_info(json.dumps(dati_estratti, indent=2, ensure_ascii=False))

            items_to_process = dati_estratti if isinstance(dati_estratti, list) else [dati_estratti]

            for item in items_to_process:
                for key, value in item.items():
                    if isinstance(value, str):
                        item[key] = value.strip()
                item['nome_file'] = os.path.basename(percorso)
                if 'mittente' in item and isinstance(item['mittente'], str) and '@' in item['mittente']:
                    item['mittente'] = item['mittente'].split('@', 1)[1].strip()
                oggetto = dati.get('subject', '') if 'subject' in dati else ''
                testo_filtrato = filtra_body_mail(dati['body']) if 'body' in dati and isinstance(dati['body'], str) else ''
                separatore = '=' * 100
                testo_finale = f"OGGETTO:\n{oggetto}\n{separatore}\n{testo_filtrato}"
                item['body_mail'] = testo_finale[:4000]

            return items_to_process

        except json.JSONDecodeError as e:
            log_error(f"\n❌ Errore nel parsing JSON per il file {percorso}")
            log_error(f"Errore specifico: {str(e)}")
            return None
    except Exception as e:
        import traceback
        log_error(f"\n❌ Errore nell'elaborazione del file {percorso}: {e}")
        log_error(traceback.format_exc())
        return None

def elabora_cartella(percorso_cartella):
    risultati = []
    file_elaborati = 0
    file_errore = 0
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = "elaborazioni"
    os.makedirs(output_dir, exist_ok=True)
    nome_file_csv = os.path.join(output_dir, f"risultati_elaborazione_{timestamp}.csv")

    fieldnames = [
        "data_mail", "numero_ordine", "nome", "cognome", "codice_fiscale",
        "telefono", "articolo", "prezzo", "quantita", "email",
        "mittente", "codice_barre", "nome_file"
    ]
    for file in os.listdir(percorso_cartella):
        if file.lower().endswith('.msg') or file.lower().endswith('.eml'):
            percorso_completo = os.path.join(percorso_cartella, file)
            risultato = elabora_file(percorso_completo)
            if risultato:
                if isinstance(risultato, list):
                    risultati.extend(risultato)
                    if INSERISCI_IN_ORACLE:
                        for item in risultato:
                            inserisci_dati_oracle([item], dsn=ORACLE_DSN, user=ORACLE_USER, password=ORACLE_PASSWORD)
                else:
                    risultati.append(risultato)
                    if INSERISCI_IN_ORACLE:
                        inserisci_dati_oracle([risultato], dsn=ORACLE_DSN, user=ORACLE_USER, password=ORACLE_PASSWORD)
                file_elaborati += 1
                log_info(f"\n✅ File elaborato con successo: {file}")
            else:
                file_errore += 1
                log_error(f"\n❌ Errore nell'elaborazione del file: {file}")
            log_info("Pausa di 5 secondi prima del prossimo file...")
            time.sleep(5)
    if risultati:
        try:
            with open(nome_file_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in risultati:
                    row_filtrato = {k: v for k, v in row.items() if k in fieldnames}
                    writer.writerow(row_filtrato)
            log_info(f"\n✅ Risultati salvati nel file: {nome_file_csv}")
        except Exception as e:
            log_error(f"\n❌ Errore nel salvataggio del file CSV: {e}")
    return file_elaborati, file_errore