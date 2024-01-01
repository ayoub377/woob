import configparser
import hashlib
import os
from redis import Redis
from rq import Queue, Retry
from .woober import rq_logger, Woobank, Woobill, notify_client, discord_msg
from woob.core.woob import Woob

path = os.path.expanduser('~')

if "C:" in path:
    path = path.replace('\\', '/')

redis = Redis()
q = Queue('scrafi', connection=redis)


def del_backend(job, connection, type, value, traceback):
    logger = rq_logger()
    logger.error('Uncaught error', exc_info=True)
    discord_msg()

    logger.warning(f'/!\ DELETING BACKEND : {job.id} /!\ \n')
    b_hash = hashlib.md5(bytearray(job.id, 'utf-8')).hexdigest()

    w = Woob()
    w.load_backends()

    try:
        w[b_hash].browser.driver.quit()
        w[b_hash].browser.vdisplay.stop()

    except AttributeError:
        pass

    except Exception as e:
        logger.error(e, exc_info=True)
        os.system("pkill chrome")

    p = configparser.ConfigParser()

    with open(f'{path}/.config/woob/backends', "r") as f:
        p.read_file(f)

    p.remove_section(b_hash)

    with open(f'{path}/.config/woob/backends', "w") as f:
        p.write(f)

    notify_client(job_id=job.id)


def woober_connect(woober, username, password):
    return woober.connect(username, password)


def add_to_bank_q(flow, bank, username, password, acc_id, date):
    woobank = Woobank(flow, bank, acc_id, date)

    job = q.create_job(
        woober_connect,
        args=(woobank, username, password),
        result_ttl=3600,  # 1 hour

        on_failure=del_backend
    )

    # run the job
    job.perform()

    # q.enqueue(
    #     notify_client,
    #     job.id,
    #     depends_on=job,
    #     retry=Retry(max=2, interval=120)  # 2 mins
    # )

    return {'job_id': job.id}


def add_to_bill_q(flow, username, password, bill, date):
    woobill = Woobill(flow, username, password, bill, date)

    # job = q.enqueue(
    #     woober_connect,
    #     args=(woobill, username, password),
    #     result_ttl=3600,  # 1 hour
    #     job_timeout=600,  # 10 mins
    #     on_failure=del_backend
    # )

    # q.enqueue(
    #     notify_client,
    #     job.id,
    #     depends_on=job,
    #     retry=Retry(max=2, interval=120)  # 2 mins
    # )

    job = woober_connect(woobill, username, password)

    return {'job_id': job.id}
