import requests
import json

_BASE_URL = 'https://api.iextrading.com/1.0'


class Client(object):
    def __init__(self):
        res = requests.get(_BASE_URL + '/ref-data/symbols?filter=symbol,name')

        if res.status_code != 200:
            raise requests.RequestException(kwargs={'response': res})

        self.symbols = {x['symbol']: x['name'] for x in res.json()}




