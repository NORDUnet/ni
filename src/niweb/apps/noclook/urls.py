# This also imports the include function
from django.conf.urls import *

urlpatterns = patterns('',
    (r'^login/$', 'django.contrib.auth.views.login'),
)

urlpatterns += patterns('apps.noclook.views.other',
    (r'^$', 'index'),
    # Log out
    (r'^logout/$', 'logout_page'),
    # Visualize views
    (r'^visualize/(?P<handle_id>\d+)\.json$', 'visualize_json'),
    (r'^visualize/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/maximized/$', 'visualize_maximize'),
    (r'^visualize/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/$', 'visualize'),
    # Google maps views
    (r'^gmaps/(?P<slug>[-\w]+)\.json$', 'gmaps_json'),
    (r'^gmaps/(?P<slug>[-\w]+)/$', 'gmaps'),
    # Get all
    (r'^getall/(?P<slug>[-\w]+)/(result.)?(?P<form>(csv|json|xls)?)$', 'find_all'),
    # Find all
    (r'^findall/(?P<key>[-\w]+)/(?P<value>.*)/(result.)?(?P<form>(csv|json|xls)?)$', 'find_all'),
    (r'^findall/(?P<value>.*)/(result.)?(?P<form>(csv|json|xls)?)$', 'find_all'),
    # Find in
    (r'^findin/(?P<slug>[-\w]+)/(result.)?(?P<form>(csv|json|xls)?)$', 'find_all'),
    (r'^findin/(?P<slug>[-\w]+)/(?P<key>[-\w]+)/(?P<value>.*)/(result.)?(?P<form>(csv|json|xls)?)$', 'find_all'),
    (r'^findin/(?P<slug>[-\w]+)/(?P<value>.*)/(result.)?(?P<form>(csv|json|xls)?)$', 'find_all'),
    # Search
    (r'^search/$', 'search'),
    (r'^search/autocomplete$', 'search_autocomplete'),
    (r'^search/typeahead/ports$', 'search_port_typeahead'),
    (r'^search/(?P<value>.*)/(result.)?(?P<form>(csv|json|xls)?)$', 'search'),
    # QR lookup
    (r'^lu/(?P<name>[-\w]+)/$', 'qr_lookup'),
    # Hostname lookup
    (r'^ajax/hostname/$', 'ip_address_lookup'),
    # Table to CSV or Excel
    (r'^download/tabletofile/$', 'json_table_to_file'),
)

urlpatterns += patterns('apps.noclook.views.create',
    (r'^new/$', 'new_node'),
    (r'^new/(?P<slug>[-\w]+)/$', 'new_node'),
    (r'^new/(?P<slug>[-\w]+)/parent/(?P<parent_id>\d+)/$', 'new_node'),
    (r'^new/(?P<slug>[-\w]+)/name/(?P<name>[-\w]+)/$', 'new_node'),
    # Reserve IDs
    (r'^reserve-id/$', 'reserve_id_sequence'),
    (r'^reserve-id/(?P<slug>[-\w]+)/$', 'reserve_id_sequence'),
)

urlpatterns += patterns('apps.noclook.views.edit',
    (r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/edit$', 'edit_node'),
    (r'^host/(?P<handle_id>\d+)/edit/convert-to/(?P<slug>[-\w]+)/$', 'convert_host'),
    (r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/delete$', 'delete_node'),
    (r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/relationship/(?P<rel_id>\d+)/delete$', 'delete_relationship'),
    (r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/relationship/(?P<rel_id>\d+)/update$', 'update_relationship'),
    (r'^formdata/(?P<slug>[-\w]+)/$', 'get_node_type'),
    (r'^formdata/unlocated/(?P<slug>[-\w]+)/$', 'get_unlocated_node_type'),
    (r'^formdata/(?P<handle_id>\d+)/children/$', 'get_child_form_data'),
    (r'^formdata/(?P<handle_id>\d+)/children/(?P<slug>[-\w]+)/$', 'get_child_form_data'),
    (r'^formdata/(?P<slug>[-\w]+)/(?P<key>[-\w]+)/(?P<value>[-\w ]+)/$', 'get_subtype_form_data'),
)

from .views.import_nodes import ImportNodesView, ExportNodesView
urlpatterns += [
    url(r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/import$',  ImportNodesView.as_view(), name='import_nodes'),
    url(r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/export$',  ExportNodesView.as_view(), name='import_nodes'),
]

urlpatterns += patterns('apps.noclook.views.report',
    (r'^reports/hosts/$', 'host_reports'),
    (r'^reports/hosts/host-users/$', 'host_users'),
    (r'^reports/hosts/host-users/(?P<host_user_name>[-\w]+)/$', 'host_users'),
    (r'^reports/hosts/host-security-class/$', 'host_security_class'),
    (r'^reports/hosts/host-security-class/(?P<status>[-\w]+)/$', 'host_security_class'),
    (r'^reports/hosts/host-services/$', 'host_services'),
    (r'^reports/hosts/host-services/(?P<status>[-\w]+)/$', 'host_services'),
    (r'^reports/unique-ids/(?P<organisation>[-\w]+)\.(?P<file_format>xls|csv)$', 'download_unique_ids'),
    (r'^reports/unique-ids/(?P<organisation>[-\w]+)/$', 'unique_ids'),
    (r'^reports/unique-ids/$', 'unique_ids'),
)

urlpatterns += patterns('apps.noclook.views.list',
    (r'^peering-partner/$', 'list_peering_partners'),
    (r'^host/$', 'list_hosts'),
    (r'^site/$', 'list_sites'),
    (r'^service/(?P<service_class>(DWDM|Ethernet|External|IAAS|IP|Internal|MPLS|Hosting|SAAS)?)/$',
     'list_services'),
    (r'^service/$', 'list_services'),
    (r'^optical-path/$', 'list_optical_paths'),
    (r'^optical-multiplex-section/$', 'list_optical_multiplex_section'),
    (r'^optical-link/$', 'list_optical_links'),
    (r'^optical-node/$', 'list_optical_nodes'),
    (r'^router/$', 'list_routers'),
    (r'^rack/$', 'list_racks'),
    (r'^odf/$', 'list_odfs'),
    (r'^cable/$', 'list_cables'),
    (r'^switch/$', 'list_switches'),
    # Generic list
    (r'^(?P<slug>[-\w]+)/$', 'list_by_type'),
)

urlpatterns += patterns('apps.noclook.views.detail',
    (r'^router/(?P<handle_id>\d+)/$', 'router_detail'),
    (r'^peering-partner/(?P<handle_id>\d+)/$', 'peering_partner_detail'),
    (r'^peering-group/(?P<handle_id>\d+)/$', 'peering_group_detail'),
    (r'^optical-node/(?P<handle_id>\d+)/$', 'optical_node_detail'),
    (r'^cable/(?P<handle_id>\d+)/$', 'cable_detail'),
    (r'^host/(?P<handle_id>\d+)/$', 'host_detail'),
    (r'^host-service/(?P<handle_id>\d+)/$', 'host_service_detail'),
    (r'^host-provider/(?P<handle_id>\d+)/$', 'host_provider_detail'),
    (r'^host-user/(?P<handle_id>\d+)/$', 'host_user_detail'),
    (r'^odf/(?P<handle_id>\d+)/$', 'odf_detail'),
    (r'^optical-filter/(?P<handle_id>\d+)/$', 'optical_filter_detail'),
    (r'^port/(?P<handle_id>\d+)/$', 'port_detail'),
    (r'^site/(?P<handle_id>\d+)/$', 'site_detail'),
    (r'^rack/(?P<handle_id>\d+)/$', 'rack_detail'),
    (r'^site-owner/(?P<handle_id>\d+)/$', 'site_owner_detail'),
    (r'^service/(?P<handle_id>\d+)/$', 'service_detail'),
    (r'^optical-link/(?P<handle_id>\d+)/$', 'optical_link_detail'),
    (r'^optical-path/(?P<handle_id>\d+)/$', 'optical_path_detail'),
    (r'^end-user/(?P<handle_id>\d+)/$', 'end_user_detail'),
    (r'^customer/(?P<handle_id>\d+)/$', 'customer_detail'),
    (r'^provider/(?P<handle_id>\d+)/$', 'provider_detail'),
    (r'^unit/(?P<handle_id>\d+)/$', 'unit_detail'),
    (r'^external-equipment/(?P<handle_id>\d+)/$', 'external_equipment_detail'),
    (r'^optical-multiplex-section/(?P<handle_id>\d+)/$', 'optical_multiplex_section_detail'),
    (r'^firewall/(?P<handle_id>\d+)/$', 'firewall_detail'),
    (r'^switch/(?P<handle_id>\d+)/$', 'switch_detail'),
    (r'^pdu/(?P<handle_id>\d+)/$', 'pdu_detail'),
    # Generic detail
    (r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/$', 'generic_detail'),
    (r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/history$', 'generic_history'),
)

urlpatterns += patterns('apps.noclook.views.redirect',
  #wins only because of no /
  (r'^nodes/(?P<handle_id>\d+)$', 'node_redirect'),
  (r'^slow-nodes/(?P<handle_id>\d+)$', 'node_slow_redirect'),
)

urlpatterns += patterns('apps.noclook.views.debug',
  (r'^nodes/(?P<handle_id>\d+)/debug$', 'generic_debug'),
)
