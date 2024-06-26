# -*- coding: utf-8 -*-
"""
Created on Wed Dec 14 14:00:03 2011

@author: lundberg

Node manipulation views.
"""
from operator import itemgetter
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
import json
from apps.noclook.models import NodeHandle, Dropdown, UniqueIdGenerator, NordunetUniqueId
from django.core.exceptions import ObjectDoesNotExist
from apps.noclook import forms
from apps.noclook import activitylog
from apps.noclook import helpers
from apps.noclook import unique_ids
import norduniclient as nc
from norduniclient.exceptions import UniqueNodeError


# Helper functions
@staff_member_required
def delete_node(request, slug, handle_id):
    """
    Removes the node and all its relationships.
    """
    redirect_url = '/{}'.format(slug)
    nh, node = helpers.get_nh_node(handle_id)
    if nh.node_type.get_label() == 'Unit':
        part_of = node.get_part_of()
        if part_of.get('Part_of'):
            redirect_url = helpers.get_node_url(part_of.get('Part_of')[0]['node'].handle_id)
    try:
        # Redirect to parent if deleted node was a child node
        parent = node.get_parent().get('Has', [])
        if parent:
            redirect_url = helpers.get_node_url(parent[0]['node'].handle_id)
    except AttributeError:
        pass
    helpers.delete_node(request.user, node.handle_id)
    return redirect(redirect_url)


@staff_member_required
def delete_relationship(request, slug, handle_id, rel_id):
    """
    Removes the relationship if the node has a relationship matching the
    supplied id.
    """
    success = False
    if request.method == 'POST':
        nh, node = helpers.get_nh_node(handle_id)
        try:
            relationship = nc.get_relationship_model(nc.graphdb.manager, rel_id)
            if node.handle_id == relationship.start['handle_id'] or node.handle_id == relationship.end['handle_id']:
                activitylog.delete_relationship(request.user, relationship)
                relationship.delete()
                success = True
        except nc.exceptions.RelationshipNotFound:
            success = True
    return JsonResponse({'success': success, 'relationship_id': '{}'.format(rel_id)})


def is_expired(node):
    _, expired = helpers.neo4j_data_age(node)
    return expired


@staff_member_required
def delete_expired_units(request, handle_id):
    """
    Removes the all expired units.
    """
    redirect_url = '/port/{}/'.format(handle_id)
    if request.method == 'POST':
        print("it was a post")
        nh, node = helpers.get_nh_node(handle_id)
        q = """
            MATCH (n:Node {handle_id: $handle_id})<-[:Part_of]-(unit:Unit)
            RETURN unit
            """
        expired_units = [u['unit'] for u in nc.query_to_list(nc.graphdb.manager, q, handle_id=nh.handle_id) if is_expired(u['unit'])]
        for unit in expired_units:
            helpers.delete_node(request.user, unit['handle_id'])
    return redirect(redirect_url)


@staff_member_required
def update_relationship(request, slug, handle_id, rel_id):
    """
    Removes the relationship if the node has a relationship matching the
    supplied id.
    """
    success = False
    properties = {}
    if request.POST:
        nh, node = helpers.get_nh_node(handle_id)
        try:
            for key, value in request.POST.items():
                properties[key] = json.loads(value)
            relationship = nc.get_relationship_model(nc.graphdb.manager, int(rel_id))
            if node.handle_id == relationship.start['handle_id'] or node.handle_id == relationship.end['handle_id']:
                success = helpers.dict_update_relationship(request.user, relationship.id, properties)
        except nc.exceptions.RelationshipNotFound:
            # If the relationship does not exist, then we cannot update
            success = False
        except ValueError:
            pass
    return JsonResponse({'success': success, 'relationship_id': '{}'.format(rel_id), 'data': properties})


# Form data returns
@login_required
def get_node_type(request, slug):
    """
    Compiles a list of alla nodes of that node type and returns a list of
    node name, node id tuples.
    """
    node_type = helpers.slug_to_node_type(slug)
    label = node_type.type.replace(' ', '_')
    result_list = []
    for node in nc.get_node_by_type(nc.graphdb.manager, label):
        result_list.append([node['handle_id'], node['name']])
    result_list = sorted(result_list, key=lambda n: n[1].lower())
    return JsonResponse(result_list, safe=False)


@login_required
def get_unlocated_node_type(request, slug):
    """
    Compiles a list of alla nodes of that node type that does not have a Located_in
    relationship and returns a list of node name, node id tuples.
    """
    node_type = helpers.slug_to_node_type(slug)
    q = '''
        MATCH (node:{node_type})
        WHERE NOT (node)-[:Located_in]->()
        RETURN node.handle_id, node.name
        ORDER BY node.name
        '''.format(node_type=node_type.type.replace(' ', '_'))
    result_list = []
    with nc.graphdb.manager.session as s:
        result = s.run(q)
        result_list = [r for r in result]
    return JsonResponse(result_list, safe=False)


@login_required
def get_child_form_data(request, handle_id, slug=None):
    """
    Compiles a list of the nodes children and returns a list of
    node name, node id tuples. If node_type is set the function will only return
    nodes of that type.
    """
    nh = get_object_or_404(NodeHandle, handle_id=handle_id)
    node_type = slug
    if slug:
        node_type = helpers.slug_to_node_type(slug).type.replace(' ', '_')
    child_list = []
    for child in nh.get_node().get_child_form_data(node_type):
        if not slug:
            node_type = helpers.labels_to_node_type(child['labels'])
        name = u'{} {}'.format(node_type.replace('_', ' '), child['name'])
        if child.get('description', None):
            name = u'{} ({})'.format(name, child['description'])
        child_list.append((child['handle_id'], name))
        child_list = sorted(child_list, key=itemgetter(1))
    return JsonResponse(child_list, safe=False)


@login_required
def get_subtype_form_data(request, slug, key, value):
    """
    Compiles a list of the nodes children and returns a list of
    node name, node id tuples. If node_type is set the function will only return
    nodes of that type.
    """
    node_type = helpers.slug_to_node_type(slug).type.replace(' ', '_')
    q = """
        MATCH (n:{node_type})
        WHERE n.{key} = '{value}'
        RETURN n.handle_id as handle_id, n.name as name, n.description as description
        ORDER BY n.name
        """.format(node_type=node_type, key=key, value=value)
    subtype_list = []
    for subtype in nc.query_to_list(nc.graphdb.manager, q):
        name = subtype['name']
        if subtype.get('description', None):
            name = u'{} ({})'.format(name, subtype['description'])
        subtype_list.append((subtype['handle_id'], name))
        subtype_list = sorted(subtype_list, key=itemgetter(1))
    return JsonResponse(subtype_list, safe=False)


@staff_member_required
def convert_host(request, handle_id, slug):
    """
    Convert a Host to Firewall or Switch.
    """
    allowed_types = ['firewall', 'switch', 'pdu', 'router']  # Types that can be added as Hosts by nmap
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    if slug in allowed_types and nh.node_type.type == 'Host':
        node_type = helpers.slug_to_node_type(slug, create=True)
        nh, node = helpers.logical_to_physical(request.user, handle_id)
        node.switch_type(nh.node_type.get_label(), node_type.get_label())
        nh.node_type = node_type
        nh.save()
        node_properties = {
            'backup': ''
        }
        helpers.dict_update_node(request.user, node.handle_id, node_properties, node_properties.keys())
    return redirect(nh.get_absolute_url())


# Edit functions
@staff_member_required
def edit_node(request, slug, handle_id):
    """
    Generic edit function that redirects calls to node type sensitive edit
    functions.
    """
    try:
        func = EDIT_FUNC[slug]
    except KeyError:
        raise Http404
    return func(request, handle_id)


@staff_member_required
def edit_cable(request, handle_id):
    # Get needed data from node
    nh, cable = helpers.get_nh_node(handle_id)
    connections = cable.get_connected_equipment()
    relations = cable.get_relations()
    if request.POST:
        form = forms.EditCableForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, cable.handle_id, form)
            if form.cleaned_data['relationship_end_a']:
                end_a_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_end_a'])
                helpers.set_connected_to(request.user, cable, end_a_nh.handle_id)
            if form.cleaned_data['relationship_end_b']:
                end_b_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_end_b'])
                helpers.set_connected_to(request.user, cable, end_b_nh.handle_id)
            if form.cleaned_data['relationship_provider']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, cable, owner_nh.handle_id)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditCableForm(cable.data)
    return render(request, 'noclook/edit/edit_cable.html',
                  {'node_handle': nh, 'form': form, 'node': cable, 'connections': connections,
                   'relations': relations})


@staff_member_required
def edit_customer(request, handle_id):
    # Get needed data from node
    nh, customer = helpers.get_nh_node(handle_id)
    if request.POST:
        form = forms.EditCustomerForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, customer.handle_id, form)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditCustomerForm(customer.data)
    return render(request, 'noclook/edit/edit_customer.html', {'node_handle': nh, 'form': form, 'node': customer})


@staff_member_required
def edit_docker_image(request, handle_id):
    # Get needed data from node
    nh, docker_image = helpers.get_nh_node(handle_id)
    if request.POST:
        form = forms.EditDockerImageForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, docker_image.handle_id, form)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditDockerImageForm(docker_image.data)
    return render(request, 'noclook/edit/edit_docker_image.html',
                  {'node_handle': nh, 'form': form, 'node': docker_image})


@staff_member_required
def edit_end_user(request, handle_id):
    # Get needed data from node
    nh, end_user = helpers.get_nh_node(handle_id)
    if request.POST:
        form = forms.EditEndUserForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, end_user.handle_id, form)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditEndUserForm(end_user.data)
    return render(request, 'noclook/edit/edit_end_user.html', {'node_handle': nh, 'form': form, 'node': end_user})


def _handle_ports(parent, clean_ports, user):
    if clean_ports and isinstance(clean_ports, list):
        for port_name in clean_ports:
            helpers.create_port(parent, port_name, user)


@staff_member_required
def edit_external_equipment(request, handle_id):
    # Get needed data from node
    nh, external_equipment = helpers.get_nh_node(handle_id)
    relations = external_equipment.get_relations()
    location = external_equipment.get_location()
    ports = external_equipment.get_ports()
    if request.POST:
        form = forms.EditExternalEquipmentForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, external_equipment.handle_id, form)
            # External Equipment specific updates
            if form.cleaned_data['relationship_owner']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_owner'])
                helpers.set_owner(request.user, external_equipment, owner_nh.handle_id)
            _handle_location(request.user,
                             external_equipment,
                             form.cleaned_data['relationship_location'])
            _handle_ports(external_equipment,
                          form.cleaned_data['relationship_ports'],
                          request.user)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditExternalEquipmentForm(external_equipment.data)
    return render(request, 'noclook/edit/edit_external_equipment.html',
                  {'node_handle': nh, 'node': external_equipment, 'form': form, 'relations': relations,
                   'location': location, 'ports': ports})


def _handle_location(user, node, location_id):
    if location_id:
        location_nh = _nh_safe_get(location_id)
        if location_nh:
            # Remove old.
            helpers.remove_locations(user, node)
            # Set new location
            helpers.set_location(user, node, location_nh.handle_id)


@staff_member_required
def edit_firewall(request, handle_id):
    # Get needed data from node
    nh, firewall = helpers.get_nh_node(handle_id)
    location = firewall.get_location()
    relations = firewall.get_relations()
    host_services = firewall.get_host_services()
    ports = firewall.get_ports()
    if request.POST:
        form = forms.EditFirewallForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, firewall.handle_id, form)
            #  Firewall specific updates
            if form.cleaned_data['relationship_user']:
                user_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_user'])
                helpers.set_user(request.user, firewall, user_nh.handle_id)
            if form.cleaned_data['relationship_owner']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_owner'])
                helpers.set_owner(request.user, firewall, owner_nh.handle_id)
            _handle_location(request.user,
                             firewall,
                             form.cleaned_data['relationship_location'])
            if form.cleaned_data['services_locked'] and form.cleaned_data['services_checked']:
                helpers.remove_rogue_service_marker(request.user, firewall.handle_id)
            _handle_ports(firewall,
                          form.cleaned_data['relationship_ports'],
                          request.user)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditFirewallForm(firewall.data)
    return render(request, 'noclook/edit/edit_firewall.html',
                  {'node_handle': nh, 'node': firewall, 'form': form, 'location': location,
                   'relations': relations, 'ports': ports,
                   'host_services': host_services})


@staff_member_required
def edit_host(request, handle_id):
    # Get needed data from node
    nh, host = helpers.get_nh_node(handle_id)
    location = host.get_location()
    relations = host.get_relations()
    depends_on = host.get_dependencies()
    host_services = host.get_host_services()
    ports = host.get_ports()
    dependency_categories = 'service,host'
    user_categories = ['host-user']
    if request.POST:
        form = forms.EditHostForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, host.handle_id, form)
            # Host specific updates
            if form.cleaned_data['relationship_user']:
                    user_nh = _nh_safe_get(form.cleaned_data['relationship_user'])
                    if user_nh:
                        helpers.set_user(request.user, host, user_nh.handle_id)
            if form.cleaned_data['relationship_owner']:
                owner_nh = _nh_safe_get(form.cleaned_data['relationship_owner'])
                if owner_nh:
                    helpers.set_owner(request.user, host, owner_nh.handle_id)
            # You can not set location and depends on at the same time
            if form.cleaned_data['relationship_depends_on']:
                depends_on_nh = _nh_safe_get(form.cleaned_data['relationship_depends_on'])
                if depends_on_nh:
                    helpers.set_depends_on(request.user, host, depends_on_nh.handle_id)
            elif form.cleaned_data['relationship_location']:
                _handle_location(request.user,
                                 host,
                                 form.cleaned_data['relationship_location'])
            if form.cleaned_data['services_locked'] and form.cleaned_data['services_checked']:
                helpers.remove_rogue_service_marker(request.user, host.handle_id)
            _handle_ports(host,
                          form.cleaned_data['relationship_ports'],
                          request.user)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditHostForm(host.data)
    context = {
        'node_handle': nh, 'node': host, 'form': form, 'location': location,
        'relations': relations, 'depends_on': depends_on, 'ports': ports,
        'host_services': host_services, 'dependency_categories': dependency_categories,
        'user_categories': user_categories,
    }
    return render(request, 'noclook/edit/edit_host.html', context)


def _nh_safe_get(pk):
    try:
        nh = NodeHandle.objects.get(pk=pk)
    except:
        nh = None
    return nh


@staff_member_required
def edit_odf(request, handle_id):
    # Get needed data from node
    nh, odf = helpers.get_nh_node(handle_id)
    location = odf.get_location()
    ports = odf.get_ports()
    if request.POST:
        form = forms.EditOdfForm(request.POST)
        ports_form = forms.BulkPortsForm(request.POST)
        if form.is_valid() and ports_form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, odf.handle_id, form)
            # ODF specific updates
            _handle_location(request.user,
                             odf,
                             form.cleaned_data['relationship_location'])
            _handle_ports(odf,
                          form.cleaned_data['relationship_ports'],
                          request.user)
            if not ports_form.cleaned_data['no_ports']:
                data = ports_form.cleaned_data
                helpers.bulk_create_ports(nh.get_node(), request.user, **data)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditOdfForm(odf.data)
        ports_form = forms.BulkPortsForm({'port_type': 'LC', 'offset': 1, 'num_ports': '0'})
    return render(request, 'noclook/edit/edit_odf.html',
                  {'node_handle': nh, 'node': odf, 'form': form, 'location': location, 'ports': ports, 'ports_form': ports_form})

@staff_member_required
def edit_outlet(request, handle_id):
    # Get needed data from node
    nh, outlet = helpers.get_nh_node(handle_id)
    location = outlet.get_location()
    location_path = outlet.get_location_path()
    ports = outlet.get_ports()
    if request.POST:
        form = forms.EditOutletForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, outlet.handle_id, form)
            # ODF specific updates
            _handle_location(request.user,
                             outlet,
                             form.cleaned_data['relationship_location'])
            _handle_ports(outlet,
                          form.cleaned_data['relationship_ports'],
                          request.user)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditOutletForm(outlet.data)
    return render(request, 'noclook/edit/edit_outlet.html',
                  {'node_handle': nh, 'node': outlet, 'form': form, 'location': location,
                   'location_path': location_path, 'ports': ports})


def _handle_trunk_cable(node, form, user):
    # sanity checks
    if form.is_valid():
        if form.cleaned_data['trunk_num_ports'] < 1:
            # no ports to handle
            return True
        # get base cable id
        base_name = form.cleaned_data['trunk_base_name']
        if not base_name:
            # check uniqueIDgennerator
            try:
                id_generator = UniqueIdGenerator.objects.filter(name__endswith='cable_id').get()
                base_name = unique_ids.get_collection_unique_id(id_generator)
            except ObjectDoesNotExist:
                form.add_error('trunk_base_name', 'No unique id generator found, so base name is required')
                return False

        # get other equipment
        try:
            target_nh, target_node = helpers.get_nh_node(form.cleaned_data['trunk_relationship_other'])
        except Exception:
            form.add_error('trunk_relationship_other', 'Other equipment cannot be found')
            return False

        def port_map(ports_raw):
            ports = ports_raw.get('Has', {})
            return {p.get('node').data.get('name'): p.get('node') for p in ports}
        ports = port_map(node.get_ports())
        target_ports = port_map(target_node.get_ports())
        first_port = form.cleaned_data['trunk_first_port']
        end_port = first_port + form.cleaned_data['trunk_num_ports']
        create_missing = form.cleaned_data['trunk_create_missing_ports']
        trunk_prefix = form.cleaned_data['trunk_prefix']

        ports_to_connect = []
        for i in range(first_port, end_port):
            port_name = '{}{}'.format(trunk_prefix, i)
            port_a = ports.get(port_name)
            port_b = target_ports.get(port_name)

            # check if cable exis
            cable_name = '{}_{}'.format(base_name, port_name)
            cable_count = NodeHandle.objects.filter(node_name=cable_name, node_type__type='Cable').count()
            if cable_count != 0:
                form.add_error('trunk_base_name', '{} already exist'.format(cable_name))
            elif port_a and port_b:
                ports_to_connect.append((port_a, port_b))
            elif create_missing:
                if not port_a:
                    port_a = helpers.create_port(node, port_name, user)
                if not port_b:
                    port_b = helpers.create_port(target_node, port_name, user)
                ports_to_connect.append((port_a, port_b))
            else:
                form.add_error('trunk_create_missing_ports', '{} missing on one of the endpoints'.format(port_name))

        if form.errors:
            return False

        # create cables between ports
        for a, b in ports_to_connect:
            port_name = a.data.get('name')
            cable_name = '{}_{}'.format(base_name, port_name)
            unique_ids.register_unique_id(NordunetUniqueId, cable_name)
            cable_nh = helpers.create_unique_node_handle(user, cable_name, 'cable', 'Physical')
            cable_node = cable_nh.get_node()
            # update cable type
            helpers.dict_update_node(user, cable_node.handle_id, {'cable_type': 'Fixed'})
            helpers.set_connected_to(user, cable_node, a.handle_id)
            helpers.set_connected_to(user, cable_node, b.handle_id)
        return True


@staff_member_required
def edit_patch_panel(request, handle_id):
    # Get needed data from node
    nh, patch_panel = helpers.get_nh_node(handle_id)
    location = patch_panel.get_location()
    location_path = patch_panel.get_location_path()
    ports = patch_panel.get_ports()

    trunk_form = forms.TrunkCableForm(request.POST or None)
    if request.POST:
        form = forms.EditPatchPanelForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, patch_panel.handle_id, form)
            # ODF specific updates
            _handle_location(request.user,
                             patch_panel,
                             form.cleaned_data['relationship_location'])
            _handle_ports(patch_panel,
                          form.cleaned_data['relationship_ports'],
                          request.user)
            if not _handle_trunk_cable(patch_panel, trunk_form, request.user):
                # fall through to default return
                form.add_error(None, 'Error in trunk cable')
            elif 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditPatchPanelForm(patch_panel.data)
    return render(
        request,
        'noclook/edit/edit_patch_panel.html',
        {'node_handle': nh,
         'node': patch_panel,
         'form': form,
         'trunk_form': trunk_form,
         'location': location,
         'location_path': location_path,
         'ports': ports})


@staff_member_required
def edit_optical_fillter(request, handle_id):
    nh, of = helpers.get_nh_node(handle_id)
    location = of.get_location()
    ports = of.get_ports()
    form = forms.EditOpticalFilterForm(request.POST or of.data)
    if request.POST and form.is_valid():
        # Generic node update
        helpers.form_update_node(request.user, of.handle_id, form)
        # Optical Filter specific updates
        _handle_location(request.user,
                         of,
                         form.cleaned_data['relationship_location'])
        _handle_ports(of,
                      form.cleaned_data['relationship_ports'],
                      request.user)
        if 'saveanddone' in request.POST:
            return redirect(nh.get_absolute_url())
        else:
            return redirect('%sedit' % nh.get_absolute_url())

    return render(request, 'noclook/edit/edit_optical_filter.html', {'node_handle': nh, 'node': of, 'form': form, 'location': location, 'ports': ports})


@staff_member_required
def edit_optical_link(request, handle_id):
    # Get needed data from node
    nh, link = helpers.get_nh_node(handle_id)
    relations = link.get_relations()
    depends_on = link.get_dependencies()
    if request.POST:
        form = forms.EditOpticalLinkForm(request.POST)
        if form.is_valid():
            if 'type' in form.cleaned_data:
                form.cleaned_data['type'] = form.cleaned_data['type'].name
            # Generic node update
            helpers.form_update_node(request.user, link.handle_id, form)
            # Optical Link node updates
            if form.cleaned_data['relationship_provider']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, link, owner_nh.handle_id)
            if form.cleaned_data['relationship_end_a']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_end_a'])
                helpers.set_depends_on(request.user, link, depends_on_nh.handle_id)
            if form.cleaned_data['relationship_end_b']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_end_b'])
                helpers.set_depends_on(request.user, link, depends_on_nh.handle_id)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditOpticalLinkForm(link.data)
    return render(request, 'noclook/edit/edit_optical_link.html',
                  {'node_handle': nh, 'form': form, 'node': link, 'relations': relations,
                   'depends_on': depends_on})


@staff_member_required
def edit_optical_multiplex_section(request, handle_id):
    # Get needed data from node
    nh, oms = helpers.get_nh_node(handle_id)
    relations = oms.get_relations()
    depends_on = oms.get_dependencies()
    dependency_categories = 'optical-link'
    if request.POST:
        form = forms.EditOpticalMultiplexSectionForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, oms.handle_id, form)
            # Optical Multiplex Section node updates
            if form.cleaned_data['relationship_provider']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, oms, owner_nh.handle_id)
            if form.cleaned_data['relationship_depends_on']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_depends_on'])
                helpers.set_depends_on(request.user, oms, depends_on_nh.handle_id)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditOpticalMultiplexSectionForm(oms.data)
    return render(request, 'noclook/edit/edit_optical_multiplex_section.html',
                  {'node_handle': nh, 'form': form, 'node': oms, 'relations': relations,
                      'depends_on': depends_on, 'dependency_categories': dependency_categories})


@staff_member_required
def edit_optical_node(request, handle_id):
    # Get needed data from node
    nh, optical_node = helpers.get_nh_node(handle_id)
    location = optical_node.get_location()
    ports = optical_node.get_ports()
    if request.POST:
        form = forms.EditOpticalNodeForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, optical_node.handle_id, form)
            # Optical Node specific updates
            _handle_location(request.user,
                             optical_node,
                             form.cleaned_data['relationship_location'])
            _handle_ports(optical_node,
                          form.cleaned_data['relationship_ports'],
                          request.user)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditOpticalNodeForm(optical_node.data)
    return render(request, 'noclook/edit/edit_optical_node.html',
                  {'node_handle': nh, 'node': optical_node, 'form': form, 'location': location,
                   'ports': ports})


@staff_member_required
def edit_optical_path(request, handle_id):
    # Get needed data from node
    nh, path = helpers.get_nh_node(handle_id)
    relations = path.get_relations()
    depends_on = path.get_dependencies()
    dependency_categories = 'odf,optical-link,optical-multiplex-section,optical-node,router,switch,optical-path,service'
    if request.POST:
        form = forms.EditOpticalPathForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, path.handle_id, form)
            # Optical Path node updates
            if form.cleaned_data['relationship_provider']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, path, owner_nh.handle_id)
            if form.cleaned_data['relationship_depends_on']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_depends_on'])
                helpers.set_depends_on(request.user, path, depends_on_nh.handle_id)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditOpticalPathForm(path.data)
    return render(request, 'noclook/edit/edit_optical_path.html',
                  {'node_handle': nh, 'form': form, 'node': path, 'relations': relations,
                   'depends_on': depends_on, 'dependency_categories': dependency_categories})


@staff_member_required
def edit_pdu(request, handle_id):
    # Get needed data from node
    nh, pdu = helpers.get_nh_node(handle_id)
    location = pdu.get_location()
    relations = pdu.get_relations()
    depends_on = pdu.get_dependencies()
    host_services = pdu.get_host_services()
    ports = pdu.get_ports()
    dependency_categories = 'service'
    ports_form = forms.BulkPortsForm(request.POST or None)
    if request.POST:
        form = forms.EditPDUForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, pdu.handle_id, form)
            # Host specific updates
            if form.cleaned_data['relationship_user']:
                user_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_user'])
                helpers.set_user(request.user, pdu, user_nh.handle_id)
            if form.cleaned_data['relationship_owner']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_owner'])
                helpers.set_owner(request.user, pdu, owner_nh.handle_id)
            # You can not set location and depends on at the same time
            if form.cleaned_data['relationship_depends_on']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_depends_on'])
                helpers.set_depends_on(request.user, pdu, depends_on_nh.handle_id)
            elif form.cleaned_data['relationship_location']:
                _handle_location(request.user,
                                 pdu,
                                 form.cleaned_data['relationship_location'])
            if form.cleaned_data['services_locked'] and form.cleaned_data['services_checked']:
                helpers.remove_rogue_service_marker(request.user, pdu.handle_id)
            if ports_form.is_valid() and not ports_form.cleaned_data['no_ports']:
                data = ports_form.cleaned_data
                helpers.bulk_create_ports(pdu, request.user, **data)
            _handle_ports(pdu,
                          form.cleaned_data['relationship_ports'],
                          request.user)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditPDUForm(pdu.data)
    return render(request, 'noclook/edit/edit_pdu.html',
                  {'node_handle': nh, 'node': pdu, 'form': form, 'location': location,
                   'relations': relations, 'depends_on': depends_on, 'ports': ports,
                   'host_services': host_services, 'dependency_categories': dependency_categories,
                   'ports_form': ports_form})


@staff_member_required
def edit_peering_group(request, handle_id):
    # Get needed data from node
    nh, peering_group = helpers.get_nh_node(handle_id)
    depends_on = peering_group.get_dependencies()

    if request.POST:
        form = forms.EditPeeringGroupForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, peering_group.handle_id, form)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditPeeringGroupForm(peering_group.data)
    return render(request, 'noclook/edit/edit_peering_group.html',
                  {'node_handle': nh, 'node': peering_group, 'form': form,
                      'depends_on': depends_on})


@staff_member_required
def edit_peering_partner(request, handle_id):
    # Get needed data from node
    nh, peering_partner = helpers.get_nh_node(handle_id)
    if request.POST:
        form = forms.EditPeeringPartnerForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, peering_partner.handle_id, form)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditPeeringPartnerForm(peering_partner.data)
    return render(request, 'noclook/edit/edit_peering_partner.html',
                  {'node_handle': nh, 'node': peering_partner, 'form': form})


@staff_member_required
def edit_port(request, handle_id):
    nh, port = helpers.get_nh_node(handle_id)
    parent = port.get_parent()
    connected_to = port.get_connected_to()
    parent_categories = ['external-equipment',
                         'firewall',
                         'host',
                         'odf',
                         'optical-node',
                         'router',
                         'switch']
    connections_categories = Dropdown.get('cable_types').as_values(False)
    if request.POST:
        form = forms.EditPortForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, port.handle_id, form)
            # Port specific updates
            if form.cleaned_data['relationship_parent']:
                parent_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_parent'])
                helpers.set_has(request.user, parent_nh.get_node(), port.handle_id)
            if form.cleaned_data['relationship_connected_to']:
                cable_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_connected_to'])
                helpers.set_connected_to(request.user, cable_nh.get_node(), port.handle_id)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditPortForm(port.data)
    return render(request, 'noclook/edit/edit_port.html',
                  {'node_handle': nh, 'form': form, 'node': port, 'parent': parent,
                      'connected_to': connected_to, 'parent_categories': parent_categories, 'connections_categories': connections_categories})


@staff_member_required
def connect_port(request, handle_id):
    nh, port = helpers.get_nh_node(handle_id)
    location_path = port.get_location_path()

    tmp_connected_to = port.get_connected_to()

    # Remove all "Fixed" cables, reduce risk for user to remove building cables
    connected_to = {'Connected_to': []}
    if tmp_connected_to.get('Connected_to'):
        for item in tmp_connected_to['Connected_to']:
            if item['node'].data['cable_type'] != 'Fixed':
                connected_to['Connected_to'].append(item)

    connections_categories = Dropdown.get('cable_types').as_values(False)
    cable_types = u', '.join([u'"{}"'.format(val) for val in Dropdown.get('cable_types').as_values()])

    # retunr to device the port is connected to
    redirect_url = helpers.get_node_url(port.handle_id)
    parent = port.get_parent().get('Has', [])
    if parent:
        redirect_url = helpers.get_node_url(parent[0]['node'].handle_id)

    if request.POST:
        form = forms.ConnectPortForm(request.POST)
        if form.is_valid():
            if not form.cleaned_data['relationship_end_a']:
                form.add_error('relationship_end_a', 'Please select other end of cable')
            else:
                try:
                    new_cable_nh = helpers.form_to_unique_node_handle(request, form, 'cable', 'Physical')
                except UniqueNodeError:
                    form = forms.ConnectPortForm(request.POST)
                    form.add_error('name', 'A Cable with that name already exists.')
                    return render(request, 'noclook/edit/connect_port.html', {'form': form})

                #Update cable
                helpers.form_update_node(request.user, new_cable_nh.handle_id, form)

                # Connect cable to first port
                helpers.set_connected_to(request.user, new_cable_nh.get_node(), port.handle_id)

                # Connect cable to selected port
                end_a_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_end_a'])
                helpers.set_connected_to(request.user, new_cable_nh.get_node(), end_a_nh.handle_id)

                return redirect(redirect_url)
    else:
        initial = {'name': None}
        form = forms.ConnectPortForm(initial=initial)

    return render(request, 'noclook/edit/connect_port.html',
                  {'node_handle': nh, 'form': form, 'node': port, 'redirect_url': redirect_url,
                      'connected_to': connected_to, 'cable_types': cable_types,
                   'connections_categories': connections_categories, 'location_path': location_path})

@staff_member_required
def edit_provider(request, handle_id):
    # Get needed data from node
    nh, provider = helpers.get_nh_node(handle_id)
    if request.POST:
        form = forms.EditProviderForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, provider.handle_id, form)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditProviderForm(provider.data)
    return render(request, 'noclook/edit/edit_provider.html',
                  {'node_handle': nh, 'form': form, 'node': provider})


@staff_member_required
def edit_rack(request, handle_id):
    # Get needed data from node
    nh, rack = helpers.get_nh_node(handle_id)
    parent = rack.get_parent()
    located_in = rack.get_located_in()
    located_in_categories = ['host', 'odf', 'optical-node', 'router']
    if request.POST:
        form = forms.EditRackForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, rack.handle_id, form)
            # Rack specific updates
            if form.cleaned_data['relationship_parent']:
                parent_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_parent'])
                helpers.set_has(request.user, parent_nh.get_node(), rack.handle_id)
            if form.cleaned_data['relationship_located_in']:
                equipment = NodeHandle.objects.get(pk=form.cleaned_data['relationship_located_in'])
                helpers.set_location(request.user, equipment.get_node(), rack.handle_id)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditRackForm(rack.data)
    return render(request, 'noclook/edit/edit_rack.html',
                  {'node_handle': nh, 'form': form, 'parent': parent, 'node': rack,
                      'located_in': located_in, 'parent_categories': 'site', 'located_in_categories': located_in_categories})


@staff_member_required
def edit_room(request, handle_id):
    # Get needed data from node
    nh, room = helpers.get_nh_node(handle_id)
    parent = room.get_parent()
    located_in = room.get_located_in()
    located_in_categories = ['rack', 'host', 'odf', 'optical-node', 'router']
    if request.POST:
        form = forms.EditRoomForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, room.handle_id, form)
            # Room specific updates
            if form.cleaned_data['relationship_parent']:
                parent_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_parent'])
                helpers.set_has(request.user, parent_nh.get_node(), room.handle_id)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditRoomForm(room.data)
    return render(request, 'noclook/edit/edit_room.html',
                  {'node_handle': nh, 'form': form, 'parent': parent, 'node': room,
                      'located_in': located_in, 'parent_categories': 'site', 'located_in_categories': located_in_categories})


@staff_member_required
def update_rack_position(request, rack_handle_id, handle_id, position):
    """
    Updates the nodes rack_position if node is placed in rack
    """
    if request.method == 'POST':
        success = False
        nh, node = helpers.get_nh_node(handle_id)
        if nh.node_meta_type == 'Physical':
            helpers.dict_update_node(request.user, node.handle_id, {'rack_position': int(position)})
            success = True
        return JsonResponse({'success': success, 'position': '{}'.format(position), 'handle_id': node.handle_id})
    else:
        return Http404()


@staff_member_required
def edit_router(request, handle_id):
    # Get needed data from node
    nh, router = helpers.get_nh_node(handle_id)
    location = router.get_location()
    if request.POST:
        form = forms.EditRouterForm(request.POST)
        ports_form = forms.BulkPortsForm(request.POST)
        if form.is_valid() and ports_form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, router.handle_id, form)
            # Router specific updates
            _handle_location(request.user,
                             router,
                             form.cleaned_data['relationship_location'])
            _handle_ports(router,
                          form.cleaned_data['relationship_ports'],
                          request.user)
            if not ports_form.cleaned_data['no_ports']:
                data = ports_form.cleaned_data
                helpers.bulk_create_ports(nh.get_node(), request.user, **data)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditRouterForm(router.data)
        ports_form = forms.BulkPortsForm({'port_type': 'LC', 'offset': 1, 'num_ports': '0'})
        return render(request, 'noclook/edit/edit_router.html',
                {'node_handle': nh, 'node': router, 'form': form, 'location': location, 'ports_form': ports_form})


@staff_member_required
def edit_service(request, handle_id):
    # Get needed data from node
    nh, service = helpers.get_nh_node(handle_id)
    relations = service.get_relations()
    depends_on = service.get_dependencies()
    dependency_categories = ['host',
                             'firewall',
                             'odf',
                             'optical-node',
                             'optical-path',
                             'optical-filter',
                             'router',
                             'service',
                             'switch',
                             'external-equipment']
    user_categories = ['customer', 'end-user']
    if request.POST:
        form = forms.EditServiceForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, service.handle_id, form)
            # Service node updates
            if form.cleaned_data['relationship_provider']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
                helpers.set_provider(request.user, service, owner_nh.handle_id)
            if form.cleaned_data['relationship_user']:
                user_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_user'])
                helpers.set_user(request.user, service, user_nh.handle_id)
            if form.cleaned_data['relationship_depends_on']:
                depends_on_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_depends_on'])
                helpers.set_depends_on(request.user, service, depends_on_nh.handle_id)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditServiceForm(service.data)
    return render(request, 'noclook/edit/edit_service.html',
                  {'node_handle': nh, 'form': form, 'node': service, 'relations': relations,
                   'depends_on': depends_on, 'dependency_categories': dependency_categories,
                   'user_categories': user_categories})


@staff_member_required
def edit_site(request, handle_id):
    # Get needed data from node
    nh, site = helpers.get_nh_node(handle_id)
    relations = site.get_relations()
    if request.POST:
        form = forms.EditSiteForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, site.handle_id, form)
            # Set site owner
            if form.cleaned_data['relationship_responsible_for']:
                responsible_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_responsible_for'])
                helpers.set_responsible_for(request.user, site, responsible_nh.handle_id)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditSiteForm(site.data)
    return render(request, 'noclook/edit/edit_site.html',
                  {'node_handle': nh, 'form': form, 'relations': relations, 'node': site})


@staff_member_required
def edit_site_owner(request, handle_id):
    # Get needed data from node
    nh, site_owner = helpers.get_nh_node(handle_id)
    if request.POST:
        form = forms.EditSiteOwnerForm(request.POST)
        if form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, site_owner.handle_id, form)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditSiteOwnerForm(site_owner.data)
    return render(request, 'noclook/edit/edit_site_owner.html',
                  {'node_handle': nh, 'form': form, 'node': site_owner})


@staff_member_required
def edit_switch(request, handle_id):
    # Get needed data from node
    nh, switch = helpers.get_nh_node(handle_id)
    location = switch.get_location()
    relations = switch.get_relations()
    depends_on = switch.get_dependencies()
    host_services = switch.get_host_services()
    ports = switch.get_ports()
    ports_form = forms.BulkPortsForm(request.POST or None)
    if request.POST:
        form = forms.EditSwitchForm(request.POST)
        if form.is_valid() and ports_form.is_valid():
            # Generic node update
            helpers.form_update_node(request.user, switch.handle_id, form)
            # Host specific updates
            if form.cleaned_data['relationship_owner']:
                owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_owner'])
                helpers.set_owner(request.user, switch, owner_nh.handle_id)
            # You can not set location and depends on at the same time
            _handle_location(request.user,
                             switch,
                             form.cleaned_data['relationship_location'])
            if form.cleaned_data['services_locked'] and form.cleaned_data['services_checked']:
                helpers.remove_rogue_service_marker(request.user, switch.handle_id)
            _handle_ports(switch,
                          form.cleaned_data['relationship_ports'],
                          request.user)

            if not ports_form.cleaned_data['no_ports']:
                data = ports_form.cleaned_data
                helpers.bulk_create_ports(switch, request.user, **data)
            if 'saveanddone' in request.POST:
                return redirect(nh.get_absolute_url())
            else:
                return redirect('%sedit' % nh.get_absolute_url())
    else:
        form = forms.EditSwitchForm(switch.data)
    return render(request, 'noclook/edit/edit_switch.html',
                  {'node_handle': nh, 'node': switch, 'form': form, 'location': location,
                   'relations': relations, 'depends_on': depends_on, 'ports': ports,
                   'host_services': host_services, 'ports_form': ports_form})


@staff_member_required
def disable_noclook_auto_manage(request, slug, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    node = nh.get_node()
    if node.data.get('noclook_auto_manage'):
        node_properties = {
            'noclook_auto_manage': ''
        }
        helpers.dict_update_node(request.user, node.handle_id, node_properties, node_properties.keys())
    return redirect(nh.get_absolute_url())



EDIT_FUNC = {
    'cable': edit_cable,
    'customer': edit_customer,
    'docker-image': edit_docker_image,
    'end-user': edit_end_user,
    'external-equipment': edit_external_equipment,
    'firewall': edit_firewall,
    'service': edit_service,
    'host': edit_host,
    'odf': edit_odf,
    'optical-filter': edit_optical_fillter,
    'optical-node': edit_optical_node,
    'optical-link': edit_optical_link,
    'optical-multiplex-section': edit_optical_multiplex_section,
    'optical-path': edit_optical_path,
    'outlet': edit_outlet,
    'patch-panel': edit_patch_panel,
    'pdu': edit_pdu,
    'peering-partner': edit_peering_partner,
    'peering-group': edit_peering_group,
    'port': edit_port,
    'provider': edit_provider,
    'rack': edit_rack,
    'router': edit_router,
    'site': edit_site,
    'room': edit_room,
    'site-owner': edit_site_owner,
    'switch': edit_switch,
}
