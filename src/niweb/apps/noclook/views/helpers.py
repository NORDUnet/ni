from django.utils.http import urlencode

class Table(object):
    def __init__(self, *args):
        self.headers = args[:]
        self.rows = []
        self.filters = []

    def add_row(self, row):
        self.rows.append(row)

    def add_filter(self, badge, name, param, params):
        self.filters.append(create_filter(badge, name, param, params))

    def __repr__(self):
        s = u'''
            {header}
            {row}
            {filters}
            {omitted} rows omitted
            '''
        row = ''
        filters = ''
        omitted = 0
        if self.rows:
            row = self.rows[0]
            omitted = len(self.rows) - 1
        if self.filters:
            filters = self.filters
        return s.format(header=self.headers, row=row, filters=filters, omitted=omitted)

    def __str__(self):
        return self.__repr__()


class TableRow(object):
    def __init__(self, *args):
        self.cols = args[:]


def create_filter(badge, name, param, params):
    """
        params should be a QueryDict e.g. request.GET.copy()
    """
    # handle show/hide
    active = param in params
    if 'hide' in param:
        active = not active

    if param in params:
        del params[param]
    else:
        params[param] = ''
    link = "?{}".format(params.urlencode())
    return (badge, name, link, active)

    def __repr__(self):
        return u'{!s}'.format(self.cols)

    def __str__(self):
        return self.__repr__()
