import unittest

from iex.Client import Client

c = Client()  # call this once so we can re-use sessions


class ClientTest(unittest.TestCase):
    def test_get_price_list(self):
        prices = c.get_price(['aapl', 'fb', 'zzaa'])

        assert 'AAPL' in prices, 'AAPL not found'
        assert 'FB' in prices, 'FB not found'
        assert 'ZZAA' not in prices, 'ZZAA found'

    def test_get_price_single(self):
        prices = c.get_price('aapl')

        assert 'AAPL' in prices, 'AAPL not found'

    def test_get_name_list(self):
        names = c.get_name(['aapl', 'fb', 'zzaa'])

        assert 'AAPL' in names, 'AAPL not found'
        assert 'FB' in names, 'FB not found'
        assert 'ZZAA' not in names, 'ZZAA found'

    def test_get_name(self):
        names = c.get_name('aapl')

        assert 'AAPL' in names, 'AAPL not found'

    def test_get_news_list(self):
        news = c.get_news(['aapl', 'fb', 'zzaa'])

        assert len(news) > 0, 'Did not find any news'

if __name__ == '__main__':
    unittest.main()