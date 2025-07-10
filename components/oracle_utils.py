import cx_Oracle
from components.logging_utils import log_info, log_error
from components.config import ORACLE_DSN, ORACLE_USER, ORACLE_PASSWORD

# Inizializza Oracle Client (obbligatorio per Windows)
try:
    cx_Oracle.init_oracle_client(lib_dir=r"C:\instantclient_11_2")

except Exception as e:
    log_error(f"\n❌ Errore nell'inizializzazione del client Oracle: {e}")
    exit(1)

def verifica_tabella_oracle(dsn, user, password, nome_tabella):
    try:
        conn = cx_Oracle.connect(user=user, password=password, dsn=dsn)
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM all_tables 
            WHERE table_name = :nome_tabella AND owner = :owner
        """, nome_tabella=nome_tabella.upper(), owner=user.upper())
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        if count == 0:
            log_error(f"\n❌ La tabella '{nome_tabella}' non esiste nello schema Oracle '{user}'.")
            exit(1)
        else:
            log_info(f"\n✅ Tabella '{nome_tabella}' trovata nello schema Oracle '{user}'.")
    except Exception as e:
        log_error(f"\n❌ Errore nella verifica della tabella Oracle: {e}")
        exit(1)

def get_max_ord_key(dsn, user, password):
    try:
        conn = cx_Oracle.connect(user=user, password=password, dsn=dsn)
        cur = conn.cursor()
        cur.execute("SELECT NVL(MAX(ORD_KEY), 0) FROM ord_eatin")
        max_key = cur.fetchone()[0]
        cur.close()
        conn.close()
        return int(max_key)
    except Exception as e:
        log_error(f"\n❌ Errore nel recupero di ORD_KEY massimo da Oracle: {e}")
        return -1

def inserisci_dati_oracle(dati, dsn, user, password):
    max_ord_key = get_max_ord_key(dsn, user, password)
    if max_ord_key == -1:
        log_error("Impossibile procedere con l'inserimento in Oracle a causa di un errore nel recupero di ORD_KEY.")
        return
    try:
        conn = cx_Oracle.connect(user=user, password=password, dsn=dsn)
        cur = conn.cursor()
        sql = """
            INSERT INTO ord_eatin (
                ORD_KEY, data_mail, numero_ordine, nome, cognome, codice_fiscale, telefono,
                articolo, prezzo, quantita, email, mittente, codice_barre, nome_file, stato, PROVIENE_DA, BODY_MAIL, MESS_ERRORE, UTENTE
            ) VALUES (
                :ord_key, :data_mail, :numero_ordine, :nome, :cognome, :codice_fiscale, :telefono,
                :articolo, :prezzo, :quantita, :email, :mittente, :codice_barre, :nome_file, :stato, :proviene_da, :body_mail, :mess_errore, :utente
            )
        """
        # Query per controllare se la mail è già presente
        check_email_sql = "SELECT COUNT(*) FROM ord_eatin WHERE email = :email"
        for riga in dati:
            max_ord_key += 1
            riga['ord_key'] = max_ord_key
            riga['proviene_da'] = 'M'
            riga['utente'] = None  # UTENTE può rimanere NULL
            for key, value in riga.items():
                if isinstance(value, str):
                    riga[key] = value.strip()
            if 'body_mail' not in riga:
                riga['body_mail'] = ''
            # Controllo se la mail è già presente
            cur.execute(check_email_sql, {'email': riga['email']})
            email_gia_presente = cur.fetchone()[0] > 0
            if email_gia_presente:
                riga['stato'] = 'E'
                riga['mess_errore'] = "email già presente nel db"
            else:
                riga['stato'] = 'N'
                riga['mess_errore'] = None
            cur.execute(sql, riga)

        conn.commit()
        cur.close()
        conn.close()
        log_info(f"\n✅ Inseriti {len(dati)} record nel database Oracle.")
    except Exception as e:
        log_error(f"\n❌ Errore nell'inserimento dati in Oracle: {e}")

def leggi_codici_barre():
    try:
        import cx_Oracle
        from components.config import ORACLE_DSN, ORACLE_USER, ORACLE_PASSWORD
        conn = cx_Oracle.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)
        cur = conn.cursor()
        sql = """
            SELECT AE_BARRE, AE_DESC, STATO FROM art_eatin WHERE STATO = 'f'
        """
        cur.execute(sql)
        codici = {}
        for row in cur:
            codice = str(row[0]).strip()
            descrizione = str(row[1]).strip()
            codici[descrizione] = codice
        cur.close()
        conn.close()
        return codici
    except Exception as e:
        from components.logging_utils import log_error
        log_error(f"\n❌ Errore nella lettura dei codici a barre da Oracle: {e}")
        return {}
