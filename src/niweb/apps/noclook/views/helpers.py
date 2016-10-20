import urllib

class Table(object):
    def __init__(self, *args):
        self.headers = args[:]
        self.rows = []
        self.filters = []
    def add_row(self, row):
        self.rows.append(row)
    def add_filter(self, badge, name, param, params):
        self.filters.append(create_filter(badge, name, param, params))



class TableRow(object):
    def __init__(self, *args):
        self.cols = args[:]

def create_filter(badge,  name, param, params):
    # handle show/hide
    active = param in params
    if 'hide' in param:
        active = not active

    if param in params:
        del params[param]
    else:
        params[param] = ''
    link = "?{}".format(urllib.urlencode(params))
    return (badge, name, link, active)
