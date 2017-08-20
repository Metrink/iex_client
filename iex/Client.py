import requests

from urllib.parse import quote_plus

_BASE_URL = 'https://api.iextrading.com/1.0'


class Client(object):
    def __init__(self):
        self.session = requests.Session()  # setup a session for reuse
        res = self.session.get(_BASE_URL + '/ref-data/symbols?filter=symbol,name')

        if res.status_code != 200:
            raise requests.RequestException(kwargs={'response': res})

        # save off all the symbols the exchange knows about so we can reference later
        self.symbols = {x['symbol']: x['name'] for x in res.json()}

    def get_price(self, stocks):
        """
        Gets the price of the last trade of a stock or list of stocks.
        :param stocks: a single stock or list of stocks to fetch
        :return: dict with uppercase symbols and prices, any unknown symbols are discarded
        """
        if not isinstance(stocks, list):
            stocks = [stocks]  # create a list

        # filter and quote the list
        stocks = [quote_plus(s) for s in filter(lambda s: s in self.symbols, [str(s).upper() for s in stocks])]

        if len(stocks) == 0:
            return {}

        # make the request, getting only symbol and price
        res = self.session.get(_BASE_URL + '/tops/last?symbols=%s&filter=symbol,price'%','.join(stocks))

        return {x['symbol']: x['price'] for x in res.json()}


