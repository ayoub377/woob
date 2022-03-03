import os, time, logging, sys

from redis import Redis
from rq import Queue


path = os.path.expanduser('~')
backend_file = f'{path}/.config/woob/backends'
redis = Redis()
q = Queue('scrafi', connection=redis)

logger = logging.getLogger('rq_worker')
if not logger.hasHandlers():
    formatter = logging.Formatter('%(asctime)s | %(message)s', "%a %d %b - %H:%M:%S")
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(console_handler)

jobs_qty = len(q)
while jobs_qty > 0:
    time.sleep(10)
    jobs_qty = len(q)

content = open(backend_file, 'r').read().strip()
if content:
    logger.info("-= Cleaning Job =- Removing backends.. \n")
    open(backend_file,"w").close()
else:
    logger.info('-= Cleaning Job =- Backend file is empty. \n')