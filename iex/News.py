from dateutil import parser


class News(object):
    @staticmethod
    def from_dict(data):
        ret = News()

        ret.date_time = parser.parse(data['datetime'])
        ret.headline = data['headline']
        ret.source = data['source']
        ret.url = data['url']
        ret.summary = data['summary']
        ret.symbols = set(filter(lambda s: len(s) < 6 and s.upper() == s, data['related'].split(',')))

        return ret

    def __str__(self):
        return self.headline

    def __hash__(self):
        return hash(self.date_time.__hash__() + self.source.__hash__())

    def __eq__(self, other):
        return \
            self.date_time == other.date_time and \
            self.headline == other.headline and \
            self.source == other.source and \
            self.url == other.url and \
            self.summary == other.summary and \
            self.symbols == other.symbols

    def headline_link(self):
        return '<a href="%s">%s</a>' % (self.url, self.headline)