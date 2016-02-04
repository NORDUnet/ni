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

class ImportNodesView(View):
    def get(self, request, slug, handle_id):
        parent = get_object_or_404(NodeHandle, handle_id=handle_id)
        return render(request, 'noclook/import/upload.html')

    def post(self, request, slug, handle_id):
        parent = get_object_or_404(NodeHandle, handle_id=handle_id)
        if 'file' in  request.FILES:
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
        for key, val in sorted(request.POST.iteritems()):
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

    def convert_children(self,data):
        if 'children' in data:
            tmp = [v for k,v in sorted(data['children'].iteritems())]
        for child in tmp:
            self.convert_children(child)
        data['children'] = tmp


    def validate(self, data, parent_id=None):
        errors_out = {}
        for i, item in enumerate(data):
            form = VALIDATION_FORMS.get(item['type'])
            # Create item id
            item_id = u'{}{}'.format(item['type'], i+1)
            if parent_id:
                item_id = u'{}.{}'.format(parent_id, item_id)

            if form:
                f = form(item)
                for field, errors in f.errors.items():
                    idx = u"{}.{}".format(item_id, field)
                    errors_out[idx] = errors
            if item['type'] not in GENERIC_TYPES:
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
             slug = slugify(item['type'])
             node_type = helpers.slug_to_node_type(slug, create=True)
             try:
                 NodeHandle.objects.get(node_name=item['name'], node_type=node_type)
                 error  = "Must be unique."
             except NodeHandle.DoesNotExist:
                 pass
         return error


    def file(self, request, parent):
        data = json.load(request.FILES['file'])
        errors = self.validate(data)
        if 'import' in request.POST and not errors:
            return self.create(request, parent, data)
        else:
            return self.edit(request, parent, data, errors)

    def edit(self, request, parent, data, errors=None):
        return render(request, 'noclook/import/edit.html', {'parent': parent, 'data': data, 'errors': errors})
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
        slug = slugify(item['type'])
        meta_type = META_TYPES.get(item['type'], 'Physical')
        nh = None
        if item['type'] in GENERIC_TYPES:
            nh = helpers.get_generic_node_handle(user, item['name'], slug, meta_type)
        else:
            try:
                nh = helpers.get_unique_node_handle(user, item['name'], slug, meta_type)
            except UniqueNodeError:
                # Should have been validated, but hey race conditions
                errors.append(u"Could not create a {} named '{}', since one already exist".format(item['type'], item['name']))
        if nh:
            helpers.dict_update_node(user, nh.handle_id, item, filtered_keys=['type','children','ports'])
            if item['type'] in HAS_RELATION:
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
            RETURN tail(nodes(p)) as nodes, labels(x) as labels
        """
        results = nc.query_to_list(nc.neo4jdb, q, handle_id=nh.handle_id)
        output = self.extract_results(results)

        # Sorting output...
        helpers.sort_nicely(output, "name")
        for item in output:
            self.sort_data(item)
        json_result = json.dumps(output, indent=4)

        filename = "{}.{}_export.json".format(nh.node_type, nh.node_name)

        resp = HttpResponse(json_result, content_type="application/json")
        resp['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
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
            raw = result['nodes'][-1]
            node = self.export_node(result)
            depth = len(result['nodes'])
            tmp[raw['handle_id']] = node
            if len(result['nodes']) == 1:
                output.append(node)
            else:
                parent = result['nodes'][-2]
                tmp[parent['handle_id']]['children'].append(node)
        return output

    def export_node(self, data, parent=None):
        node = {k: v for k,v in data['nodes'][-1].items() if k not in ['noclook_last_seen', 'noclook_auto_manage', 'handle_id']}
        node_type = data['labels'][-1]

        #Extra fields
        node['type'] = node_type
        node['children'] = []
        form = VALIDATION_FORMS.get(node_type)
        template = node
        if form:
            template = {k: '' for k in form().fields.keys() if not k.startswith("relationship_")}
            template.update(node)
        return template


    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ExportNodesView, self).dispatch(*args, **kwargs)
