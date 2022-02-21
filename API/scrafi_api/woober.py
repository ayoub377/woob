import requests, sys, json, configparser, time, discord, traceback, logging, hashlib, os
from datetime import datetime

from woob.core import Woob
from woob.capabilities.bank import CapBank
from woob.capabilities.bill import CapDocument
from .creation import create_signature

from redis import Redis
from rq.job import Job, get_current_job


redis = Redis()
path = os.path.expanduser('~')
if "C:" in path:
    path = path.replace('\\', '/')

bankis = {
    'akhdar': 'Al Akhdar bank',
    'awb': 'Attijariwafa bank',
    'bmce': 'BMCE',
    'cdm': 'Crédit du Maroc',
    'cfg': 'CFG',
    'chaabi': 'Banque Populaire',
    'cih': 'CIH',
    'ineo': 'INEO'
}

billis = {
    'lydec': 'Lydec',
    'orange': 'Orange',
    'inwi': 'Inwi',
    'iam': 'Maroc Telecom',
    'billeo': 'BILLEO'
}

def setup_logger(name, log_file):
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        formatter = logging.Formatter('%(asctime)s | %(message)s', "%a %d %b - %H:%M:%S")
        file_handler = logging.FileHandler(log_file)
        console_handler = logging.StreamHandler(sys.stdout)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    return logger

def rq_logger():
    rqfile = f'{path}/scrafi_project/Logs/rq/rq.log'
    logger = setup_logger('rq_worker', rqfile)
    return logger

# def discord_msg(msg='===> UNCAUGHT ERROR <=== \n ', unparsed=None):
#     if unparsed:
#         e = msg
#         msg = '===> ENABLE TO PARSE WOOB RESULTS <=== \n '
#         msg += e
#     else:
#         for i in traceback.format_exc():
#             msg += i
#     while msg[-1:] == '\n':
#         msg = msg[:-1]
        
#     client = discord.Client()
#     @client.event
#     async def on_ready(msg=msg):
#         length = len(msg)
#         while length > 1980:
#             last = msg[:1980].rindex('\n')
#             message = msg[:last]
#             msg = msg[last + 1:]
#             await client.get_channel(892338601403228201).send('>>> ``` ' + message + ' ```')
#             length = len(msg)
#         await client.get_channel(892338601403228201).send('>>> ``` ' + msg + ' ```')
#         await client.close()

#     client.run('OTA3NjE4MDQ2OTIxODM0NTE2.YYpzLQ.jOYrIB9ONjQBc7MIqTuqZP7Do1w')

# def notify_zhor(flow, module, date, e, unparsed=None, logger=None):
#     if not logger:
#         logger = rq_logger()

#     logger.info('>>> Notify_zhor')
#     logger.error(e)

#     msg = '-+- FLOW : %s \n -+- BANK : %s \n -+- DATE : %s \n ' % (flow.capitalize(), module, date)
#     if unparsed:
#         discord_msg(msg=e, unparsed=unparsed)
#     else:
#         discord_msg(msg=msg)
    

class Woobank:
    logger = rq_logger()
    unparsed = None

    def __init__(self, flow, bank, acc_id, date):
        self.flow = flow
        self.bank = bank
        self.acc_id = acc_id
        self.bankia = bankis[bank]

        if date == 'Now':
            self.start_date = date
        else:
            self.start_date = datetime.strftime(date, '%d/%m/%Y')
    
    def add_backend(self, username, password, bankash):
        backend ="[%s]\n _module = %s\n login = %s\n password = %s\n\n" % (bankash, self.bank, username, password)
        with open(f'{path}/.config/woob/backends', 'a') as backends:
            backends.write(backend)

    def delete_backend(self, bankash):
        p = configparser.ConfigParser()
        with open(f'{path}/.config/woob/backends', "r") as backends:
            p.read_file(backends)
        p.remove_section(bankash)
        with open(f'{path}/.config/woob/backends', "w") as backends:
            p.write(backends)

    def error_response(self, error_msg):
        json_response = {}
        json_response["Response"] = "Error"
        
        if self.unparsed:
            self.logger.info('Enable to parse Woob results')
            # self.notify_zaz(error_msg)
            json_response["Error"] = "Un problème est survenu, veuillez réessayer ultérieurement."

        elif error_msg == 'credentials':
            self.logger.info('Wrong credentials')
            json_response["Error"] = "L'identifiant ou le mot de passe sont incorrects."

        elif error_msg == 'ID':
            self.logger.info('Account ID not found')
            json_response["Error"] = "L'ID du compte ne figure pas dans la liste des comptes disponibles."

        elif error_msg == 'nohistory':
            self.logger.info('No history available')
            json_response["Error"] = "Aucun historique n'est disponible depuis le %s." % self.start_date

        elif error_msg == 'bank':
            self.logger.info('Bank website out of service')
            json_response["Error"] = "Le connecteur %s n'est pas operationel." % self.bankia

        else:
            self.logger.info('BUG in "%s"' % self.flow)
            # self.notify_zaz(error_msg)
            json_response["Error"] = "Un problème est survenu, veuillez réessayer ultérieurement."
        return json_response

    # def notify_zaz(self, e):
    #     return notify_zhor(self.flow, self.bankia, self.start_date, e, self.unparsed)

    def call_woob(self, bankash):
        results = []
        w = Woob()
        w.load_backends(caps=CapBank)
        self.logger.info('Getting the %s...' % self.flow)

        try:
            if self.flow == 'history':
                woob_results = w[bankash].iter_history(self.acc_id, **{'start_date': self.start_date, 'end_date': datetime.today().strftime('%d/%m/%Y')})
                if self.bank == 'ineo':
                    return {"Response": "OK", "Transactions": woob_results}
            elif self.flow == 'account':
                woob_results = [w[bankash].get_account(self.acc_id)]
            elif self.flow == 'accounts':
                woob_results = w[bankash].iter_accounts()

            if not self.bankia in ('INEO', 'Banque Populaire') :
                w[bankash].browser.driver.quit()
                w[bankash].browser.vdisplay.stop()

            for result in woob_results:
                try:
                    data = {
                        'id': result.id,
                        'label': result.label,
                    }
                    if self.flow == 'history':
                        data['date'] = result.date.strftime("%d/%m/%Y")
                        data['solde'] = str(result.solde)

                    results.append(data)

                except AttributeError:
                    self.unparsed = True
                    return self.error_response(str(woob_results))

            self.logger.info('Returning data')
            if self.flow == 'history':
                return {"Response": "OK", "Transactions": results}
            elif len(woob_results) > 1:
                return {"Response": "Multicomptes", "Error": "Il existe plus d'un ID pour ce compte.", "Accounts": results}
            else:
                return {"Response": "OK", "Accounts": results}

        except Exception as e:
            if not self.bankia in ('INEO', 'Banque Populaire') :
                w[bankash].browser.driver.quit()
                w[bankash].browser.vdisplay.stop()
            else:
                pass

            error_msg = w[bankash].browser.error_msg
            if error_msg != '':
                return self.error_response(error_msg)
            else:
                return self.error_response(e)

    def connect(self, username, password):
        job_id = get_current_job().id
        bankash = hashlib.md5(bytearray(job_id, 'utf-8')).hexdigest()

        self.logger.info('RQ ### Woobank.connect(%s, ********, ********, %s, "%s")' % (self.bankia, self.acc_id, self.start_date))
        self.logger.info("%s JOB: %s" % (self.flow.upper(), job_id))
        
        self.add_backend(username, password, bankash)
        self.logger.info('>>> Calling woobank')
        data = self.call_woob(bankash)
        self.logger.info(data)
        self.logger.info('Truncating \n')
        self.delete_backend(bankash)

        return data


class Woobill:
    logger = rq_logger()
    unparsed = None

    def __init__(self, flow, username, password, bill, date):
        self.flow = flow
        self.username = username
        self.password = password
        self.bill = bill
        self.billia = billis[bill]

        if date == 'Now':
            self.start_date = date
        else:
            self.start_date = datetime.strftime(date, '%m/%Y')
    
    def add_backend(self, username, password, billash):
        backend ="[%s]\n _module = %s\n login = %s\n password = %s\n\n" % (billash, self.bill, username, password)
        with open(f'{path}/.config/woob/backends', 'a') as backends:
            backends.write(backend)

    def delete_backend(self, billash):
        p = configparser.ConfigParser()
        with open(f'{path}/.config/woob/backends', "r") as backends:
            p.read_file(backends)
        p.remove_section(billash)
        with open(f'{path}/.config/woob/backends', "w") as backends:
            p.write(backends)

    def error_response(self, error_msg):
        json_response = {}
        json_response["Response"] = "Error"
        
        if self.unparsed:
            self.logger.info('Enable to parse Woob results')
            # self.notify_zaz(error_msg)
            json_response["Error"] = "Un problème est survenu, veuillez réessayer ultérieurement."

        elif error_msg == 'credentials':
            self.logger.info('Wrong credentials')
            json_response["Error"] = "L'identifiant ou le mot de passe sont incorrects."

        elif error_msg == 'nobill':
            self.logger.info('No bill available')
            json_response["Error"] = "Aucune facture n'est disponible depuis le %s." % self.start_date

        elif error_msg == 'website':
            self.logger.info('Bill website out of service')
            json_response["Error"] = "Le connecteur %s n'est pas operationel." % self.billia

        else:
            self.logger.info('BUG in "%s"' % self.flow)
            # self.notify_zaz(error_msg)
            json_response["Error"] = "Un problème est survenu, veuillez réessayer ultérieurement."
        return json_response

    # def notify_zaz(self, e):
    #     return notify_zhor(self.flow, self.billia, self.start_date, e, self.unparsed)

    def call_woob(self, billash):
        results = []
        w = Woob()
        w.load_backends(caps=CapDocument)
        self.logger.info('Getting the bills...')

        try:
            if self.flow == 'bills':
                woob_results = w[billash].get_bills(self.start_date)

                if self.billia != 'BILLEO' :
                    w[billash].browser.driver.quit()
                    w[billash].browser.vdisplay.stop()

                for result in woob_results:
                    try:
                        data = {
                            'scrafiId': result.id,
                            'factureNumero': result.number,
                            'dateFacture': result.date,
                            'montantTTC': result.montant,
                            'PDF': result.pdf
                        }
                        results.append(data)

                    except AttributeError:
                        self.unparsed = True
                        return self.error_response(str(woob_results))

                self.logger.info('Returning data')
                return {"Response": "OK", "FactureAchat": results}

            elif self.flow == 'connect':
                woob_results = w[billash].connect()

                if self.billia != 'BILLEO' :
                    w[billash].browser.driver.quit()
                    w[billash].browser.vdisplay.stop()
                
                for result in woob_results:
                    try:
                        creds = {
                            'scrafiId': result,
                            'username': self.username,
                            'password': self.password
                        }
                
                    except AttributeError:
                        self.unparsed = True
                        return self.error_response(str(woob_results))

                self.logger.info('Returning data')
                return {"Response": "OK", "Tier": creds}

        except Exception as e:
            if not self.billia in ('BILLEO') :
                w[billash].browser.driver.quit()
                w[billash].browser.vdisplay.stop()
            else:
                pass

            error_msg = w[billash].browser.error_msg
            if error_msg != '':
                return self.error_response(error_msg)
            else:
                return self.error_response(e)

    def connect(self, username, password):
        job_id = get_current_job().id
        billash = hashlib.md5(bytearray(job_id, 'utf-8')).hexdigest()

        self.logger.info('RQ ### Woobill.connect(%s, ********, ********, "%s")' % (self.billia, self.start_date))
        self.logger.info("%s JOB: %s" % (self.flow.upper(), job_id))
        
        self.add_backend(username, password, billash)
        self.logger.info('>>> Calling woobill')
        data = self.call_woob(billash)
        self.logger.info(data)
        self.logger.info('Truncating \n')
        self.delete_backend(billash)
        
        return data


def notify_client(job_id):
    notify_job = get_current_job()
    logger = rq_logger()
    logger.info('RQ ### notify_client("%s") \n' % job_id)

    data = json.dumps({"notification": "Job is done", "job_id": job_id})
    signature = create_signature(data)
    headers = {'X-INEO-Signature': signature, 'content-type':'text/plain'}
    r_post = requests.post(
        'https://ineo.app/api/Webhook/IneoReceiver',
        headers=headers,
        data=data)
    response = str(r_post.content)
    logger.info('POST Response >>> ' + response)

    if '400' in response:
        logger.info('RETRIES LEFT : %i' % notify_job.retries_left)
        if notify_job.retries_left > 0:
            logger.info("Client can't find the job ID \n")
            raise Exception("Client can't find the job ID \n")
        else:
            job = Job.fetch(job_id, connection=redis)
            logger.info('DELETING RESULTS... \n')
            job.delete(delete_dependents=True)
    elif "404" in response:
        raise Exception('Error 404 \n')
    elif "502" in response:
        logger.error('502 Response ---> Backend out of service')
        time.sleep('480')
        raise Exception('Backend out of service \n')
    else:
        logger.info('no 400. no 404. and no 502.\n')