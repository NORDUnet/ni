from math import ceil

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


def get_bool(querydict, key, default=False):
    return str(querydict.get(key, str(default))).lower() == 'true'



def create_filter(badge, name, param, params):
    """
    Creates a toggle link that switches param between 'true' and 'false'.

    :param badge: Badge class (for CSS)
    :param name: Display name
    :param param: Query param to toggle (e.g., 'hide_current')
    :param params: request.GET.copy()
    :return: (badge, name, link, active)
    """
    params = params.copy()  # Clone to avoid modifying the original

    current = str(params.get(param, 'false')).lower()

    active = current == 'true'
    # Toggle the value
    params[param] = 'false' if active else 'true'

    link = "?{}".format(params.urlencode())
    return badge, name, link, active

def create_filter_(badge, name, param, params):
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



class CustomPaginator:
    def __init__(self, object_list, per_page, search_query = ''):
        """
        Custom paginator that works for any iterable or list-like object.

        :param object_list: List or queryset to paginate
        :param per_page: Number of objects per page
        """
        self.object_list = list(object_list)
        self.search_query = search_query
        self.per_page = per_page
        self.total_objects = len(object_list)
        self.total_pages = ceil(self.total_objects / per_page)

    def get_page(self, page_number):
        """
        Returns the objects for the requested page number.

        :param page_number: Page number (1-based index)
        :return: A Page object with the items for the page
        """
        if page_number < 1:
            page_number = 1
        if page_number > self.total_pages:
            page_number = self.total_pages

        start = (page_number - 1) * self.per_page
        end = start + self.per_page

        return CustomPage(self.object_list[start:end], page_number, self)

    @property
    def num_pages(self):
        return self.total_pages


class CustomPage:
    def __init__(self, object_list, number, paginator):
        """
        Custom Page object that holds paginated data.

        :param object_list: List of objects for the current page
        :param number: The current page number
        :param paginator: The paginator instance
        """
        self.object_list = object_list
        self.number = number
        self.paginator = paginator


    def has_next(self):
        return self.number < self.paginator.total_pages


    def has_previous(self):
        return self.number > 1


    def next_page_number(self):
        return self.number + 1 if self.has_next() else None


    def previous_page_number(self):
        return self.number - 1 if self.has_previous() else None