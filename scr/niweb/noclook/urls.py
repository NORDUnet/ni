# This also imports the include function
from django.conf.urls.defaults import *

urlpatterns = patterns('niweb.noclook.views',
    (r'^$', 'index'),
    (r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/$', 'detail'),
    (r'^(?P<slug>[-\w]+)/$', 'list_by_type'),
)
