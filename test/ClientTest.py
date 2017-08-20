import unittest

from iex import client


class ClientTest(unittest.TestCase):
    def test__init__(self):
        c = client.Client()


if __name__ == '__main__':
    unittest.main()