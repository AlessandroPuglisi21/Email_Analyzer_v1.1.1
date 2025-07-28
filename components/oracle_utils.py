import cx_Oracle
from contextlib import contextmanager
from components.logging_utils import log_info, log_error
from components.config import ORACLE_DSN, ORACLE_USER, ORACLE_PASSWORD
from components.notification_utils import send_error_notification

# Inizializza Oracle Client (obbligatorio per Windows)
try:
    cx_Oracle.init_oracle_client(lib_dir=r"C:\instantclient_11_2")

except Exception as e:
    log_error(f"\n❌ Errore nell'inizializzazione del client Oracle: {e}")
    send_error_notification(
        subject="Errore inizializzazione client Oracle",
        body=f"Si è verificato un errore nell'inizializzazione del client Oracle.\n\nErrore: {e}"
    )
    exit(1)

def verifica_tabella_oracle(dsn, user, password, nome_tabella):
    ##print(f"[DEBUG] Tentativo connessione Oracle: dsn={dsn}, user={user}, password={'*' * len(password)} tabella={nome_tabella}")
    try:
        conn = cx_Oracle.connect(user=user, password=password, dsn=dsn)
        print("[DEBUG] Connessione Oracle riuscita.")
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM all_tables 
            WHERE table_name = :nome_tabella AND owner = :owner
        """, nome_tabella=nome_tabella.upper(), owner=user.upper())
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        ##  print(f"[DEBUG] Query tabella eseguita, count={count}")
        if count == 0:
            log_error(f"\n❌ La tabella '{nome_tabella}' non esiste nello schema Oracle '{user}'.")
            exit(1)
        else:
            log_info(f"\n✅ Tabella '{nome_tabella}' trovata nello schema Oracle '{user}'.")
    except Exception as e:
        print(f"[DEBUG] Errore connessione Oracle: {e}")
        log_error(f"\n❌ Errore nella verifica della tabella Oracle: {e}")
        send_error_notification(
            subject="Errore connessione Oracle",
            body=f"Si è verificato un errore nella connessione al database Oracle durante la verifica della tabella '{nome_tabella}'.\n\nErrore: {e}"
        )
        exit(1)

##def get_max_ord_key(dsn, user, password):  ## creare lock per la tabella
##    try:
##        conn = cx_Oracle.connect(user=user, password=password, dsn=dsn)
##        cur = conn.cursor()
##        cur.execute("SELECT NVL(MAX(ORD_KEY), 0) FROM ord_eatin")
##        max_key = cur.fetchone()[0]
##        cur.close()
##        conn.close()
##        return int(max_key)
##    except Exception as e:
##        log_error(f"\n❌ Errore nel recupero di ORD_KEY massimo da Oracle: {e}")
##        return -1

def inserisci_dati_oracle(dati, dsn, user, password):
##    Tolta perchè c'è la sequence
##    max_ord_key = get_max_ord_key(dsn, user, password)
##    if max_ord_key == -1:
##        log_error("Impossibile procedere con l'inserimento in Oracle a causa di un errore nel recupero di ORD_KEY.")
##        for riga in dati:
##            riga['errore_oracle'] = True
##        return dati  # restituisco comunque la lista
    try:
        conn = cx_Oracle.connect(user=user, password=password, dsn=dsn)
        cur = conn.cursor()
        sql = """
            INSERT INTO ord_eatin (
                ORD_KEY, data_mail, numero_ordine, nome, cognome, codice_fiscale, telefono,
                articolo, prezzo, quantita, email, mittente, codice_barre, nome_file, stato, PROVIENE_DA, BODY_MAIL, MESS_ERRORE, UTENTE
            ) VALUES (
                ord_eatin_seq.NEXTVAL, :data_mail, :numero_ordine, :nome, :cognome, :codice_fiscale, :telefono,
                :articolo, :prezzo, :quantita, :email, :mittente, :codice_barre, :nome_file, :stato, :proviene_da, :body_mail, :mess_errore, :utente
            )
        """
        check_email_sql = "SELECT COUNT(*) FROM ord_eatin WHERE mittente = :mittente AND numero_ordine = :numero_ordine AND articolo = :articolo"
        import traceback
        for riga in dati:
            try:
                riga['proviene_da'] = 'M'
                riga['utente'] = None  # UTENTE può rimanere NULL
                for key, value in riga.items():
                    if isinstance(value, str):
                        riga[key] = value.strip()
                if 'body_mail' not in riga:
                    riga['body_mail'] = ''
                cur.execute(check_email_sql, {'mittente': riga['mittente'], 'numero_ordine': riga['numero_ordine'], 'articolo': riga['articolo']})
                email_gia_presente = cur.fetchone()[0] > 0
                if email_gia_presente:
                    riga['stato'] = 'X'
                    riga['mess_errore'] = "mittente, numero ordine e articolo già presenti nel db"
                else:
                    riga['stato'] = 'N'
                    riga['mess_errore'] = None
                cur.execute(sql, riga)
                riga['errore_oracle'] = False
            except Exception as e:
                dettagli_mail = (
                    f"Oggetto: {riga.get('subject', 'N/A')}\n"
                    f"Mittente: {riga.get('mittente', 'N/A')}\n"
                    f"Destinatario: {riga.get('email', 'N/A')}\n"
                    f"Data mail: {riga.get('data_mail', 'N/A')}\n"
                    f"Nome file: {riga.get('nome_file', 'N/A')}\n"
                    f"Numero ordine: {riga.get('numero_ordine', 'N/A')}\n"
                )
                corpo = (
                    "Si è verificato un errore durante l'inserimento di una mail nel Database.\n\n"
                    "Dettagli mail:\n"
                    "--------------------------------\n"
                    f"{dettagli_mail}\n"
                    f"Errore Oracle:\n{e}\n\n"
                    f"Traceback:\n{traceback.format_exc()}"
                )
                oggetto_mail = f"Errore inserimento: {riga.get('nome_file', 'Mail senza nome')}"
                send_error_notification(
                    subject=oggetto_mail,
                    body=corpo
                )
                log_error(f"\n❌ Errore nell'inserimento dati in Oracle per la mail '{riga.get('nome_file', 'Mail senza nome')}': {e}")
                riga['errore_oracle'] = True
                riga['stato'] = 'O'
        conn.commit()
        cur.close()
        conn.close()
        # Conteggio dei record inseriti senza errori
        inseriti = sum(1 for r in dati if r.get('errore_oracle') is False)
        if inseriti > 0:
            log_info(f"\n✅ Inseriti {inseriti} record nel database Oracle.")
        else:
            log_error(f"\n❌ Nessun record inserito nel database Oracle.")
            for riga in dati:
                riga['errore_oracle'] = True
        return dati  # restituisco la lista aggiornata
    except Exception as e:
        log_error(f"\n❌ Errore generale nell'inserimento dati in Oracle: {e}")
        send_error_notification(
            subject="Errore generale connessione/inserimento Oracle",
            body=f"Si è verificato un errore generale nella connessione o nell'inserimento dati in Oracle.\n\nErrore: {e}"
        )
        for riga in dati:
            riga['errore_oracle'] = True
            riga['stato'] = 'O'
        return dati  # restituisco comunque la lista

def leggi_codici_barre():
    ## print("[DEBUG] Inizio lettura codici a barre da Oracle...")
    try:
        import cx_Oracle
        from components.config import ORACLE_DSN, ORACLE_USER, ORACLE_PASSWORD
        ## print(f"[DEBUG] Parametri Oracle: DSN={ORACLE_DSN}, USER={ORACLE_USER}, PASSWORD={'*' * len(ORACLE_PASSWORD)}")
        conn = cx_Oracle.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)
        ## print("[DEBUG] Connessione Oracle per codici a barre riuscita.")
        cur = conn.cursor()
        sql = """
            -- SELECT AE_BARRE, AE_DESC, STATO FROM art_eatin WHERE STATO = 'f'
            SELECT BARCODE, NAME, DELETED FROM BOXES WHERE DELETED = 0       
        """
        cur.execute(sql)
        codici = {}
        for row in cur:
            codice = str(row[0]).strip()
            descrizione = str(row[1]).strip()
            codici[descrizione] = codice
        cur.close()
        conn.close()
        print(f"[DEBUG] Codici a barre letti: {len(codici)}")
        return codici
    except Exception as e:
        print(f"[DEBUG] Errore lettura codici a barre: {e}")
        log_error(f"\n❌ Errore nella lettura dei codici a barre da Oracle: {e}")
        send_error_notification(
            subject="Errore lettura codici a barre da Oracle",
            body=f"Si è verificato un errore nella lettura dei codici a barre dal database Oracle.\n\nErrore: {e}"
        )
        return {}

## SICUREZZA CONNESSIONI
# Pool di connessioni sicuro
pool = None

def init_connection_pool():
    """Inizializza un pool di connessioni sicuro"""
    global pool
    try:
        pool = cx_Oracle.create_pool(
            user=ORACLE_USER,
            password=ORACLE_PASSWORD,
            dsn=ORACLE_DSN,
            min=1,            # Numero minimo di connessioni aperte all’avvio
            max=5,            # Numero massimo di connessioni nel pool
            increment=1,      # Quante connessioni aggiungere quando serve crescere
            timeout=60,       # Inattività >60 s => connessione chiusa se sopra min
            getmode=cx_Oracle.SPOOL_ATTRVAL_WAIT  # Attende se pool pieno
        )
        log_info("✅ Pool di connessioni Oracle inizializzato")
    except Exception as e:
        log_error(f"❌ Errore inizializzazione pool: {e}")
        raise

@contextmanager
def get_oracle_connection():
    """Context manager per connessioni sicure"""
    if not pool:
        init_connection_pool()
    
    conn = None
    try:
        conn = pool.acquire()
    except Exception as e:
        log_error(f"❌ Errore connessione Oracle: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            pool.release(conn)

def leggi_codici_barre():
    ## print("[DEBUG] Inizio lettura codici a barre da Oracle...")
    try:
        import cx_Oracle
        from components.config import ORACLE_DSN, ORACLE_USER, ORACLE_PASSWORD
        ## print(f"[DEBUG] Parametri Oracle: DSN={ORACLE_DSN}, USER={ORACLE_USER}, PASSWORD={'*' * len(ORACLE_PASSWORD)}")
        conn = cx_Oracle.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)
        ## print("[DEBUG] Connessione Oracle per codici a barre riuscita.")
        cur = conn.cursor()
        sql = """
            -- SELECT AE_BARRE, AE_DESC, STATO FROM art_eatin WHERE STATO = 'f'
            SELECT BARCODE, NAME, DELETED FROM BOXES WHERE DELETED = 0       
        """
        cur.execute(sql)
        codici = {}
        for row in cur:
            codice = str(row[0]).strip()
            descrizione = str(row[1]).strip()
            codici[descrizione] = codice
        cur.close()
        conn.close()
        print(f"[DEBUG] Codici a barre letti: {len(codici)}")
        return codici
    except Exception as e:
        print(f"[DEBUG] Errore lettura codici a barre: {e}")
        log_error(f"\n❌ Errore nella lettura dei codici a barre da Oracle: {e}")
        send_error_notification(
            subject="Errore lettura codici a barre da Oracle",
            body=f"Si è verificato un errore nella lettura dei codici a barre dal database Oracle.\n\nErrore: {e}"
        )
        return {}
