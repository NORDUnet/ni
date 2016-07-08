
class Table(object):
    def __init__(self, *args):
        self.headers = args[:]
        self.rows = []

    def add_row(self, row):
        self.rows.append(row)

    def __repr__(self):
        s = u'''
            {header}
            {row}
            {omitted} rows omitted
            '''
        row = ''
        omitted = 0
        if self.rows:
            row = self.rows[0]
            omitted = len(self.rows) - 1
        return s.format(header=self.headers, row=row, omitted=omitted)

    def __str__(self):
        return self.__repr__()


class TableRow(object):
    def __init__(self, *args):
        self.cols = args[:]

    def __repr__(self):
        return u'{!s}'.format(self.cols)

    def __str__(self):
        return self.__repr__()
