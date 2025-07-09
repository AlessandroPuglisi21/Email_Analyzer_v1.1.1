import os
from dotenv import load_dotenv

load_dotenv()

USA_LLM = "Gemini" # Scegli tra: "Gemini", "OpenAI", "Copilote" 

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
COPILOTE_API_KEY = os.getenv("COPILOTE_API_KEY")
COPILOTE_ENDPOINT = os.getenv("COPILOTE_ENDPOINT")
COPILOTE_DEPLOYMENT_NAME = os.getenv("COPILOTE_DEPLOYMENT_NAME")

ORACLE_DSN = "192.168.253.82:1521/seaora"

ORACLE_USER = 'seacng'
ORACLE_PASSWORD = 'seacng'

INSERISCI_IN_ORACLE = True

CARTELLA_MAIL = os.getenv("CARTELLA_MAIL", "")
