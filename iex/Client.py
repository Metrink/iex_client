import requests

from urllib.parse import quote_plus

from iex.News import News

_BASE_URL = 'https://api.iextrading.com/1.0'


class Client(object):
    def __init__(self):
        self.session = requests.Session()  # setup a session for reuse
        res = self.session.get(_BASE_URL + '/ref-data/symbols?filter=symbol,name')

        if res.status_code != 200:
            raise requests.RequestException(kwargs={'response': res})

        # save off all the symbols the exchange knows about so we can reference later
        self.symbols = {x['symbol']: x['name'] for x in res.json()}

    def _fix_symbols(self, symbols):
        if not isinstance(symbols, list):
            symbols = [symbols]

        return list(filter(lambda s: s in self.symbols, [str(s).upper() for s in symbols]))

    def get_name(self, symbols):
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

    def get_price(self, symbols):
        """
        Gets the price of the last trade of a stock or list of stocks.
        :param symbols: a single stock or list of stocks to fetch
        :return: dict with uppercase symbols and prices, any unknown symbols are discarded
        """
        # quote the list
        symbols = [quote_plus(s) for s in self._fix_symbols(symbols)]

        if len(symbols) == 0:
            return {}

        # make the request, getting only symbol and price
        res = self.session.get(_BASE_URL + '/tops/last?symbols=%s&filter=symbol,price' %','.join(symbols))

        return {x['symbol']: x['price'] for x in res.json()}

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


