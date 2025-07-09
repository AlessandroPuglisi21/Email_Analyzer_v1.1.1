import logging
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, 'log_generale.txt')
ERROR_LOG_FILE = os.path.join(LOG_DIR, 'log_errori.txt')

logger = logging.getLogger('email_analyzer')
logger.setLevel(logging.INFO)

fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
fh.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

eh = logging.FileHandler(ERROR_LOG_FILE, encoding='utf-8')
eh.setLevel(logging.ERROR)
eh.setFormatter(formatter)
logger.addHandler(eh)

def log_info(msg):
    print(msg)
    logger.info(msg)

def log_error(msg):
    print(msg)
    logger.error(msg)
