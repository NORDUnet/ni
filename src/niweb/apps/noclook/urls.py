# This also imports the include function
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # Login / logout.
    #(r'^login/$', 'django.contrib.auth.views.login'),
    #(r'^logout/$', 'niweb.apps.noclook.views.logout_page'),
)

urlpatterns += patterns('niweb.apps.noclook.views',
    # NOCLook views
    (r'^$', 'index'),
    # Detailed views
    (r'^router/(?P<handle_id>\d+)/$', 'router_detail'),
    (r'^pic/(?P<handle_id>\d+)/$', 'pic_detail'),
    (r'^peering-partner/(?P<handle_id>\d+)/$',
                                        'peering_partner_detail'),
    (r'^ip-service/(?P<handle_id>\d+)/$', 'ip_service_detail'),
    (r'^optical-node/(?P<handle_id>\d+)/$', 'optical_node_detail'),
    (r'^cable/(?P<handle_id>\d+)/$', 'cable_detail'),
    # Visualize views
    (r'^visualize/(?P<slug>[-\w]+)/(?P<handle_id>\d+)\.json$', 
                                                         'visualize_json'),
    (r'^visualize/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/$', 'visualize'),
    # Manipulation views
    (r'^new/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/relationship/$', 
                                                         'new_relationship'),
    (r'^edit/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/relationship/(?P<rel_id>\d+)/$', 
                                                         'edit_relationship'),
    (r'^save/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/relationship/(?P<rel_id>\d+)/$',
                                                         'save_relationship'),    
    (r'^delete/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/relationship/(?P<rel_id>\d+)/$',
                                                         'delete_relationship'),
    (r'^new/(?P<slug>[-\w]+)/$', 'new_node'),
    (r'^edit/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/$', 'edit_node'),
    (r'^save/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/$', 'save_node'),
    (r'^delete/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/$', 'delete_node'),
    # Find all
    (r'^findall/(?P<key>[-\w]+)/(?P<value>[-\w]+)/$', 'search'),
    (r'^findall/(?P<value>[-\w]+)/$', 'search'),
    (r'^findall/$', 'search'),
    # Search
    (r'^search/(?P<slug>[-\w]+)/(?P<key>[-\w]+)/(?P<value>[-\w]+)/$', 'search'),
    (r'^search/(?P<slug>[-\w]+)/(?P<value>[-\w]+)/$', 'search'),
    (r'^search/$', 'search'),
    # List views
    (r'^([-\w]+)/(?P<handle_id>\d+)/(?P<slug>[-\w]+)s/$',
        'list_by_master'),
    (r'^peering-partner/$', 'list_peering_partners'),
    (r'^(?P<slug>[-\w]+)/$', 'list_by_type'),
    # Generic view
    (r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/$', 'generic_detail'),
)
