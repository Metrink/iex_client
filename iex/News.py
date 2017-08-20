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
        ret.symbols = list(filter(lambda s: len(s) < 6 and s.upper() == s, data['related'].split(',')))

        return ret

    def headline_link(self):
        return '<a href="%s">%s</a>' % (self.url, self.headline)