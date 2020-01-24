# This also imports the include function
from django.conf import settings
from django.conf.urls import url
from django.contrib.auth import views as auth_views
from .views import other, create, edit, import_nodes, report, detail, redirect, debug, list as _list

urlpatterns = [
    url(r'^$', other.index),
    # Log out
    url(r'^logout/$', other.logout_page),
    # Visualize views
    url(r'^visualize/(?P<handle_id>\d+)\.json$', other.visualize_json, name='visualize_json'),
    url(r'^visualize/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/maximized/$', other.visualize_maximize),
    url(r'^visualize/(?P<slug>[-\w]+)/(?P<handle_id>\d+)/$', other.visualize, name='visualize'),
    # Google maps views
    url(r'^gmaps/(?P<slug>[-\w]+)\.json$', other.gmaps_json),
    url(r'^gmaps/(?P<slug>[-\w]+)/$', other.gmaps),
    # Get all
    url(r'^getall/(?P<slug>[-\w]+)/(result.)?(?P<form>(csv|json|xls)?)$', other.find_all),
    # Find all
    url(r'^findall/(?P<key>[-\w]+)/(?P<value>.*)/(result.)?(?P<form>(csv|json|xls)?)$', other.find_all),
    url(r'^findall/(?P<value>.*)/(result.)?(?P<form>(csv|json|xls)?)$', other.find_all),
    # Find in
    url(r'^findin/(?P<slug>[-\w]+)/(result.)?(?P<form>(csv|json|xls)?)$', other.find_all),
    url(r'^findin/(?P<slug>[-\w]+)/(?P<key>[-\w]+)/(?P<value>.*)/(result.)?(?P<form>(csv|json|xls)?)$', other.find_all),
    url(r'^findin/(?P<slug>[-\w]+)/(?P<value>.*)/(result.)?(?P<form>(csv|json|xls)?)$', other.find_all),
    # Search
    url(r'^search/$', other.search),
    url(r'^search/autocomplete$', other.search_autocomplete),
    url(r'^search/typeahead/ports$', other.search_port_typeahead),
    url(r'^search/typeahead/locations$', other.search_location_typeahead),
    url(r'^search/typeahead/non-locations$', other.search_non_location_typeahead),
    url(r'^search/typeahead/(?P<slug>[-\+\w]+)/?$', other.typeahead_slugs, name='typeahead_slugs'),
    url(r'^search/(?P<value>.*)/(result.)?(?P<form>(csv|json|xls)?)$', other.search),
    # QR lookup
    url(r'^lu/(?P<name>[-\w]+)/$', other.qr_lookup),
    # Hostname lookup
    url(r'^ajax/hostname/$', other.ip_address_lookup),
    # Table to CSV or Excel
    url(r'^download/tabletofile/$', other.json_table_to_file),

    # -- create views
    url(r'^new/$', create.new_node),
    url(r'^new/(?P<slug>[-\w]+)/$', create.new_node, name='create_node'),
    url(r'^new/(?P<slug>[-\w]+)/parent/(?P<parent_id>\d+)/$', create.new_node),
    url(r'^new/(?P<slug>[-\w]+)/name/(?P<name>[-\w]+)/$', create.new_node),
    # Reserve IDs
    url(r'^reserve-id/$', create.reserve_id_sequence),
    url(r'^reserve-id/(?P<slug>[-\w]+)/$', create.reserve_id_sequence),

    # -- edit views
    url(r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/edit$', edit.edit_node, name='generic_edit'),
    url(r'^port/(?P<handle_id>\d+)/edit_connect$', edit.connect_port),
    url(r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/edit/disable-noclook-auto-manage/$', edit.disable_noclook_auto_manage),
    url(r'^host/(?P<handle_id>\d+)/edit/convert-to/(?P<slug>[-\w]+)/$', edit.convert_host),
    url(r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/delete$', edit.delete_node),
    url(r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/relationship/(?P<rel_id>\d+)/delete$', edit.delete_relationship),
    url(r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/relationship/(?P<rel_id>\d+)/update$', edit.update_relationship, name='relationship_update'),
    url(r'^rack/(?P<rack_handle_id>\d+)/node/(?P<handle_id>\d+)/position/(?P<position>\d+)$', edit.update_rack_position, name='rack_position'),
    url(r'^formdata/(?P<slug>[-\w]+)/$', edit.get_node_type),
    url(r'^formdata/unlocated/(?P<slug>[-\w]+)/$', edit.get_unlocated_node_type),
    url(r'^formdata/(?P<handle_id>\d+)/children/$', edit.get_child_form_data),
    url(r'^formdata/(?P<handle_id>\d+)/children/(?P<slug>[-\w]+)/$', edit.get_child_form_data),
    url(r'^formdata/(?P<slug>[-\w]+)/(?P<key>[-\w]+)/(?P<value>[-\w ]+)/$', edit.get_subtype_form_data),

    # -- import_nodes
    url(r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/import$', import_nodes.ImportNodesView.as_view(), name='import_nodes'),
    url(r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/export$', import_nodes.ExportNodesView.as_view(), name='import_nodes'),

    # -- report views
    url(r'^reports/hosts/$', report.host_reports, name='host_report'),
    url(r'^reports/hosts/host-users/$', report.host_users, name='host_users_report'),
    url(r'^reports/hosts/host-users/(?P<host_user_name>[-\w]+)/$', report.host_users, name='host_user_report'),
    url(r'^reports/hosts/host-security-class/$', report.host_security_class),
    url(r'^reports/hosts/host-security-class/(?P<status>[-\w]+)/$', report.host_security_class),
    url(r'^reports/hosts/host-services/$', report.host_services),
    url(r'^reports/hosts/host-services/(?P<status>[-\w]+)/$', report.host_services),
    url(r'^reports/unique-ids\.(?P<file_format>xls|csv)$', report.download_unique_ids),
    url(r'^reports/unique-ids/$', report.unique_ids),

    # -- list views
    url(r'^peering-partner/$', _list.list_peering_partners),
    url(r'^host/$', _list.list_hosts),
    url(r'^site/$', _list.list_sites),
    url(r'^service/(?P<service_class>(DWDM|Ethernet|External|IAAS|IP|Internal|MPLS|Hosting|SAAS)?)/$', _list.list_services),
    url(r'^service/$', _list.list_services),
    url(r'^optical-path/$', _list.list_optical_paths),
    url(r'^optical-multiplex-section/$', _list.list_optical_multiplex_section),
    url(r'^optical-link/$', _list.list_optical_links),
    url(r'^optical-node/$', _list.list_optical_nodes),
    url(r'^outlet/$', _list.list_outlet),
    url(r'^patch-panel/$', _list.list_patch_panels),
    url(r'^router/$', _list.list_routers),
    url(r'^rack/$', _list.list_racks),
    url(r'^room/$', _list.list_rooms),
    url(r'^odf/$', _list.list_odfs),
    url(r'^cable/$', _list.list_cables),
    url(r'^switch/$', _list.list_switches),
    url(r'^firewall/$', _list.list_firewalls),
    url(r'^customer/$', _list.list_customers),
    url(r'^port/$', _list.list_ports),
    url(r'^pdu/$', _list.list_pdu),
    # Generic list
    url(r'^(?P<slug>[-\w]+)/$', _list.list_by_type, name='generic_list'),

    # -- detail views
    url(r'^router/(?P<handle_id>\d+)/$', detail.router_detail),
    url(r'^peering-partner/(?P<handle_id>\d+)/$', detail.peering_partner_detail, name='peering_partner_detail'),
    url(r'^peering-group/(?P<handle_id>\d+)/$', detail.peering_group_detail, name='peering_group_detail'),
    url(r'^optical-node/(?P<handle_id>\d+)/$', detail.optical_node_detail),
    url(r'^cable/(?P<handle_id>\d+)/$', detail.cable_detail),
    url(r'^host/(?P<handle_id>\d+)/$', detail.host_detail, name='detail_host'),
    url(r'^host-service/(?P<handle_id>\d+)/$', detail.host_service_detail),
    url(r'^host-provider/(?P<handle_id>\d+)/$', detail.host_provider_detail),
    url(r'^host-user/(?P<handle_id>\d+)/$', detail.host_user_detail),
    url(r'^odf/(?P<handle_id>\d+)/$', detail.odf_detail),
    url(r'^optical-filter/(?P<handle_id>\d+)/$', detail.optical_filter_detail),
    url(r'^outlet/(?P<handle_id>\d+)/$', detail.outlet_detail),
    url(r'^patch-panel/(?P<handle_id>\d+)/$', detail.patch_panel_detail),
    url(r'^port/(?P<handle_id>\d+)/$', detail.port_detail),
    url(r'^site/(?P<handle_id>\d+)/$', detail.site_detail),
    url(r'^rack/(?P<handle_id>\d+)/$', detail.rack_detail),
    url(r'^room/(?P<handle_id>\d+)/$', detail.room_detail),
    url(r'^site-owner/(?P<handle_id>\d+)/$', detail.site_owner_detail),
    url(r'^service/(?P<handle_id>\d+)/$', detail.service_detail),
    url(r'^optical-link/(?P<handle_id>\d+)/$', detail.optical_link_detail),
    url(r'^optical-path/(?P<handle_id>\d+)/$', detail.optical_path_detail),
    url(r'^end-user/(?P<handle_id>\d+)/$', detail.end_user_detail),
    url(r'^customer/(?P<handle_id>\d+)/$', detail.customer_detail),
    url(r'^provider/(?P<handle_id>\d+)/$', detail.provider_detail),
    url(r'^unit/(?P<handle_id>\d+)/$', detail.unit_detail),
    url(r'^external-equipment/(?P<handle_id>\d+)/$', detail.external_equipment_detail),
    url(r'^optical-multiplex-section/(?P<handle_id>\d+)/$', detail.optical_multiplex_section_detail),
    url(r'^firewall/(?P<handle_id>\d+)/$', detail.firewall_detail),
    url(r'^switch/(?P<handle_id>\d+)/$', detail.switch_detail),
    url(r'^pdu/(?P<handle_id>\d+)/$', detail.pdu_detail),
    # Generic detail
    url(r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/$', detail.generic_detail, name='generic_detail'),
    url(r'^(?P<slug>[-\w]+)/(?P<handle_id>\d+)/history$', detail.generic_history),

    # -- redirect
    # wins only because of no /
    url(r'^nodes/(?P<handle_id>\d+)$', redirect.node_redirect, name='node_redirect'),
    url(r'^slow-nodes/(?P<handle_id>\d+)$', redirect.node_slow_redirect),

    # -- debug view
    url(r'^nodes/(?P<handle_id>\d+)/debug$', debug.generic_debug, name='debug'),
]

if not settings.DJANGO_LOGIN_DISABLED:
    urlpatterns = [url(r'^login/$', auth_views.LoginView.as_view())] + urlpatterns
