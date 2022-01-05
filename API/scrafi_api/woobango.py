import configparser, hashlib, os

from redis import Redis
from rq import Queue, Retry

from woob.core.woob import Woob
from woob.capabilities.bank import CapBank

from scrafi_api.woober import rq_logger, Woober, notify_client, discord_msg


path = os.path.expanduser('~')
if "C:" in path:
    path = path.replcae('\\', '/')
    
redis = Redis()
q = Queue('scrafi', connection=redis)


def del_backend(job, connection, type, value, traceback):
    logger = rq_logger()
    logger.error('Uncaught error', exc_info=True)
    discord_msg()

    logger.warning(f'/!\ DELETING BACKEND : {job.id} /!\ \n')
    p = configparser.ConfigParser()
    with open(f'{path}/.config/woob/backends', "r") as f:
        p.read_file(f)

    bankash = hashlib.md5(bytearray(job.id, 'utf-8')).hexdigest()
    p.remove_section(bankash)

    with open(f'{path}/.config/woob/backends', "w") as f:
        p.write(f)

    w = Woob()
    w.load_backends(CapBank)
    try:
        w[bankash].browser.driver.quit()
    except Exception:
        pass


def woober_connect(woober, username, password):
    return woober.connect(username, password)


def add_to_q(flow, bank, username, password, acc_id, date):
    woober = Woober(flow, bank, acc_id, date)

    job = q.enqueue(
        woober_connect, 
        args=(woober, username, password), 
        result_ttl=3600, # 1 hour
        job_timeout=600, # 10 mins
        on_failure=del_backend
        )

    q.enqueue(
        notify_client, 
        job.id,
        depends_on=job, 
        retry=Retry(max=2, interval=120) # 2 mins
        )
    return {'job_id': job.id}
