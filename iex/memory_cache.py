

class MemoryCache(object):
    def __init__(self):
        self.cache = dict()

    def set(self, key, value, time=0):
        self.cache[key] = value

    def get(self, key):
        return self.cache[key] if key in self.cache else None