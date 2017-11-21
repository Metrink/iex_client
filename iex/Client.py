import requests

from urllib.parse import quote_plus
from dateutil.parser import parse

from iex.News import News

_BASE_URL = 'https://api.iextrading.com/1.0'


class Client(object):
    def __init__(self, cache=None):
        self.cache = cache
        if cache is None:  # use memcache if none provided
            import memcache

            self.cache = memcache.Client(['127.0.0.1:11211'], debug=0)

        self.session = requests.Session()  # setup a session for reuse

        # try and get the symbols from the cache first
        self.symbols = self.cache.get('symbols')

        if self.symbols is None:
            res = self.session.get(_BASE_URL + '/ref-data/symbols?filter=symbol,name')

            if res.status_code != 200:
                raise requests.RequestException(response=res)

            # save off all the symbols the exchange knows about
            self.symbols = {x['symbol']: x['name'] for x in res.json()}

            # add the symbols to our cache for a day
            self.cache.set('symbols', self.symbols, 86400)

    def _fix_symbols(self, symbols):
        if not isinstance(symbols, list):
            symbols = [symbols]

        return set(filter(lambda s: s in self.symbols, [str(s).upper() for s in symbols]))

    @staticmethod
    def _add_pretty_numbers(arg):
        if not isinstance(arg, dict):
            raise ValueError('Arg must be a dictionary')

        ret = dict(arg)

        for k,v in arg.items():
            if isinstance(v, int):
                ret[k+'_s'] = "{:,}".format(v)
            elif isinstance(v, float):
                ret[k+'_s'] = "{:,.2f}".format(v)

        return ret

    def get_name(self, symbols):
        """
        Given a symbol(s), return the company name(s) if found
        :param symbols: the symbol(s) to look up
        :return: a dict containing symbol: name
        """
        return {s: self.symbols[s] for s in self._fix_symbols(symbols)}

    def find_symbol(self, arg):
        """
        Attempts to find a symbol given either a symbol, partial symbol, name or partial name.
        :param arg: the string to search for
        :return: a dictionary of symbol name combinations
        """
        arg = str(arg).lower()
        ret = {}

        for s,n in self.symbols.items():
            if arg in str(s).lower() or arg in str(n).lower():
                ret[s] = n

        return ret

    def get_symbols(self):
        ret = []

        for s,n in self.symbols.items():
            ret.append({'s': s, 'name': "%s - %s" % (s,n) })

        return ret

    def get_quote(self, symbols):
        """
        Gets a full quote for the stock or list of stocks.
        :param symbols: the symbol or list of symbols
        :return:
        """
        # quote the list
        symbols = [quote_plus(s) for s in self._fix_symbols(symbols)]

        if len(symbols) == 0:
            return {}

        # make the request
        res = self.session.get(_BASE_URL + '/stock/market/batch?symbols=%s&types=quote'%','.join(symbols))

        if res.status_code != 200:
            raise requests.RequestException(response=res)

        res = {k: v['quote'] for k,v in res.json().items()}

        return Client._add_pretty_numbers(res)  # add pretty numbers

    def get_news(self, symbols, num_stories=10):
        """
        Fetch news stories for each stock.
        :param symbols: the symbols to fetch stories for
        :param num_stories: number of stories to fetch [1,50]
        :return: a set of News objects which might be less than len(symbols) * num_stories
        """
        symbols = self._fix_symbols(symbols)
        ret = set()

        if len(symbols) == 0:
            return ret

        if num_stories > 50:
            num_stories = 50
        if num_stories < 1:
            num_stories = 1

        for symbol in symbols:
            res = self.session.get(_BASE_URL + '/stock/%s/news/last/%d' % (symbol, num_stories))

            for n in res.json():
                ret.add(News.from_dict(n))

        return ret

    def get_chart_data(self, symbol, range='1m'):
        """
        Return chart data used for plotting candlestick charts.
        :param symbol: the symbol to fetch data for
        :param range: one of 1m, 3m, 6m, 1y, 2y, 5y
        :return: an array of arrays with [date, low, open, close, high]
        """
        if range not in ('1m', '3m', '6m', '1y', '2y', '5y'):
            raise ValueError('Range error, must be one of: 1m, 3m, 6m, 1y, 2y, 5y')

        symbols = self._fix_symbols(symbol)

        if len(symbols) == 0:
            raise ValueError('Unknown symbol: ' + symbol)
        else:
            symbol = list(symbols)[0]

        res = self.session.get(_BASE_URL + '/stock/%s/chart/%s'%(symbol, range))

        if res.status_code != 200:
            raise requests.RequestException(response=res)

        ret = []

        for point in res.json():
            if 'm' in range:
                d = parse(point['date']).strftime("%m/%d")
            else:
                d = parse(point['date']).strftime("%m/%d/%Y")
            ret.append([d, point['low'], point['open'], point['close'], point['high']])

        return ret

    def get_financials(self, symbols):
        symbols = self._fix_symbols(symbols)

        if len(symbols) == 0:
            raise ValueError('Unknown symbol: ' + str(symbols))

        ret = dict()

        # make the requests
        for symbol in symbols:
            res = self.session.get(_BASE_URL + '/stock/%s/financials'%symbol)

            if res.status_code != 200:
                raise requests.RequestException(response=res)

            ret[symbol] = res.json()['financials']

        return ret



