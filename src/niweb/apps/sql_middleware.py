from django.db import connection
from django.conf import settings
import os
from time import time


class SqlPrintingMiddleware(object):
    """
    Middleware which prints out a list of all SQL queries done
    for each view that is processed.  This is only useful for debugging.
    """
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        indentation = 2
        if len(connection.queries) > 0 and settings.DEBUG:
            fpath = request.path.replace('/', '-')
            with open(f'/app/log/sql-{fpath}-{time()}.log', 'w') as f:
                width = 80
                total_time = 0.0
                n = 0
                for query in connection.queries:
                    n += 1
                    nice_sql = query['sql'].replace('"', '').replace(',',', ')
                    sql = "[%s][ %s" % (query['time'], nice_sql)
                    total_time = total_time + float(query['time'])
                    while len(sql) > width-indentation:
                        print("%s%s" % (" "*indentation, sql[:width-indentation]), file=f)
                        sql = sql[width-indentation:]
                    print("%s%s\n" % (" "*indentation, sql), file=f)
                replace_tuple = (" "*indentation, str(total_time), n)
                print("%sTOTAL TIME: %s seconds for %d QUERIES" % replace_tuple, file=f)
        return response
