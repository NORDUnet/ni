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

def create_filter(badge,  name, param, parms):
    if param in parms:
        del parms[param]
        active = True
    else:
        parms[param] = ''
        active = False
    link = "?{}".format(urllib.urlencode(parms))
    return (badge, name, link, active)
