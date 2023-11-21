# This also imports the include function
from django.conf import settings
from django.urls import path, re_path
from django.contrib.auth import views as auth_views
from .views import other, create, edit, import_nodes, report, detail, redirect, debug, list as _list

urlpatterns = [
    path('', other.index),
    # Log out
    path(r'logout/', other.logout_page),
    # Visualize views
    path('visualize/<handle_id>.json', other.visualize_json, name='visualize_json'),
    path('visualize/<slug>/<handle_id>/maximized/', other.visualize_maximize),
    path('visualize/<slug>/<handle_id>/', other.visualize, name='visualize'),
    # Google maps views
    path('gmaps/<slug>.json', other.gmaps_json),
    path('gmaps/<slug>/', other.gmaps),
    # Get all
    # TODO: can it be switched to path instead
    # Or are they even used?, cannot find anything on getall and findall
    re_path(r'^getall/(?P<slug>[-\w]+)/(result.)?(?P<form>(csv|json|xls)?)$', other.find_all),
    # Find all
    re_path(r'^findall/(?P<key>[-\w]+)/(?P<value>.*)/(result.)?(?P<form>(csv|json|xls)?)$', other.find_all),
    re_path(r'^findall/(?P<value>.*)/(result.)?(?P<form>(csv|json|xls)?)$', other.find_all),
    # Find in - re_path due to result.csv
    re_path(r'^findin/(?P<slug>[-\w]+)/(result.)?(?P<form>(csv|json|xls)?)$', other.find_all),
    re_path(r'^findin/(?P<slug>[-\w]+)/(?P<key>[-\w]+)/(?P<value>.*)/(result.)?(?P<form>(csv|json|xls)?)$', other.find_all),
    re_path(r'^findin/(?P<slug>[-\w]+)/(?P<value>.*)/(result.)?(?P<form>(csv|json|xls)?)$', other.find_all),
    # Search
    path('search/', other.search),
    path('search/autocomplete', other.search_autocomplete),

    path('search/typeahead/ports', other.search_port_typeahead),
    path('search/typeahead/locations', other.search_location_typeahead),
    path('search/typeahead/non-locations', other.search_non_location_typeahead),
    path('search/typeahead/<slug>/', other.typeahead_slugs, name='typeahead_slugs'),
    re_path(r'^search/(?P<value>.*)/(result.)?(?P<form>(csv|json|xls)?)$', other.search),
    # QR lookup
    path('lu/<name>/', other.qr_lookup),
    # Hostname lookup
    # TODO: use typeahead instead? used on peeringparther detail for ip lookups
    path('ajax/hostname/', other.ip_address_lookup),
    # Table to CSV or Excel
    path('download/tabletofile/', other.json_table_to_file),

    # -- create views
    path('new/', create.new_node),
    path('new/<slug>/', create.new_node, name='create_node'),
    path('new/<slug>/parent/<int:parent_id>/', create.new_node),
    path('new/<slug>/name/<name>/', create.new_node),
    # Reserve IDs
    path('reserve-id/', create.reserve_id_sequence),
    path('reserve-id/<slug>/', create.reserve_id_sequence),

    # -- edit views
    path('<slug>/<int:handle_id>/edit', edit.edit_node, name='generic_edit'),
    path('port/<int:handle_id>/edit_connect', edit.connect_port),
    path('<slug>/<int:handle_id>/edit/disable-noclook-auto-manage/', edit.disable_noclook_auto_manage),
    path('host/<int:handle_id>/edit/convert-to/<slug>/', edit.convert_host),
    path('<slug>/<int:handle_id>/delete', edit.delete_node),
    path('<slug>/<int:handle_id>/relationship/<int:rel_id>/delete', edit.delete_relationship),
    path('<slug>/<int:handle_id>/relationship/<int:rel_id>/update', edit.update_relationship, name='relationship_update'),
    path('rack/<int:rack_handle_id>/node/<int:handle_id>/position/<int:position>', edit.update_rack_position, name='rack_position'),
    path('port/<int:handle_id>/expired-units/delete', edit.delete_expired_units, name='delete_expire_units'),
    # jscombo
    path('formdata/<slug>/', edit.get_node_type),
    path('formdata/unlocated/<slug>/', edit.get_unlocated_node_type),
    path('formdata/<int:handle_id>/children/', edit.get_child_form_data),
    path('formdata/<int:handle_id>/children/<slug>/', edit.get_child_form_data),
    path('formdata/<slug>/<key>/<value>/', edit.get_subtype_form_data),

    # -- import_nodes
    path('<slug>/<int:handle_id>/import', import_nodes.ImportNodesView.as_view(), name='import_nodes'),
    path('<slug>/<int:handle_id>/export', import_nodes.ExportNodesView.as_view(), name='import_nodes'),

    # -- report views
    path('reports/hosts/', report.host_reports, name='host_report'),
    path('reports/hosts/host-users/', report.host_users, name='host_users_report'),
    path('reports/hosts/host-users/<host_user_name>/', report.host_users, name='host_user_report'),
    path('reports/hosts/host-security-class/', report.host_security_class),
    path('reports/hosts/host-security-class/<status>/', report.host_security_class),
    path('reports/hosts/host-services/', report.host_services),
    path('reports/hosts/host-services/<status>/', report.host_services),
    re_path(r'^reports/unique-ids\.(?P<file_format>xls|csv)$', report.download_unique_ids),
    path('reports/unique-ids/', report.unique_ids),
    re_path(r'^reports/rack-cables/(?P<handle_id>\d+)\.(?P<file_format>xls|csv)$', report.download_rack_cables),

    # -- list views
    # TODO: do as edit? with one for all based on slug
    path('peering-partner/', _list.list_peering_partners),
    path('host/', _list.list_hosts),
    path('site/', _list.list_sites),
    re_path(r'^service/(?P<service_class>(DWDM|Ethernet|External|IAAS|IP|Internal|MPLS|Hosting|SAAS)?)/$', _list.list_services),  # might cause problems for sunet
    path('service/', _list.list_services),
    path('optical-path/', _list.list_optical_paths),
    path('optical-multiplex-section/', _list.list_optical_multiplex_section),
    path('optical-link/', _list.list_optical_links),
    path('optical-node/', _list.list_optical_nodes),
    path('outlet/', _list.list_outlet),
    path('patch-panel/', _list.list_patch_panels),
    path('router/', _list.list_routers),
    path('rack/', _list.list_racks),
    path('room/', _list.list_rooms),
    path('odf/', _list.list_odfs),
    path('cable/', _list.list_cables),
    path('switch/', _list.list_switches),
    path('firewall/', _list.list_firewalls),
    path('customer/', _list.list_customers),
    path('port/', _list.list_ports),
    path('pdu/', _list.list_pdu),
    path('external-equipment/', _list.list_external_equipment),
    path('docker-image/', _list.list_docker_images),
    # Generic list
    path('<slug>/', _list.list_by_type, name='generic_list'),

    # -- detail views
    path('router/<int:handle_id>/', detail.router_detail),
    path('peering-partner/<int:handle_id>/', detail.peering_partner_detail, name='peering_partner_detail'),
    path('peering-group/<int:handle_id>/', detail.peering_group_detail, name='peering_group_detail'),
    path('optical-node/<int:handle_id>/', detail.optical_node_detail),
    path('cable/<int:handle_id>/', detail.cable_detail),
    path('docker-image/<int:handle_id>/', detail.docker_image_detail),
    path('host/<int:handle_id>/', detail.host_detail, name='detail_host'),
    path('host-service/<int:handle_id>/', detail.host_service_detail),
    path('host-provider/<int:handle_id>/', detail.host_provider_detail),
    path('host-user/<int:handle_id>/', detail.host_user_detail),
    path('odf/<int:handle_id>/', detail.odf_detail),
    path('optical-filter/<int:handle_id>/', detail.optical_filter_detail),
    path('outlet/<int:handle_id>/', detail.outlet_detail),
    path('patch-panel/<int:handle_id>/', detail.patch_panel_detail),
    path('port/<int:handle_id>/', detail.port_detail),
    path('site/<int:handle_id>/', detail.site_detail),
    path('rack/<int:handle_id>/', detail.rack_detail),
    path('room/<int:handle_id>/', detail.room_detail),
    path('site-owner/<int:handle_id>/', detail.site_owner_detail),
    path('service/<int:handle_id>/', detail.service_detail),
    path('optical-link/<int:handle_id>/', detail.optical_link_detail),
    path('optical-path/<int:handle_id>/', detail.optical_path_detail),
    path('end-user/<int:handle_id>/', detail.end_user_detail),
    path('customer/<int:handle_id>/', detail.customer_detail),
    path('provider/<int:handle_id>/', detail.provider_detail),
    path('unit/<int:handle_id>/', detail.unit_detail),
    path('external-equipment/<int:handle_id>/', detail.external_equipment_detail),
    path('optical-multiplex-section/<int:handle_id>/', detail.optical_multiplex_section_detail),
    path('firewall/<int:handle_id>/', detail.firewall_detail),
    path('switch/<int:handle_id>/', detail.switch_detail),
    path('pdu/<int:handle_id>/', detail.pdu_detail),
    # Generic detail
    path('<slug>/<int:handle_id>/', detail.generic_detail, name='generic_detail'),
    path('<slug>/<int:handle_id>/history', detail.generic_history),

    # -- redirect
    # wins only because of no /
    path(r'nodes/<int:handle_id>', redirect.node_redirect, name='node_redirect'),
    path('slow-nodes/<int:handle_id>', redirect.node_slow_redirect),
    path('docker-image/tag/<tag>', redirect.docker_image_by_tag_redirect),

    # -- debug view
    path('nodes/<int:handle_id>/debug', debug.generic_debug, name='debug'),
]

if not settings.DJANGO_LOGIN_DISABLED:
    urlpatterns = [path('login/', auth_views.LoginView.as_view())] + urlpatterns
