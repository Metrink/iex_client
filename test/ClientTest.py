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


if __name__ == '__main__':
    unittest.main()