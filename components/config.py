import os
from dotenv import load_dotenv
import cx_Oracle

load_dotenv()

USA_LLM = "Copilote" # Scegli tra: "Gemini", "OpenAI", "Copilote" 

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
COPILOTE_API_KEY = os.getenv("COPILOTE_API_KEY")
COPILOTE_ENDPOINT = os.getenv("COPILOTE_ENDPOINT")
COPILOTE_DEPLOYMENT_NAME = os.getenv("COPILOTE_DEPLOYMENT_NAME")

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
NOTIFY_EMAIL_TO = os.getenv("NOTIFY_EMAIL_TO")
NOTIFY_EMAIL_FROM = os.getenv("NOTIFY_EMAIL_FROM")



ORACLE_HOST = os.getenv("ORACLE_HOST")
ORACLE_PORT = os.getenv("ORACLE_PORT")
ORACLE_SERVICE = os.getenv("ORACLE_SERVICE")
ORACLE_USER = os.getenv("ORACLE_USER")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD")

required_vars = {
    "ORACLE_HOST": ORACLE_HOST,
    "ORACLE_PORT": ORACLE_PORT,
    "ORACLE_SERVICE": ORACLE_SERVICE,
    "ORACLE_USER": ORACLE_USER,
    "ORACLE_PASSWORD": ORACLE_PASSWORD,
}
missing = [k for k, v in required_vars.items() if not v]
if missing:
    raise ValueError(f"Devi impostare queste variabili nel file .env: {', '.join(missing)}")

if ORACLE_PORT is None or not ORACLE_PORT.isdigit():
    raise ValueError("ORACLE_PORT deve essere un numero intero valido nel file .env")
ORACLE_DSN = cx_Oracle.makedsn(ORACLE_HOST, int(ORACLE_PORT), service_name=ORACLE_SERVICE)

INSERISCI_IN_ORACLE = True


