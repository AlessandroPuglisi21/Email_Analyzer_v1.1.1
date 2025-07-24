import os
import json
import csv
import time
from datetime import datetime
from components.logging_utils import log_info, log_error
from components.email_utils import estrai_testo_da_file, filtra_body_mail
from components.ai_utils import genera_prompt, chiedi_al_modello
from components.config import INSERISCI_IN_ORACLE, ORACLE_DSN, ORACLE_USER, ORACLE_PASSWORD, STORICO_DIR
from components.oracle_utils import inserisci_dati_oracle, leggi_codici_barre
import re

def elabora_file(percorso, codici_barre=None):
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
        prompt = genera_prompt(dati["body"] if isinstance(dati["body"], str) else '', dati["date"], dati["sender"], codici_barre)
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
                # Salvo il mittente originale
                mittente_originale = dati.get('sender', '')
                # Estrazione dominio dalla mail tra <> se presente
                dominio_mittente = ''
                match = re.search(r'<([^@<>]+@([^<>]+))>', mittente_originale)
                if match:
                    dominio_mittente = match.group(2).strip()
                elif '@' in mittente_originale:
                    dominio_mittente = mittente_originale.split('@', 1)[1].replace('>', '').strip()
                else:
                    dominio_mittente = mittente_originale
                item['mittente'] = dominio_mittente
                oggetto = dati.get('subject', '') if 'subject' in dati else ''
                testo_filtrato = filtra_body_mail(dati['body']) if 'body' in dati and isinstance(dati['body'], str) else ''
                separatore = '=' * 100
                testo_finale = f"MITTENTE: {mittente_originale}\nOGGETTO:\n{oggetto}\n{separatore}\n{testo_filtrato}"
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

def genera_nome_file_unico(percorso_cartella, nome_file):
    base, ext = os.path.splitext(nome_file)
    counter = 2
    nuovo_nome = nome_file
    while os.path.exists(os.path.join(percorso_cartella, nuovo_nome)):
        nuovo_nome = f"{base} ({counter}){ext}"
        counter += 1
    return nuovo_nome

def elabora_cartella(percorso_cartella):
    risultati = []
    file_elaborati = 0
    file_errore = 0
    codici_barre = leggi_codici_barre()
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
            risultato = elabora_file(percorso_completo, codici_barre)
            stato_file = None
            errore_oracle_globale = None
            if risultato:
                # Inserimento in Oracle e raccolta stato
                if isinstance(risultato, list):
                    risultati.extend(risultato)
                    if INSERISCI_IN_ORACLE:
                        risultato_aggiornato = []
                        errore_oracle_globale = False
                        for item in risultato:
                            res = inserisci_dati_oracle([item], dsn=ORACLE_DSN, user=ORACLE_USER, password=ORACLE_PASSWORD)
                            if res and isinstance(res, list):
                                risultato_aggiornato.append(res[0])
                                if res[0].get('errore_oracle'):
                                    errore_oracle_globale = True
                        stato_file = risultato_aggiornato[0].get('stato', None) if risultato_aggiornato else None
                    else:
                        stato_file = risultato[0].get('stato', None)
                        errore_oracle_globale = False
                else:
                    risultati.append(risultato)
                    if INSERISCI_IN_ORACLE:
                        res = inserisci_dati_oracle([risultato], dsn=ORACLE_DSN, user=ORACLE_USER, password=ORACLE_PASSWORD)
                        if res and isinstance(res, list):
                            stato_file = res[0].get('stato', None)
                            errore_oracle_globale = res[0].get('errore_oracle', True)
                        else:
                            stato_file = None
                            errore_oracle_globale = True
                    else:
                        stato_file = risultato.get('stato', None)
                        errore_oracle_globale = False
                if stato_file in ('N','X') and errore_oracle_globale is False:
                    log_info(f"\n✅ File elaborato con successo: {file}")
                    # Sposto il file nella cartella di storico
                    try:
                        os.makedirs(STORICO_DIR, exist_ok=True)
                        nome_file_unico = genera_nome_file_unico(STORICO_DIR, file)
                        percorso_storico = os.path.join(STORICO_DIR, nome_file_unico)
                        os.rename(percorso_completo, percorso_storico)
                        log_info(f"File spostato nella cartella di storico: {percorso_storico}")
                    except Exception as e:
                        log_error(f"Errore nello spostamento del file {file} nella cartella storico: {e}")
                ##elif stato_file in ('X', 'E'):
                ##    log_error(f"\n❌ File con errore logico (doppio o altro): {file}")
                else:
                    log_error(f"\n❌ File con errore sconosciuto: {file}, Stato = {stato_file}")
            else:
                log_error(f"\n❌ Errore nell'elaborazione del file: {file}")
            log_info("Pausa di 1 secondi prima del prossimo file...")
            time.sleep(1)
## Rainer - tolto questa parte perchè ormai lavoriamo solo sul DB
##    if risultati:
##        try:
##            with open(nome_file_csv, 'w', newline='', encoding='utf-8') as f:
##                writer = csv.DictWriter(f, fieldnames=fieldnames)
##                writer.writeheader()
##                for row in risultati:
##                    row_filtrato = {k: v for k, v in row.items() if k in fieldnames}
##                    writer.writerow(row_filtrato)
##            log_info(f"\n✅ Risultati salvati nel file: {nome_file_csv}")
##        except Exception as e:
##            log_error(f"\n❌ Errore nel salvataggio del file CSV: {e}")
    # Nuovo conteggio basato su tutti i risultati
    for r in risultati:
        stato = r.get('stato')
        if stato in ('N','X'):
            file_elaborati += 1
        else:
            file_errore += 1

    return file_errore, file_elaborati