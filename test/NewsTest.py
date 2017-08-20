import unittest

from iex.News import News

n = News.from_dict({
    "datetime": "2017-08-19T09:00:00-04:00",
    "headline": "Retirement Strategy",
    "source": "SeekingAlpha",
    "url": "https://api.iextrading.com/1.0/stock/aapl/article/8868495060169889",
    "summary": "I do not want to sound like a broken record, but …",
    "related": "AAPL,BAC,Computer Hardware,CON31167138,ED,F,NASDAQ01,Computing and Information Technology"
})


class NewsTest(unittest.TestCase):
    def test_from_dict(self):
        assert len(n.symbols) == 4, 'Too many symbols found'
        assert 'AAPL' in n.symbols, 'AAPL not found in symbols'
        assert 'BAC' in n.symbols, 'AAPL not found in symbols'
        assert 'ED' in n.symbols, 'AAPL not found in symbols'
        assert 'F' in n.symbols, 'AAPL not found in symbols'

    def test_headline_link(self):
        link = n.headline_link()

        assert 'href' in link, 'No href found'
        assert n.url in link, 'URL not found'
        assert n.headline in link, 'Headline not found'