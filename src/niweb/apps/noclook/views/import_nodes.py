# -*- coding: utf-8 -*-

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.template.defaultfilters import slugify
from django.views.generic import View
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse
from ..models import NodeHandle
import json
import re

from apps.noclook import forms
from apps.noclook import helpers

import norduniclient as nc
from norduniclient.exceptions import UniqueNodeError

VALIDATION_FORMS = {
  'Rack': forms.EditRackForm,
  'Firewall': forms.EditFirewallForm,
  'Port': forms.EditPortForm,
  'Host': forms.EditHostForm,
  'PDU': forms.EditPDUForm,
  'Switch': forms.EditSwitchForm,
  'ODF': forms.EditOdfForm,
  'Router': forms.EditRouterForm,
  'Optica Node': forms.EditOpticalNodeForm,
}

META_TYPES = {
  'Rack': 'Location',
}

HAS_RELATION = [
  'Port',
  'Rack',
]

GENERIC_TYPES = [
  'ODF',
  'Port',
  'Rack',
  'External Equipment',
  # TODO: maybe not?
  'Module',
  'FPC',
  'PIC',
]

EXPORT_FILTER = [
  'Module',
  'FPC',
  'PIC',
]


class ImportNodesView(View):
    def get(self, request, slug, handle_id):
        parent = get_object_or_404(NodeHandle, handle_id=handle_id)
        return render(request, 'noclook/import/upload.html')

    def post(self, request, slug, handle_id):
        parent = get_object_or_404(NodeHandle, handle_id=handle_id)
        if 'file' in request.FILES:
            return self.file(request, parent)
        if 'import' in request.POST:
            # Recreate data table
            data = self.form_parse(request)
            errors = self.validate(data)
            if errors:
                return self.edit(request, parent, data, errors)
            else:
                return self.create(request, parent, data)

    # Consider moving to forms?
    def form_parse(self, request):
        data = {'children': {}}
        for key, val in sorted(request.POST.items()):
            names = key.split(".")
            last = data
            if len(names) > 1:
                for path in names[0:-1]:
                    match = re.search(r'\d+$', path)
                    if match:
                        idx = int(match.group())
                        if idx not in last['children']:
                            last['children'][idx] = {'children': {}}
                        last = last['children'][idx]
                last[names[-1]] = val
        self.convert_children(data)
        return data['children']

    def convert_children(self, data):
        if 'children' in data:
            tmp = [v for k, v in sorted(data['children'].items())]
        for child in tmp:
            self.convert_children(child)
        data['children'] = tmp

    def validate(self, data, parent_id=None):
        errors_out = {}
        for i, item in enumerate(data):
            form = VALIDATION_FORMS.get(item['node_type'])
            # Create item id
            item_id = u'{}{}'.format(item['node_type'], i+1)
            if parent_id:
                item_id = u'{}.{}'.format(parent_id, item_id)

            if form:
                f = form(item)
                for field, errors in f.errors.items():
                    idx = u"{}.{}".format(item_id, field)
                    errors_out[idx] = errors
            if item['node_type'] not in GENERIC_TYPES:
                idx = u'{}.{}'.format(item_id, 'name')
                unique_error = self.validate_unique(item)
                if unique_error:
                    errors_out[idx] = unique_error
            if 'children' in item:
                child_errors = self.validate(item['children'], item_id)
                errors_out.update(child_errors)
        return errors_out

    def validate_unique(self, item):
        error = None
        if item['name']:
            slug = slugify(item['node_type'])
            node_type = helpers.slug_to_node_type(slug, create=True)
            try:
                NodeHandle.objects.get(node_name=item['name'],
                                       node_type=node_type)
                error = "Must be unique."
            except NodeHandle.MultipleObjectsReturned:
                error = "Must be unique."
            except NodeHandle.DoesNotExist:
                pass
        return error

    def file(self, request, parent):
        _file = request.FILES['file']
        data = None
        errors = None
        try:
            string_data = _file.read().decode(_file.charset or 'utf-8')
            data = json.loads(string_data)
        except Exception as e:
            errors = {'global': ['Failed parsing json, got error: {}'.format(e)]}
        if data:
            errors = self.validate(data)

        if 'import' in request.POST and not errors:
            return self.create(request, parent, data)
        else:
            return self.edit(request, parent, data, errors)

    def edit(self, request, parent, data, errors=None):
        return render(request, 'noclook/import/edit.html',
                      {'parent': parent, 'data': data, 'errors': errors})

    def create(self, request, parent, data):
        user = request.user
        errors = []
        for item in data:
            error = self.create_node(item, parent, user)
            errors += error

        if errors:
            return self.edit(request, parent, data, {'global': errors})
        else:
            return HttpResponseRedirect(parent.get_absolute_url())

    def create_node(self, item, parent_nh, user):
        errors = []
        slug = slugify(item['node_type']).replace("_", "-")
        meta_type = META_TYPES.get(item['node_type'], 'Physical')
        nh = None
        if item['node_type'] == 'Rack':
            try:
                nh = helpers.get_or_create_site_unique_node_handle(
                    user,
                    item['name'],
                    slug,
                    meta_type,
                    parent_nh)
            except Exception as e:
                errors.append('Could not get or create a {} named {}, got error: {}'.format(item['node_type'], item['name'], e))
        elif item['node_type'] in GENERIC_TYPES:
            nh = helpers.get_generic_node_handle(user,
                                                 item['name'],
                                                 slug,
                                                 meta_type)
        else:
            try:
                nh = helpers.create_unique_node_handle(user,
                                                    item['name'],
                                                    slug,
                                                    meta_type)
            except UniqueNodeError:
                # Should have been validated, but hey race conditions
                errors.append(u"Could not create a {} named '{}', since one already exist".format(item['node_type'], item['name']))

        if nh:
            helpers.dict_update_node(user,
                                     nh.handle_id,
                                     item,
                                     filtered_keys=['node_type',
                                                    'children',
                                                    'ports'])
            if item['node_type'] in HAS_RELATION:
                helpers.set_has(user, parent_nh.get_node(), nh.handle_id)
            else:
                helpers.set_location(user, nh.get_node(), parent_nh.handle_id)
            for child in item.get('children', []):
                cerrors = self.create_node(child, nh, user)
                errors += cerrors
        return errors

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ImportNodesView, self).dispatch(*args, **kwargs)
    # TODO: based on slug decide allowed node types


class ExportNodesView(View):
    def get(self, request, slug, handle_id):
        nh = get_object_or_404(NodeHandle, handle_id=handle_id)
        q = """
            MATCH p=(n:Node {handle_id: {handle_id}})-[r:Has|:Located_in*1..3]-(x)
            WHERE (not exists(x.operational_state) or x.operational_state <> 'Decommissioned')
            RETURN tail(nodes(p)) as nodes, labels(x) as labels
        """
        results = nc.query_to_list(nc.graphdb.manager, q, handle_id=nh.handle_id)
        output = self.extract_results(results)

        # Sorting output...
        helpers.sort_nicely(output, "name")
        for item in output:
            self.sort_data(item)
        json_result = json.dumps(output, indent=4)

        filename = u"{}.{}_export.json".format(nh.node_type, nh.node_name)

        resp = HttpResponse(json_result, content_type="application/json")
        resp['Content-Disposition'] = u'attachment; filename="{}"'.format(filename)
        return resp

    def sort_data(self, data):
        if data.get('children', None):
            helpers.sort_nicely(data['children'], "name")
        for child in data['children']:
            self.sort_data(child)

    def extract_results(self, results):
        tmp = {}
        output = []
        for result in results:
            handle_id = result['nodes'][-1]['handle_id']
            node = self.export_node(result)
            # Filter out unwanted nodes
            # TODO: Skip, should be handled by cypher
            if node['node_type'] not in EXPORT_FILTER:
                tmp[handle_id] = node
                if len(result['nodes']) == 1:
                    output.append(node)
                else:
                    for parent in reversed(result['nodes'][:-1]):
                        # Attach to nearest parent that not in EXPORT_FILTER
                        if parent['handle_id'] in tmp:
                            tmp[parent['handle_id']]['children'].append(node)
                            break
        return output

    def export_node(self, data, parent=None):
        node = {k: v for k, v in data['nodes'][-1].items() if k not in
                ['noclook_last_seen', 'noclook_auto_manage', 'handle_id']}
        node_type = data['labels'][-1]

        # Extra fields
        node['node_type'] = node_type.replace("_", " ")
        node['children'] = []
        form = VALIDATION_FORMS.get(node_type)
        template = node
        if form:
            template = {k: '' for k in form().fields.keys() if
                        not k.startswith("relationship_")}
            template.update(node)
        return template

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ExportNodesView, self).dispatch(*args, **kwargs)
