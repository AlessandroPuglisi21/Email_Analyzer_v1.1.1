import os
from components.config import INSERISCI_IN_ORACLE, ORACLE_DSN, ORACLE_USER, ORACLE_PASSWORD
from components.logging_utils import log_info, log_error
from components.oracle_utils import verifica_tabella_oracle
from components.processing import elabora_cartella
from components.email_utils import estrai_testo_da_file


def main():
    if INSERISCI_IN_ORACLE:
        verifica_tabella_oracle(ORACLE_DSN, ORACLE_USER, ORACLE_PASSWORD, 'ord_eatin')

    while True:
        percorso = input("\nInserisci il percorso della cartella contenente i file .msg o .eml (o 'exit' per uscire): ").strip()
        if percorso.lower() == 'exit':
            log_info("\n👋 Arrivederci!")
            break

        percorso = percorso.strip('"\'')
        if not os.path.isdir(percorso):
            log_error("\n❌ Il percorso specificato non è una cartella valida!")
            continue

        file_elaborati, file_errore = elabora_cartella(percorso)
        log_info("\n📊 Riepilogo elaborazione:")
        log_info(f"✅ File elaborati con successo: {file_elaborati}")
        log_info(f"❌ File con errori: {file_errore}")

        continua = input("\nVuoi elaborare un'altra cartella? (s/n): ").strip().lower()
        if continua != 's':
            log_info("\n👋 Arrivederci!")
            break

if __name__ == "__main__":
    main()

def avvia_elaborazione_email():
    from components.processing import elabora_cartella

    cartella = r"C:\PYTHON\Email_Analyzer_v1.1\Mail Fittizie"

    if not os.path.isdir(cartella):
        log_error(f"\n❌ La cartella {cartella} non esiste.")
        return 0

    file_ok, file_errore = elabora_cartella(cartella)

    log_info("\n📊 Riepilogo elaborazione (da GUI):")
    log_info(f"✅ File elaborati con successo: {file_ok}")
    log_info(f"❌ File con errori: {file_errore}")

    return file_ok

def avvia_elaborazione_email_cartella(cartella):
    from components.processing import elabora_cartella

    if not os.path.isdir(cartella):
        log_error(f"\n❌ La cartella {cartella} non esiste.")
        return 0, 0

    file_ok, file_errore = elabora_cartella(cartella)

    log_info("\n📊 Riepilogo elaborazione (da GUI):")
    log_info(f"✅ File elaborati con successo: {file_ok}")
    log_info(f"❌ File con errori: {file_errore}")

    return file_ok, file_errore


