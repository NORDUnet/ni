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
    # Detailed views
    (r'^router/(?P<handle_id>\d+)/$', 'router_detail'),
    (r'^pic/(?P<handle_id>\d+)/$', 'pic_detail'),
    (r'^peering-partner/(?P<handle_id>\d+)/$',
                                        'peering_partner_detail'),
    (r'^ip-service/(?P<handle_id>\d+)/$', 'ip_service_detail'),
    (r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/$', 'generic_detail'),
    # List views
    (r'^([-\w]+)/(?P<handle_id>\d+)/(?P<slug>[-\w]+)s/$',
        'list_by_master'),
    (r'^(?P<slug>[-\w]+)/$', 'list_by_type'),
    # Visualize views
    (r'^visualize/(?P<slug>[-\w]+)/(?P<handle_id>\d+)\.json$',
                                                    'visualize_json'),
    (r'^visualize/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/$',
                                                        'visualize'),
)
