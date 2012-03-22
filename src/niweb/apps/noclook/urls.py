# This also imports the include function
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # Login / logout.
    (r'^login/$', 'django.contrib.auth.views.login'),
    (r'^logout/$', 'niweb.apps.noclook.views.logout_page'),
)

urlpatterns += patterns('niweb.apps.noclook.edit_views',
    # Manipulation views
    #(r'^new/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/relationship/$',
    #                                                     'new_relationship'),
    #(r'^edit/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/relationship/(?P<rel_id>\d+)/$',
    #                                                     'edit_relationship'),
    #(r'^save/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/relationship/(?P<rel_id>\d+)/$',
    #                                                     'save_relationship'),
    #(r'^delete/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/relationship/(?P<rel_id>\d+)/$',
    #                                                     'delete_relationship'),
    (r'^new/$', 'new_node'),
    (r'^new/(?P<slug>[-\w]+)/$', 'new_node'),
    (r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/edit$', 'edit_node'),
    (r'^formdata/(?P<slug>[-\w]+)/$', 'get_node_type'),
    (r'^formdata/(?P<node_id>\d+)/children$', 'get_children'),
    #(r'^save/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/$', 'save_node'),
    #(r'^delete/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/$', 'delete_node'),
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
    (r'^host/(?P<handle_id>\d+)/$', 'host_detail'),
    (r'^host-service/(?P<handle_id>\d+)/$', 'host_service_detail'),
    (r'^host-provider/(?P<handle_id>\d+)/$', 'host_provider_detail'),
    (r'^host-user/(?P<handle_id>\d+)/$', 'host_user_detail'),
    (r'^site/(?P<handle_id>\d+)/$', 'site_detail'),
    (r'^rack/(?P<handle_id>\d+)/$', 'rack_detail'),
    (r'^site-owner/(?P<handle_id>\d+)/$', 'site_owner_detail'),
    # Visualize views
    (r'^visualize/(?P<node_id>\d+)\.json$', 'visualize_json'),
    (r'^visualize/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/maximized/$',
                                                         'visualize_maximize'),
    (r'^visualize/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/$', 'visualize'),
    # Google maps views
    (r'^gmaps/(?P<slug>[-\w]+)\.json$', 'gmaps_json'),
    (r'^gmaps/(?P<slug>[-\w]+)/$', 'gmaps'),
    # Get all
    (r'^getall/(?P<slug>[-\w]+)/(result.)?(?P<form>(csv|json)?)$', 'find_all'),
    # Find all
    (r'^findall/(?P<value>.*)/(result.)?(?P<form>(csv)?)$', 'find_all'),
    (r'^findall/(?P<key>[-\w]+)/(?P<value>.*)/(result.)?(?P<form>(csv)?)$', 'find_all'),
    # Find in
    (r'^findin/(?P<slug>[-\w]+)/(result.)?(?P<form>(csv)?)$', 'find_all'),
    (r'^findin/(?P<slug>[-\w]+)/(?P<key>[-\w]+)/(?P<value>.*)/(result.)?(?P<form>(csv)?)$', 'find_all'),
    (r'^findin/(?P<slug>[-\w]+)/(?P<value>.*)/(result.)?(?P<form>(csv)?)$', 'find_all'),
    # Search
    (r'^search/$', 'search'),
    (r'^search/autocomplete$', 'search_autocomplete'),
    (r'^search/(?P<value>.*)/(result.)?(?P<form>(csv)?)$', 'search'),
    # List views
    (r'^peering-partner/$', 'list_peering_partners'),
    (r'^host/$', 'list_hosts'),
    (r'^site/$', 'list_sites'),
    (r'^(?P<slug>[-\w]+)/$', 'list_by_type'),
    # Generic view
    (r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/$', 'generic_detail'),
)
