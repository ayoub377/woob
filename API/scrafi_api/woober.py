import requests, sys, json, configparser, time, discord, random, traceback, logging, hashlib, os
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
    'inwi': 'Inwi',
    'iam': 'Maroc Telecom',
    'org': 'Orange Pro',
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

def discord_msg(msg='===> UNCAUGHT ERROR <=== \n ', unparsed=None):
    if unparsed:
        e = msg
        msg = '===> ENABLE TO PARSE WOOB RESULTS <=== \n '
        msg += e
    else:
        for i in traceback.format_exc():
            msg += i

    while msg[-1:] == '\n':
        msg = msg[:-1]

    # gifs = {
        # 1 : 'https://tenor.com/view/chaos-fire-gif-19254681',
        # 2 : 'https://tenor.com/view/spongebob-squarepants-spongebob-patrick-star-we-have-a-bug-panic-gif-4771359',
        # 3 : 'https://tenor.com/view/sad-tantrum-its-not-working-crying-kid-gif-17025985',
        # 4 : 'https://tenor.com/view/brand-new-bugs-bug-glitch-error-new-gif-22594128',
        # 5 : 'https://tenor.com/view/steve-urkel-jaleel-white-look-what-you-did-see-what-you-done-unimpressed-gif-15136944',
        # 6 : 'https://tenor.com/view/dr-house-gregory-house-oops-gif-6118887',
        # 7 : 'https://tenor.com/view/boys-dance-dealwithit-gif-4255501',
        # 8 : 'https://tenor.com/view/sorry-not-sorry-gif-9110784',
        # 9 : 'https://tenor.com/view/chris-hemsworth-im-not-even-sorry-sorry-not-sorry-gif-8270819',
        # 10: 'https://tenor.com/view/hello-sexy-hi-hello-mr-bean-gif-13830351',
        # 11: 'https://tenor.com/view/mr-bean-mr-beans-holiday-rowan-atkinson-lottery-raffle-gif-14784047',
        # 12: 'https://tenor.com/view/mr-bean-gif-8578130',
        # 13: 'https://tenor.com/view/mr-bean-b34n-benestad-alvesta-r0w4n-gif-21509234',
        # 14: 'https://tenor.com/view/mr-bean-what-angry-gif-12489655',
        # 15: 'https://tenor.com/view/mr-bean-middle-finger-fuck-you-fuck-everyone-smh-gif-5650690',
        # 16: 'https://tenor.com/view/trump-you-on-some-shit-donald-trump-gif-9570908',
        # 17: 'https://tenor.com/view/whatever-sarcasm-oh-well-pssh-yeah-okay-gif-4951048',
        # 18: 'https://tenor.com/view/clap-applause-proud-wow-amazed-gif-15751919',
        # 19: 'https://tenor.com/view/wow-omg-surprised-scared-kid-gif-10714204',
        # 20: 'https://tenor.com/view/krunt-emily-blunt-wow-gif-20540815',
        # 21: 'https://tenor.com/view/office-space-bill-lumbergh-we-have-sort-of-a-problem-here-problem-worried-gif-4780644',
        # 22: 'https://tenor.com/view/my-problems-are-your-problems-pay-attention-to-me-im-your-problem-take-care-of-me-mazikeen-gif-16845925',
        # 23: 'https://tenor.com/view/houston-we-have-a-problem-tom-hanks-jim-lovell-apollo13-somethings-wrong-gif-17242743',
        # 24: 'https://tenor.com/view/your-fault-leave-walk-out-finger-guns-spongebob-gif-17364939',
        # 25: 'https://tenor.com/view/youre-entirely-to-blame-blaming-its-you-its-your-fault-youre-to-blame-gif-15158052',
        # 26: 'https://tenor.com/view/seriously-are-you-serious-is-this-a-joke-gif-9295216',
        # 27: 'https://tenor.com/view/ffs-baby-really-oh-god-just-stop-gif-12739180',
        # 28: 'https://tenor.com/view/obama-what-seriously-wtf-gif-12341428',
        # 29: 'https://tenor.com/view/seriously-are-you-serious-kid-blinking-gif-15637790',
        # 30: 'https://tenor.com/view/oh-no-you-didnt-no-way-pout-upset-are-you-serious-gif-6213376',
        # 31: 'https://tenor.com/view/im-sorry-that-you-suck-animated-text-moving-text-gif-11613664',
        # 32: 'https://tenor.com/view/baby-yoda-um-nope-gif-18367579',
        # 33: 'https://tenor.com/view/haha-good-one-the-office-smh-no-gif-14556369',
        # 34: 'https://tenor.com/view/inauguration-cnn2017-donald-trump-finger-wag-no-gif-7576946',
        # 35: 'https://tenor.com/view/absolutely-not-nope-no-no-way-no-chance-gif-17243246',
        # 36: 'https://tenor.com/view/code-red-panic-omg-oh-no-warning-gif-16511097',
        # 37: 'https://tenor.com/view/this-code-will-one-hundred-percent-help-you-justin-mitchel-free-code-camp-this-code-will-work-perfectly-i-guarantee-this-code-is-effective-gif-22479594',
        # 38: 'https://tenor.com/view/jennifer-lawrence-you-failed-fail-failure-yeah-gif-4620641',
        # 39: 'https://tenor.com/view/star-wars-yoda-that-is-why-you-fail-fail-gif-17943164',
        # 40: 'https://tenor.com/view/homer-simpsons-simpson-fail-failure-gif-8569786',
        # 41: 'https://tenor.com/view/complete-failure-failure-fail-failed-messed-up-gif-13749983',
        # 42: 'https://tenor.com/view/stop-apologizing-and-correct-your-error-marco-inaros-keon-alexander-the-expanse-s506-gif-19851770',
        # 43: 'https://tenor.com/view/beepo-error-beepo-error-ownershub-bawwub-gif-22844466',
        # 44: 'https://tenor.com/view/error-type-glitch-enter-gif-16906556',
        # 45: 'https://tenor.com/view/warning-lights-cops-emergency-gif-6098038',
        # 46: 'https://tenor.com/view/alert-siren-warning-light-gif-15160785',
        # 47: 'https://tenor.com/view/minion-despicable-me-dreamworks-sirens-alarm-gif-5633151',
    # }
    # numb = random.randint(1, 47)

    client = discord.Client()
    @client.event
    async def on_ready():
        await client.get_channel(892338601403228201).send('>>> ``` ' + msg + ' ```')
        # await client.get_channel(892338601403228201).send(gifs[numb])
        await client.close()

    client.run('OTA3NjE4MDQ2OTIxODM0NTE2.YYpzLQ.jOYrIB9ONjQBc7MIqTuqZP7Do1w')

def notify_zhor(flow, module, date, e, unparsed=None, logger=None):
    if not logger:
        logger = rq_logger()

    logger.info('>>> Notify_zhor')
    logger.error(e)

    msg = '-+- FLOW : %s \n -+- BANK : %s \n -+- DATE : %s \n ' % (flow.capitalize(), module, date)
    if unparsed:
        discord_msg(msg=e, unparsed=unparsed)
    else:
        discord_msg(msg=msg)
    

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
            self.notify_zaz(error_msg)
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
            self.notify_zaz(error_msg)
            json_response["Error"] = "Un problème est survenu, veuillez réessayer ultérieurement."
        return json_response

    def notify_zaz(self, e):
        return notify_zhor(self.flow, self.bankia, self.start_date, e, self.unparsed)

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
            self.start_date = datetime.strftime(date, '%d/%m/%Y')
    
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
            self.notify_zaz(error_msg)
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
            self.notify_zaz(error_msg)
            json_response["Error"] = "Un problème est survenu, veuillez réessayer ultérieurement."
        return json_response

    def notify_zaz(self, e):
        return notify_zhor(self.flow, self.billia, self.start_date, e, self.unparsed)

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
                            'scrafiId': result.hashid,
                            'fournisseur': self.billia,
                            'numeroFacture': result.number,
                            'dateEcheance': result.date,
                            'montantTTC': result.montant,
                            'TVA': result.tva,
                            'PDF': result.pdf
                        }
                        results.append(data)

                    except AttributeError:
                        self.unparsed = True
                        return self.error_response(str(woob_results))

                self.logger.info('Returning data')
                return {"Response": "OK", "Bills": results}

            elif self.flow == 'connect':
                woob_results = w[billash].connect()

                if self.billia != 'BILLEO' :
                    w[billash].browser.driver.quit()
                    w[billash].browser.vdisplay.stop()
                
                for result in woob_results:
                    try:
                        creds = {
                            'scrafiId': result,
                            'fournisseur': self.billia,
                            'username': self.username,
                            'password': self.password
                        }
                        results.append(creds)
                
                    except AttributeError:
                        self.unparsed = True
                        return self.error_response(str(woob_results))

                self.logger.info('Returning data')
                return {"Response": "OK", "Credentials": results}

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