from hashlib import sha256


def create_signature(body):
    method = 'post'
    url = '/api/Webhook/IneoReceiver'
    key = 'xgBLyGGr5WDU52Hs56zBF8i2CZYWp7342V78Y54djeG7r2VprHhzN28p8pP4ps2r'

    sign = key + '+' + method + '+' + url + '+' + str(body)
    hashValue = sha256(sign.encode('utf-8')).hexdigest()
    signature = '$5$' + hashValue
    return signature
