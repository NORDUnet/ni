
class Table(object):
    def __init__(self, *args):
        self.headers = args[:]
        self.rows = []

    def add_row(self, row):
        self.rows.append(row)


class TableRow(object):
    def __init__(self, *args):
        self.cols = args[:]
