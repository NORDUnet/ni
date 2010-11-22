# This also imports the include function
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # Login / logout.
    (r'^login/$', 'django.contrib.auth.views.login'),
    (r'^logout/$', 'niweb.noclook.views.logout_page'),
)

urlpatterns += patterns('niweb.noclook.views',
    # NOCLook views
    (r'^$', 'index'),
    (r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/$', 'detail'),
    (r'^([-\w]+)/(?P<handle_id>\d+)/(?P<slug>[-\w]+)s/$',
        'list_by_master'),
    (r'^(?P<slug>[-\w]+)/$', 'list_by_type'),
)
