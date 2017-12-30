import requests
import logging
import sys

from urllib.parse import quote_plus
from dateutil.parser import parse
from iex.memory_cache import MemoryCache
from iex.News import News

_BASE_URL = 'https://api.iextrading.com/1.0'


class Client(object):
    def __init__(self, cache=None):
        self.cache = cache

        # setup logging
        self.logger = logging.getLogger('iex-client')

        if len(self.logger.handlers) == 0:
            sh = logging.StreamHandler(sys.stderr)
            sh.setLevel(logging.DEBUG)
            sh.setFormatter(logging.Formatter('[%(asctime)s %(levelname)s] %(filename)s %(lineno)s:\t%(message)s'))
            self.logger.setLevel(logging.DEBUG)
            self.logger.addHandler(sh)

        if cache is None:  # use memcached if none provided
            try:
                import memcache

                self.cache = memcache.Client(['127.0.0.1:11211'], debug=0)
            except ImportError as e:
                self.logger.warning("Importing memcache failed: %s", str(e), exc_info=1)
                self.cache = MemoryCache()

        self.session = requests.Session()  # setup a session for reuse

        # try and get the symbols from the cache first
        self.symbols = self.cache.get('symbols')

        if self.symbols is None:
            res = self.session.get(_BASE_URL + '/ref-data/symbols?filter=symbol,name')

            if res.status_code != 200:
                self.logger.warning("Non-200 response code getting symbols: %d", res.status_code)
                raise requests.RequestException(response=res)

            # save off all the symbols the exchange knows about
            self.symbols = {x['symbol']: x['name'] for x in res.json()}

            # add the symbols to our cache for a day
            self.cache.set('symbols', self.symbols, 86400)

    def _fix_symbols(self, symbols):
        if isinstance(symbols, str):
            symbols = [quote_plus(symbols.upper())]

        # convert to uppercase, then filter anything not in the list, and map to the URL quoted version
        return set(map(lambda s: quote_plus(s), filter(lambda s: s in self.symbols, [str(s).upper() for s in symbols])))

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

        self.logger.warning("Symbol %s not found", arg)

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
        symbols = self._fix_symbols(symbols)

        if len(symbols) == 0:
            return {}

        # make the request
        url = _BASE_URL + '/stock/market/batch?symbols=%s&types=quote'%','.join(symbols)
        res = self.session.get(url)

        if res.status_code != 200:
            self.logger.warning("Non-200 status code from %s: %d", url, res.status_code)
            raise requests.RequestException(response=res)

        return {k: Client._add_pretty_numbers(v['quote']) for k,v in res.json().items()}

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
            url = _BASE_URL + '/stock/%s/news/last/%d' % (symbol, num_stories)
            res_json = self.cache.get(url)

            if res_json is None:
                res = self.session.get(url)

                if res.status_code != 200:
                    self.logger.warning("Non-200 status code from %s: %d", url, res.status_code)
                    continue

                res_json = res.json()

                self.cache.set(url, res_json, time=86400)  # cache for a day

            for n in res_json:
                ret.add(News.from_dict(n))

        return ret

    def get_chart_data(self, symbol, range='1m'):
        """
        Return chart data used for plotting candlestick charts.
        :param symbol: the symbol to fetch data for
        :param range: one of 1m, 3m, 6m, 1y, 2y, 5y
        :return: an array of arrays with [date, low, open, close, high]
        """
        if range not in ('1d', '1m', '3m', '6m', 'ytd', '1y', '2y', '5y'):
            raise ValueError('Range error, must be one of: 1d, 1m, 3m, 6m, ytd, 1y, 2y, 5y')

        symbols = self._fix_symbols(symbol)

        if len(symbols) == 0:
            raise ValueError('Unknown symbol: ' + symbol)
        else:
            symbol = list(symbols)[0]

        url = _BASE_URL + '/stock/%s/chart/%s'%(symbol, range)

        ret = self.cache.get(url)

        if ret is not None:
            return ret

        res = self.session.get(url)

        if res.status_code != 200:
            self.logger.warning("Non-200 status from %s: %d", url, res.status_code)
            raise requests.RequestException(response=res)

        ret = []

        for point in res.json():
            if '1d' == range:
                d = point['label']
            elif 'm' in range:
                d = parse(point['date']).strftime("%m/%d")
            else:
                d = parse(point['date']).strftime("%m/%d/%Y")

            if '1d' == range:
                if point['minute'].endswith('0') or point['minute'].endswith('5'):
                    ret.append([d, point['average']])
            else:
                avg = (point['open'] + point['close'] + point['high'] + point['low']) / 4.0
                ret.append([d, avg, point['open'], point['close'], point['high'], point['low']])

        self.cache.set(url, ret, time=86400)  # cache for a day

        return ret

    def get_financials(self, symbols):
        """
        Return financialls data for a symbol.
        :param symbols:
        :return:
        """
        symbols = self._fix_symbols(symbols)

        if len(symbols) == 0:
            raise ValueError('Unknown symbol: ' + str(symbols))

        url = _BASE_URL + '/stock/market/batch?symbols=%s&types=financials'%','.join(symbols)

        ret = self.cache.get(url)

        if ret is not None:
            return ret

        # make the request
        res = self.session.get(url)

        if res.status_code != 200:
            self.logger.warning("Non-200 status from %s: %d", url, res.status_code)
            raise requests.RequestException(response=res)

        ret = dict()

        # flatten out what's returned
        for stock,financials in res.json().items():
            ret[stock] = []

            for report in financials['financials']['financials']:
                ret[stock].append(Client._add_pretty_numbers(report))

            ret[stock] = sorted(ret[stock], key=lambda x: x['reportDate'])

        self.cache.set(url, ret, time=86400)  # cache for a day

        return ret




