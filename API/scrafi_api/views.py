import json, os
from datetime import datetime

from django.http import HttpResponse
from django.http.response import HttpResponseForbidden
from rest_framework.views import APIView
from oauth2_provider.views.generic import ProtectedResourceView

from redis import Redis
from rq.job import Job
from rq.registry import FailedJobRegistry
from rq.exceptions import NoSuchJobError

from .woobango import add_to_bank_q, add_to_bill_q
from .woober import setup_logger, notify_zhor

redis = Redis()
path = os.path.expanduser('~')
if "C:" in path:
    path = path.replace('\\', '/')

def record_request(request):
    customfile = f'{path}/scrafi_project/Logs/django/custom/custom.log'
    custom_logger = setup_logger(f'custom_logger', customfile)
    dilog = {}
    log = ''
    
    if request.method == 'POST':
        dilog['Path'] = 'POST  ' + request.path_info
    elif request.method == 'GET':
        dilog['Job ID'] = request.query_params['job_id']
        dilog['Path'] = 'GET  ' + request.path_info
        
    if request.auth:
        dilog['Authorization'] = request.auth
        
    dilog['Headers'] = request._request.headers
    
    ip = request.META.get('HTTP_X_FORWARDED_FOR')
    rmt_addr = request.META.get('REMOTE_ADDR')
    if ip:
        dilog['IP'] = ip
    else:
        dilog['Remote address'] = rmt_addr
        
    if request.META.get('HTTP_REFERER'):
        dilog['Referer'] = request.META.get('HTTP_REFERER')
        
    if request._request.COOKIES:
        dilog['Cookies'] = request._request.COOKIES

    for key, value in dilog.items():
        log += f"\n     {key} : {value}"
    
    log += "\n"
    custom_logger.info(log)
    

def process_history_request(request, bank, endpoint):
    customfile = f'{path}/scrafi_project/Logs/django/custom/custom.log'
    custom_logger = setup_logger(f'custom_logger', customfile)
    if bank == 'banque populaire':
        bank = 'chaabi'

    available_banks = ['akhdar', 'awb', 'bmce', 'cdm', 'cfg', 'chaabi', 'cih', 'ineo']
    if bank not in available_banks:
        response = json.dumps([{"Response": "Error", "ERROR": "Le connecteur %s n'existe pas." % bank}])
        custom_logger.info('[{"Response": "Error", "ERROR": "Le connecteur %s n\'existe pas."}]' % bank)
        return HttpResponse(response, content_type='text/json')
        

    username = request.data['username']
    if username == '':
        response = json.dumps([{"Response": "Error", "ERROR": "L'identifiant est obligatoire."}])
        custom_logger.info('[{"Response": "Error", "ERROR": "L\'identifiant est obligatoire."}]')
        return HttpResponse(response, content_type='text/json')

    password = request.data['password']
    if password == '':
        response = json.dumps([{"Response": "Error", "ERROR": "Le mot de passe est obligatoire."}])
        custom_logger.info('[{"Response": "Error", "ERROR": "Le mot de passe est obligatoire."}]')
        return HttpResponse(response, content_type='text/json')

    acc_id = request.data['acc_id']
    if acc_id in ('', ' '):
        if endpoint == 'synchro':
            response = json.dumps([{"Response": "Error", "ERROR": "L'ID du compte est obligatoire."}])
            custom_logger.info('[{"Response": "Error", "ERROR": "L\'ID du compte est obligatoire."}]')
            return HttpResponse(response, content_type='text/json')
        elif endpoint == 'create':
            acc_id = 'no_id'
            flow = 'accounts'
    else:
        flow = 'account'

    if endpoint == 'synchro':
        flow = 'history'
        date = request.data['date']
        if date == '':
            start_date = datetime.today().replace(day=1)

        if not isinstance(date, datetime):
            try:
                start_date = datetime.strptime(date, '%Y%m%d')
                
            except ValueError:
                response = json.dumps([{"Response": "Error", "ERROR": "La date doit être sous format : AAAAmmjj. (exemple: 20210825)"}])
                custom_logger.info('[{"Response": "Error", "ERROR": "La date doit être sous format : AAAAmmjj. (exemple: 20210825)"}]')
                return HttpResponse(response, content_type='text/json')
    else:
        start_date = 'Now'

    job_id = add_to_bank_q(flow, bank, username, password, acc_id, start_date)
    try:
        response = json.dumps(job_id, indent=4)
    except Exception as e:
        notify_zhor(flow=flow, module=bank, date=start_date, e=e)
        response = json.dumps([{"Response": "Error", "ERROR": "Un problème s'est produit. Veuillez réenvoyer votre requête plus tard."}])
        custom_logger.info('[{"Response": "Error", "ERROR": "Un problème s\'est produit. Veuillez réenvoyer votre requête plus tard."}]')
    
    return HttpResponse(response, content_type='text/json')


def process_bill_request(request, bill, endpoint):
    customfile = f'{path}/scrafi_project/Logs/django/custom/custom.log'
    custom_logger = setup_logger(f'custom_logger', customfile)
    available_bills = ['lydec', 'orange', 'iam']
    if bill not in available_bills:
        response = json.dumps([{"Response": "Error", "ERROR": "Le connecteur %s n'existe pas." % bill}])
        custom_logger.info('[{"Response": "Error", "ERROR": "Le connecteur %s n\'existe pas."}]' % bill)
        return HttpResponse(response, content_type='text/json')

    username = request.data['username']
    if username == '':
        response = json.dumps([{"Response": "Error", "ERROR": "L'identifiant est obligatoire."}])
        custom_logger.info('[{"Response": "Error", "ERROR": "L\'identifiant est obligatoire."}]')
        return HttpResponse(response, content_type='text/json')

    password = request.data['password']
    if password == '':
        response = json.dumps([{"Response": "Error", "ERROR": "Le mot de passe est obligatoire."}])
        custom_logger.info('[{"Response": "Error", "ERROR": "Le mot de passe est obligatoire."}]')
        return HttpResponse(response, content_type='text/json')

    if endpoint == 'synchro':
        flow = 'bills'
        date = request.data['date']
        if date == '':
            response = json.dumps([{"Response": "Error", "ERROR": 'La date est obligatoire.'}])
            custom_logger.info('[{"Response": "Error", "ERROR": "La date est obligatoire."}]')
            return HttpResponse(response, content_type='text/json')
        else:
            try:
                start_date = datetime.strptime(date, '%Y%m')
            except ValueError:
                response = json.dumps([{"Response": "Error", "ERROR": 'La date doit être sous format : AAAAmm. (exemple: 202108)'}])
                custom_logger.info('[{"Response": "Error", "ERROR": "La date doit être sous format : AAAAmm. (exemple: 202108)"}]')
                return HttpResponse(response, content_type='text/json')

    elif endpoint == 'create':
        flow = 'connect'
        start_date = 'Now'

    job_id = add_to_bill_q(flow, username, password, bill, start_date)
    try:
        response = json.dumps(job_id, indent=4)
    except Exception as e:
        notify_zhor(flow=flow, module=bill, date=start_date, e=e)
        response = json.dumps([{"Response": "Error", "ERROR": "Un problème s'est produit. Veuillez réenvoyer votre requête plus tard."}])
        custom_logger.info('[{"Response": "Error", "ERROR": "Un problème s\'est produit. Veuillez réenvoyer votre requête plus tard."}]')
    
    return HttpResponse(response, content_type='text/json')


class HistorySynchro(APIView):
    def post(self, request, bank):
        record_request(request)
        return process_history_request(request, bank, 'synchro')


class HistoryCreate(APIView):
    def post(self, request, bank):
        record_request(request)
        return process_history_request(request, bank, 'create')


class BillSynchro(APIView):
    def post(self, request, bill):
        record_request(request)
        return process_bill_request(request, bill, 'synchro')


class BillCreate(APIView):
    def post(self, request, bill):
        record_request(request)
        return process_bill_request(request, bill, 'create')


class Results(ProtectedResourceView, APIView):
    def get(self, request):
        record_request(request)
        customfile = f'{path}/scrafi_project/Logs/django/custom/custom.log'
        custom_logger = setup_logger(f'custom_logger', customfile)
        job_id = request.query_params['job_id']
        try:
            job = Job.fetch(job_id, connection=redis)
        except NoSuchJobError:
            response = json.dumps({"Response": "Error", "ERROR": "Ce job ID n'existe pas."})
            custom_logger.info('{"Response": "Error", "ERROR": "Ce job ID n\'existe pas."}')
            return HttpResponse(response, content_type='text/json')
        else:
            if job in FailedJobRegistry(name='scrafi', connection=redis):
                response = json.dumps({"Response": "Error", "ERROR": "Un problème s'est produit. Veuillez réenvoyer votre requête plus tard."})
                custom_logger.info('{"Response": "Error", "ERROR": "Un problème s\'est produit. Veuillez réenvoyer votre requête plus tard."}')
                return HttpResponse(response, content_type='text/json')      
            else:          
                response = json.dumps(job.result, indent=4, ensure_ascii=False).encode('utf8')
                custom_logger.info('Sending Resultls')
                return HttpResponse(response, content_type='text/json')



class Confirmation(APIView):
    def get(self, request):
        record_request(request)
        customfile = f'{path}/scrafi_project/Logs/django/custom/custom.log'
        custom_logger = setup_logger(f'custom_logger', customfile)
        job_id = request.query_params['job_id']
        try:
            job = Job.fetch(job_id, connection=redis)
        except NoSuchJobError:
            response = json.dumps({"Response": "Error", "ERROR": "Ce job ID n'existe pas."})
            custom_logger.info('{"Response": "Error", "ERROR": "Ce job ID n\'existe pas."}')
            return HttpResponse(response, content_type='text/json')
        else:
            response = json.dumps({"Response": "OK"})
            custom_logger.info('{"Response": "OK"}')
            job.delete(delete_dependents=True)
            return HttpResponse(response, content_type='text/json')

            

def other_paths(request):
    otherfile = f'{path}/scrafi_project/Logs/other_requests/other.log'
    other_logger = setup_logger(f'other_logger', otherfile)
    dilog = {}
    log = ''
    
    ip = request.META.get('HTTP_X_FORWARDED_FOR')
    rmt_addr = request.META.get('REMOTE_ADDR')
    if ip:
        dilog['IP'] = ip
    else:
        dilog['Remote address'] = rmt_addr

    if request.META.get('HTTP_REFERER'):
        dilog['Referer'] = request.META.get('HTTP_REFERER')
        
    dilog['Headers'] = request.headers
    dilog['Method'] = request.method
    dilog['Path'] = 'http://159.65.95.248:8000' + request.path_info
    dilog['Server protocol'] = request.META['SERVER_PROTOCOL']

    if request.COOKIES:
        dilog['Cookies'] = request.COOKIES
        
    if request.method == 'POST':
        dilog['Data'] = request.POST.dict()
    elif request.method == 'GET':
        dilog['Data'] = request.GET.dict()
    
    for key, value in dilog.items():
        log += f"\n     {key} : {value}"
    
    log += "\n"
    other_logger.info(log)
    return HttpResponseForbidden('<!doctype html>\n<html lang="en">\n\n<head>\n<title>403 Forbidden</title>\n</head>\n\n<body>\n<h1>403 Forbidden</h1>\n<p></p>\n</body>\n\n</html>')