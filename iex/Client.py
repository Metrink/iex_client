import requests
import logging
import sys

from os.path import abspath

from urllib.parse import quote_plus
from dateutil.parser import parse
from iex.memory_cache import MemoryCache
from iex.News import News
from json import load


class Client(object):
    def __init__(self, is_test=False, token_file='token.json', cache=None):
        self.cache = cache
        self.is_test = is_test

        if is_test:
            self.base_url = 'https://sandbox.iexapis.com/stable'
        else:
            self.base_url = 'https://cloud.iexapis.com/stable'

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

        # load-up the tokens
        try:
            with open(token_file, 'r') as fp:
                tokens = load(fp)
        except Exception as e:
            self.logger.error('Error opening token file {}: {}'.format(abspath(token_file), e))
            raise ValueError(e)

        if is_test:
            self.token = tokens['test_secret']
        else:
            self.token = tokens['secret']

        # try and get the symbols from the cache first
        self.symbols = self.cache.get('symbols')

        if self.symbols is None:
            res = self.session.get(self.base_url + '/ref-data/symbols?filter=symbol,name&token={}'.format(self.token))

            if res.status_code != 200:
                self.logger.warning("Non-200 response code ({}) getting symbols: {}".format(res.status_code, res.text))
                raise requests.RequestException(response=res)

            # save off all the symbols the exchange knows about
            self.symbols = {x['symbol']: x['name'] for x in res.json()}

            # add the symbols to our cache for a day
            self.cache.set('symbols', self.symbols, 86400)

    def _make_request(self, url, params, method='GET', use_cache=True):
        """
        Make a request adding in the proper base URL and access token
        :param url:
        :param params:
        :param method:
        :return:
        """
        request_url = self.base_url + url
        cache_url = request_url + str(params).replace(' ', '')

        if use_cache:  # check if it's in the cache
            ret = self.cache.get(cache_url)

            if ret is not None:
                return ret

        if method == 'GET':
            res = self.session.get(request_url, params={**params, **{'token': self.token}})
        elif method == 'DELETE':
            res = self.session.delete(request_url, params={**params, **{'token': self.token}})
        else:
            self.logger.error("Unknown method for {}: {}".format(request_url, method))
            raise requests.RequestException("Unknown method for {}: {}".format(request_url, method))

        if res.status_code != 200:
            print("REQUEST: {}".format(res.request.url))
            self.logger.error("Error requesting {}: {} - {}".format(request_url, res.status_code, res.text))
            raise requests.RequestException(response=res)

        self.logger.info("Messages used: {}".format(res.headers['iexcloud-messages-used']))

        res_json = res.json()

        if use_cache:
            self.cache.set(cache_url, res_json, time=86400)  # cache for a day

        return res_json

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

        for s, n in self.symbols.items():
            if arg in str(s).lower() or arg in str(n).lower():
                ret[s] = n

        if len(ret) == 0:
            self.logger.warning("Symbol %s not found", arg)

        return ret

    def get_symbols(self):
        ret = []

        for s,n in self.symbols.items():
            ret.append({'s': s, 'name': "%s - %s" % (s,n) })

        return ret

    def get_company_info(self, symbols):
        """
        Gets information about the company.
        :param symbols: the symbol or list of symbols
        :return:
        """
        symbols = self._fix_symbols(symbols)

        if len(symbols) == 0:
            return {}

        # make the request
        res = self._make_request('/stock/market/batch', {'symbols': ','.join(symbols), 'types': 'company'})

        # pull out the company
        ret = {k: v['company'] for k, v in res.items()}

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
        res = self._make_request('/stock/market/batch', {'symbols': ','.join(symbols), 'types': 'quote'}, use_cache=False)

        return {k: Client._add_pretty_numbers(v['quote']) for k, v in res.items()}

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

        # limit the number of stories to between 1 & 50
        if num_stories > 50:
            num_stories = 50
        if num_stories < 1:
            num_stories = 1

        for symbol in symbols:
            # make the request
            res = self._make_request('/stock/{}/news/last/{}'.format(symbol, num_stories), {})

            for n in res:
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

        # make the request
        res = self._make_request('/stock/{}/chart/{}'.format(symbol, range), {})

        ret = []

        for point in res:
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

        # make the request
        res = self._make_request('/stock/market/batch', {'symbols': ','.join(symbols), 'types': 'financials'})

        ret = dict()

        # flatten out what's returned
        for stock,financials in res.items():
            ret[stock] = []

            for report in financials['financials']['financials']:
                ret[stock].append(Client._add_pretty_numbers(report))

            ret[stock] = sorted(filter(lambda x: x['reportDate'] is not None, ret[stock]), key=lambda x: x['reportDate'])

        return ret




