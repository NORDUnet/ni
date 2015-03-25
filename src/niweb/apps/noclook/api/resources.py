# -*- coding: utf-8 -*-
"""
Created on Thu Apr 12 15:56:38 2012

@author: lundberg

For use with python-neo4jdb, norduniclient and neo4j >2.0
"""

from tastypie.resources import Resource, ModelResource
from tastypie.bundle import Bundle
from tastypie import fields, utils
from tastypie.http import HttpGone, HttpMultipleChoices, HttpApplicationError, HttpConflict
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.constants import ALL
from tastypie.exceptions import NotFound
from tastypie.utils import trailing_slash
from tastypie.authentication import ApiKeyAuthentication
from tastypie.authorization import Authorization
from django.contrib.auth.models import User
from django.conf.urls import url
from django.core.urlresolvers import reverse, resolve, NoReverseMatch
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.http import HttpResponseNotAllowed, HttpResponse
from django.template.defaultfilters import slugify
from apps.noclook.models import NodeHandle, NodeType, NordunetUniqueId
from apps.noclook import forms
from apps.noclook import helpers
from apps.noclook import unique_ids
import norduniclient as nc
from norduniclient.exceptions import NodeNotFound
import logging

neo4jdb = nc.init_db()  # Open a separate manager for the REST API

logger = logging.getLogger('api_resources')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


def handle_id2resource_uri(handle_id):
    """
    Returns a NodeHandleResource URI from a Neo4j node.
    """
    nh = NodeHandle.objects.get(pk=handle_id)
    view = 'api_dispatch_detail'
    nhr = NodeHandleResource()
    kwargs = nhr.resource_uri_kwargs()
    kwargs['resource_name'] = slugify(nh.node_type)
    kwargs['pk'] = nh.handle_id
    if nhr._meta.urlconf_namespace:
        view = "%s:%s" % (nhr._meta.urlconf_namespace, view)
    if nhr._meta.api_name is not None:
        kwargs['api_name'] = nhr._meta.api_name
    try:
        return reverse(view, args=None, kwargs=kwargs)
    # If the object uses node_name as unique id.
    except NoReverseMatch:
        kwargs.pop('pk', None)
        kwargs['node_name'] = nh.node_name
        return reverse(view, args=None, kwargs=kwargs)

    
def resource_uri2id(resource_uri):
    """
    Takes a resource uri and returns the id.
    """
    return resolve(resource_uri).kwargs.get('pk', None)


def raise_not_acceptable_error(message):
    """
    Raises Http406 error with message.

    :param message: Error message
    :return: None
    """
    class HttpMethodNotAcceptable(HttpResponse):
        status_code = 406

    raise ImmediateHttpResponse(
        HttpMethodNotAcceptable(message)
    )


def raise_conflict_error(message):
    """
    Raises Http409 error with message.

    :param message: Error message
    :return: None
    """
    raise ImmediateHttpResponse(
        HttpConflict(message)
    )


def raise_app_error(message):
    """
    Raises Http500 error with message.

    :param message: Error message
    :return: None
    """
    raise ImmediateHttpResponse(
        HttpApplicationError(message)
    )


class FullUserResource(ModelResource):
    
    class Meta:
        queryset = User.objects.all()
        resource_name = 'full_user'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        excludes = ['email', 'password', 'is_active', 'is_staff', 'is_superuser']
        filtering = {
            "username": ALL
        }
    
    created = fields.ToManyField('apps.noclook.api.resources.NodeHandleResource', 'creator', related_name='creator')
    modified = fields.ToManyField('apps.noclook.api.resources.NodeHandleResource', 'modifier', related_name='modifier')


class UserResource(ModelResource):
    class Meta:
        queryset = User.objects.all()
        resource_name = 'user'
        authorization = Authorization()
        authentication = ApiKeyAuthentication()
        excludes = ['email', 'password', 'is_staff', 'is_superuser']


class NodeTypeResource(ModelResource):
    
    node_handles = fields.ToManyField('apps.noclook.api.resources.NodeHandleResource',
                                      'nodehandle_set', related_name='node_type')
    
    class Meta:
        queryset = NodeType.objects.all()
        resource_name = 'node_type'
        authentication = ApiKeyAuthentication()
        authorization = Authorization() 

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<slug>[-\w]+)/$" % self._meta.resource_name,
                self.wrap_view('dispatch_detail'), name="api_dispatch_detail"),
        ]
    
    def dehydrate(self, bundle):
        bundle.data['resource_uri'] = bundle.data['resource_uri'].replace('/%d/' % bundle.obj.pk,
                                                                          '/%s/' % bundle.obj.slug)
        return bundle  


class NodeHandleResource(ModelResource):
    
    handle_id = fields.IntegerField(attribute='handle_id', readonly=True, unique=True)
    node_name = fields.CharField(attribute='node_name')
    node_type = fields.ForeignKey(NodeTypeResource, 'node_type')
    node_meta_type = fields.CharField(attribute='node_meta_type')
    creator = fields.ForeignKey(UserResource, 'creator')
    created = fields.DateTimeField(attribute='created', readonly=True)
    modifier = fields.ForeignKey(UserResource, 'modifier')
    modified = fields.DateTimeField(attribute='modified', readonly=True)
    node = fields.DictField(default={}, blank=True)
        
    class Meta:
        api_name = 'v1'
        queryset = NodeHandle.objects.all()
        resource_name = 'node_handle'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        include_absolute_url = True
        always_return_data = True
        filtering = {
            "node_name": ALL,
        }

    def obj_create(self, bundle, **kwargs):
        bundle = super(NodeHandleResource, self).obj_create(bundle, **kwargs)
        return self.hydrate_node(bundle)

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/relationships/(?P<rel_type>\w[\w]*)%s$" % (
                self._meta.resource_name, utils.trailing_slash()),
                self.wrap_view('get_relationships'), name="api_get_relationships"),
            url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/relationships%s$" % (
                self._meta.resource_name, utils.trailing_slash()),
                self.wrap_view('get_relationships'), name="api_get_relationships"),
        ]
    
    def get_relationships(self, request, **kwargs):
        rel_type = kwargs.get('rel_type', None)
        if rel_type:
            kwargs.pop('rel_type', None)
        try:
            data = {'pk': kwargs['pk']}
            if getattr(self._meta, 'pk_field', 'pk') != 'pk':
                kwargs[self._meta.pk_field] = kwargs['pk']
                data = {self._meta.pk_field: kwargs['pk']}
                kwargs.pop('pk', None)
            bundle = self.build_bundle(data, request=request)
            obj = self.cached_obj_get(bundle=bundle, **self.remove_api_resource_names(kwargs))
            kwargs = {
                'parent_obj': obj.pk
            }
        except ObjectDoesNotExist:
            return HttpGone()
        except MultipleObjectsReturned:
            return HttpMultipleChoices("More than one resource is found at this URI.")
        if rel_type:
            kwargs['rel_type'] = rel_type
        child_resource = RelationshipResource()
        return child_resource.get_list(request, **kwargs)

    def dehydrate_node(self, bundle):
        return bundle.obj.get_node().data
        
    def hydrate_node(self, bundle):
        try:
            node = bundle.obj.get_node()
            if bundle.data.get('node'):
                node.data.update(bundle.data.get('node'))
                helpers.dict_update_node(bundle.request.user, node.handle_id, node.data, node.data.keys())
        except NodeNotFound:
            # Node is not yet created, obj_create will take care of that.
            pass
        return bundle

    def dehydrate_node_type(self, bundle):
        return bundle.data['node_type'].replace('/%d/' % bundle.obj.node_type_id,
                                                '/%s/' % slugify(bundle.obj.node_type))

    def dehydrate(self, bundle):
        bundle.data['relationships'] = []
        rr = RelationshipResource()
        tmp_obj = RelationshipObject()
        relationships = bundle.obj.get_node().relationships
        for key in relationships.keys():
            for rel in relationships.get(key, []):
                tmp_obj.id = rel['relationship_id']
                bundle.data['relationships'].append(rr.get_resource_uri(tmp_obj))
        return bundle

    def resource_uri_kwargs(self, bundle_or_obj=None):
        """
        Changing kwargs for uri so that the url resolve works.
        Traversing bundle_or_obj in case we're using related objects.
        Removing "pk" in case we're using our own field.
        """
        kwargs = super(NodeHandleResource, self).resource_uri_kwargs(bundle_or_obj)
        if bundle_or_obj is not None and getattr(self._meta, 'pk_field', 'pk') != 'pk':
            value = bundle_or_obj
            if isinstance(bundle_or_obj, Bundle):
                value = bundle_or_obj.obj
            for attribute in self._meta.pk_field.split("__"):
                value = getattr(value, attribute)
            kwargs[self._meta.pk_field] = value
            kwargs.pop('pk', None)
        return kwargs

    def base_urls(self):
        """
        Overriding base_urls to make sure that the old pk regex is not
        included anymore. api_get_multiple needs to be removed (in our
        case because we're not using continuous numbers) and
        api_dispatch_detail needs to be changed.
        """
        urls = super(NodeHandleResource, self).base_urls()
        if getattr(self._meta, 'pk_field', 'pk') != 'pk':
            urls = [x for x in urls if (x.name != "api_get_multiple" and x.name != "api_dispatch_detail")]
            urls += [
                url(r"^(?P<resource_name>%s)/(?P<%s>%s)%s$" % (self._meta.resource_name, self._meta.pk_field,
                                                               self._meta.pk_field_regex, trailing_slash()),
                    self.wrap_view('dispatch_detail'), name="api_dispatch_detail")
            ]
        return urls


class RelationshipObject(object):
    
    def __init__(self, initial=None):
        self.__dict__['_data'] = {'properties': {}}
        
        if hasattr(initial, 'items'):
            self.__dict__['_data'] = initial

    def __getattr__(self, name):
        return self._data.get(name, None)

    def __setattr__(self, name, value):
        self.__dict__['_data'][name] = value

    def to_dict(self):
        return self._data


class RelationshipResource(Resource):
    
    id = fields.IntegerField(attribute='id', readonly=True, unique=True)
    type = fields.CharField(attribute='type')
    start = fields.CharField(attribute='start')
    end = fields.CharField(attribute='end')
    properties = fields.DictField(attribute='properties', default={}, blank=True)
    
    class Meta:
        resource_name = 'relationship'
        object_class = RelationshipObject
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']

    def _new_obj(self, rel):
        new_obj = RelationshipObject()
        new_obj.id = rel.id
        new_obj.type = rel.type
        new_obj.properties.update(rel.data)
        new_obj.start = handle_id2resource_uri(rel.start)
        new_obj.end = handle_id2resource_uri(rel.end)
        return new_obj

    def get_resource_uri(self, bundle_or_obj=None, url_name='api_dispatch_detail'):
        if not bundle_or_obj:
            return super(RelationshipResource, self).get_resource_uri()
        kwargs = {
            'resource_name': self._meta.resource_name,
        }
        if isinstance(bundle_or_obj, Bundle):
            kwargs['pk'] = bundle_or_obj.obj.id
        else:
            kwargs['pk'] = bundle_or_obj.id
        if self._meta.api_name is not None:
            kwargs['api_name'] = self._meta.api_name
        try:
            return self._build_reverse_url('api_dispatch_detail', kwargs=kwargs)
        except NoReverseMatch:
            return ''
    
    def get_object_list(self, request, **kwargs):
        results = []
        if kwargs.get('parent_obj', None):
            rel_type = kwargs.get('rel_type', None)
            nh = NodeHandle.objects.get(pk=kwargs['parent_obj'])
            relationships = nh.get_node().relationships
            if rel_type:
                keys = [rel_type]
            else:
                keys = relationships.keys()
            for key in keys:
                for item in relationships.get(key, []):
                    relationship = nc.get_relationship_model(neo4jdb, item['relationship_id'])
                    results.append(self._new_obj(relationship))
            return results
        else:
            raise ImmediateHttpResponse(HttpResponseNotAllowed(['POST']))
    
    def obj_get_list(self, request=None, **kwargs):
        return self.get_object_list(request, **kwargs)
        
    def obj_get(self, request=None, **kwargs):
        pk = int(kwargs['pk'])
        try:
            return self._new_obj(nc.get_relationship_model(neo4jdb, pk))
        except KeyError:
            raise NotFound("Object not found")

    def obj_create(self, bundle, **kwargs):
        start_pk = resource_uri2id(bundle.data['start'])
        start_nh = NodeHandle.objects.get(pk=start_pk)
        start_node = start_nh.get_node()
        end_pk = resource_uri2id(bundle.data['end'])
        end_nh = NodeHandle.objects.get(pk=end_pk)
        end_node = end_nh.get_node()
        rel = nc.create_relationship(neo4jdb, start_node, end_node, bundle.data['type'])
        nc.set_relationship_properties(neo4jdb, rel, bundle.data['properties'])
        bundle.obj = self._new_obj(rel)
        return bundle

    def obj_update(self, bundle, **kwargs):
        helpers.dict_update_relationship(neo4jdb, kwargs['pk'], bundle.data['properties'],
                                   bundle.data['properties'].keys())
        updated_rel = nc.get_relationship_model(neo4jdb, kwargs['pk'])
        bundle.obj = self._new_obj(updated_rel)
        return bundle

    def obj_delete(self, request=None, **kwargs):
        helpers.delete_relationship(request.user, kwargs['pk'])

    def obj_delete_list(self, bundle, **kwargs):
        pass

    def rollback(self, bundle, **kwargs):
        pass


class CableResource(NodeHandleResource):

    node_name = fields.CharField(attribute='node_name')
    cable_type = fields.CharField(attribute='cable_type', help_text='Choices {choices}'.format(
        choices=[choice[0] for choice in forms.CABLE_TYPES]), blank=True, null=True)
    end_points = fields.ListField(help_text='[{"device": "", "device_type": "", "port": ""},]', blank=True, null=True)
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='cable')
        resource_name = 'cable'
        pk_field = 'node_name'
        pk_field_regex = '[-\w]+'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        include_absolute_url = True
        always_return_data = True
        allowed_methods = ['get', 'put', 'post', 'patch']
        filtering = {
            "node_name": ALL,
        }

    def _initial_form_data(self, bundle):
        initial_data = {
            'node_type': '/api/v1/node_type/cable/',
            'node_meta_type': 'Physical',
        }
        return initial_data

    def obj_create(self, bundle, **kwargs):
        try:
            node_type = helpers.slug_to_node_type(self.Meta.resource_name, create=True)
            NodeHandle.objects.get(node_name=bundle.data['node_name'], node_type=node_type)
            raise_conflict_error('Cable ID (%s) is already in use.' % bundle.data['node_name'])
        except NodeHandle.DoesNotExist:
            bundle.data.update(self._initial_form_data(bundle))
            bundle.data['name'] = bundle.data['node_name']
            form = forms.NewCableForm(bundle.data)
            if form.is_valid():
                bundle.data.update({
                    'node_name': form.cleaned_data['name'],
                    'creator': '/api/%s/user/%d/' % (self._meta.api_name, bundle.request.user.pk),
                    'modifier': '/api/%s/user/%d/' % (self._meta.api_name, bundle.request.user.pk),
                })
                node_data = bundle.data.get('node', {})
                node_data.update({'cable_type': form.cleaned_data['cable_type']})
                bundle.data['node'] = node_data
                del bundle.data['name']
                # Create the new cable
                bundle = super(NodeHandleResource, self).obj_create(bundle, **kwargs)
                # Depend the created service on provided end points
                end_point_nodes = self.get_end_point_nodes(bundle)
                node = bundle.obj.get_node()
                for end_point in end_point_nodes:
                    helpers.set_connected_to(bundle.request.user, node, end_point.handle_id)
                return self.hydrate_node(bundle)
            else:
                raise_not_acceptable_error(["%s is missing or incorrect." % key for key in form.errors.keys()])

    def obj_update(self, bundle, **kwargs):
        bundle = super(CableResource, self).obj_update(bundle, **kwargs)
        end_point_nodes = self.get_end_point_nodes(bundle)
        node = bundle.obj.get_node()
        if end_point_nodes:
            for result in node.relations.get('Connected_to', []):
                helpers.delete_relationship(bundle.request.user, result['relationship_id'])
            for end_point in end_point_nodes:
                helpers.set_connected_to(bundle.request.user, node, end_point.handle_id)
        return bundle

    def dehydrate(self, bundle):
        bundle = super(CableResource, self).dehydrate(bundle)
        bundle.data['cable_type'] = bundle.data['node'].get('cable_type', None)
        bundle.data['object_path'] = bundle.data['absolute_url']
        del bundle.data['absolute_url']
        return bundle

    def get_end_point_nodes(self, bundle):
        end_point_nodes = []
        for end_point in bundle.data.get('end_points', []):
            try:
                port_node = self.get_port(bundle, end_point['device'], end_point['device_type'], end_point['port'])
                end_point_nodes.append(port_node)
            except ObjectDoesNotExist:
                raise_not_acceptable_error('End point %s not found.' % end_point)
        return end_point_nodes

    def get_port(self, bundle, device_name, device_type, port_name):
        node_type = helpers.slug_to_node_type(slugify(device_type), create=True)
        parent_node = nc.get_unique_node_by_name(neo4jdb, device_name, node_type.type)
        if not parent_node:
            raise_not_acceptable_error("End point {0} {1} not found.".format(device_type, device_name))
        result = parent_node.get_port(port_name).get('Has', [])
        if len(result) > 1:
            raise_not_acceptable_error('Multiple port objects returned for a unique port name.')
        if result:
            port_node = result[0]['node']
        else:
            port_node = helpers.create_port(parent_node, port_name, bundle.request.user)
        return port_node


class NordunetCableResource(CableResource):

    node_name = fields.CharField(attribute='node_name', blank=True, null=True, default=None)

    class Meta(CableResource.Meta):
        resource_name = 'nordunet-cable'

    def obj_create(self, bundle, **kwargs):
        try:
            if bundle.data.get('node_name', None):
                if unique_ids.is_free_unique_id(NordunetUniqueId, bundle.data['node_name']):
                    bundle.data['name'] = bundle.data['node_name']
                else:
                    raise_conflict_error('Cable ID (%s) is already in use.' % bundle.data['node_name'])

            form = forms.NewNordunetCableForm(bundle.data)
            if form.is_valid():
                bundle.data.update({
                    'node_name': form.cleaned_data['name'],
                })
                return super(NordunetCableResource, self).obj_create(bundle, **kwargs)
        except KeyError as e:
            raise_not_acceptable_error('%s is missing.' % e)


class CustomerResource(NodeHandleResource):
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='customer')
        resource_name = 'customer'
        pk_field = 'node_name'
        pk_field_regex = '[-\w]+'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }


class EndUserResource(NodeHandleResource):
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='end-user')
        resource_name = 'end-user'
        pk_field = 'node_name'
        pk_field_regex = '[-\w]+'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }


class ExternalEquipmentResource(NodeHandleResource):

    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='external-equipment')
        resource_name = 'external-equipment'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }


class FirewallResource(NodeHandleResource):

    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='firewall')
        resource_name = 'firewall'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }


class HostResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='host')
        resource_name = 'host'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }
        

class HostProviderResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='host-provider')
        resource_name = 'host-provider'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }
        

class HostServiceResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='host-service')
        resource_name = 'host-service'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }
        
        
class HostUserResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='host-user')
        resource_name = 'host-user'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }
        
        
class ODFResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='odf')
        resource_name = 'odf'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }


class OpticalLinkResource(NodeHandleResource):

    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='optical-link')
        resource_name = 'optical-link'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }


class OpticalMultiplexSectionResource(NodeHandleResource):
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='optical-multiplex-section')
        resource_name = 'optical-multiplex-section'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }


class OpticalNodeResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='optical-node')
        resource_name = 'optical-node'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }


class OpticalPathResource(NodeHandleResource):

    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='optical-path')
        resource_name = 'optical-path'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }


class PDUResource(NodeHandleResource):

    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='pdu')
        resource_name = 'pdu'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }


class PeeringGroupResource(NodeHandleResource):

    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='peering-group')
        resource_name = 'peering-group'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }


class PeeringPartnerResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='peering-partner')
        resource_name = 'peering-partner'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }


class ProviderResource(NodeHandleResource):

    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='provider')
        resource_name = 'provider'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }
        
      
class PortResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='port')
        resource_name = 'port'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }
        

class RackResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='rack')
        resource_name = 'rack'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }
        
        
class RouterResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='router')
        resource_name = 'router'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }


class ServiceResource(NodeHandleResource):

    node_name = fields.CharField(attribute='node_name', blank=True)
    node_type = fields.ForeignKey(NodeTypeResource, 'node_type', blank=True)
    node_meta_type = fields.CharField(attribute='node_meta_type', blank=True)
    creator = fields.ForeignKey(UserResource, 'creator', blank=True)
    modifier = fields.ForeignKey(UserResource, 'modifier', blank=True)
    # Service specific fields
    description = fields.CharField(blank=True, null=True)
    operational_state = fields.CharField(blank=True, null=True,
                                help_text='Choices: In service, Reserved, Decommissioned, Testing')

    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='service')
        resource_name = 'service'
        pk_field = 'node_name'
        pk_field_regex = '[-\w]+'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post', 'patch']
        include_absolute_url = True
        always_return_data = True
        filtering = {
            "node_name": ALL,
        }

    def obj_update(self, bundle, **kwargs):
        bundle = super(ServiceResource, self).obj_update(bundle, **kwargs)
        node = bundle.obj.get_node()
        data = node.data
        data.update(bundle.data)
        form = forms.EditServiceForm(data)
        if form.is_valid():
            helpers.form_update_node(bundle.request.user, node.handle_id, form)
        else:
            raise_not_acceptable_error(["%s is missing or incorrect." % key for key in form.errors.keys()])
        return bundle

    def hydrate_node(self, bundle):
        bundle = super(ServiceResource, self).hydrate_node(bundle)
        return bundle

    def dehydrate(self, bundle):
        bundle = super(ServiceResource, self).dehydrate(bundle)
        bundle.data['description'] = bundle.data['node'].get('description', None)
        bundle.data['operational_state'] = bundle.data['node'].get('operational_state', None)
        bundle.data['object_path'] = bundle.data['absolute_url']
        del bundle.data['absolute_url']
        return bundle


class ServiceL2VPNResource(ServiceResource):

    node_name = fields.CharField(attribute='node_name')
    operational_state = fields.CharField(help_text='Choices: In service, Reserved, Decommissioned, Testing')
    vrf_target = fields.CharField()
    route_distinguisher = fields.CharField()
    vpn_type = fields.CharField(help_text='Choices: l2vpn, interface-switch')
    end_points = fields.ListField(help_text='[{"device": "", "port": ""},]')

    class Meta(ServiceResource.Meta):
        resource_name = 'l2vpn'

    def _initial_form_data(self, bundle):
        initial_data = {
            'node_type': '/api/v1/node_type/service/',
            'node_meta_type': 'Logical',
        }
        try:
            vpn_type = bundle.data['vpn_type'].lower()
            if vpn_type == 'l2vpn':
                initial_data['service_type'] = 'L2VPN'
            elif vpn_type == 'interface-switch':
                initial_data['service_type'] = 'Interface Switch'
            else:
                raise_not_acceptable_error('KeyError: vpn_type %s not recognized.' % vpn_type)
        except KeyError as e:
            raise_not_acceptable_error('%s is missing or incorrect.' % e)
        return initial_data

    def obj_create(self, bundle, **kwargs):
        bundle.data.update(self._initial_form_data(bundle))
        try:
            if unique_ids.is_free_unique_id(NordunetUniqueId, bundle.data['node_name']):
                bundle.data['name'] = bundle.data['node_name']
            else:
                raise_conflict_error('Service ID (%s) is already in use.' % bundle.data['node_name'])
        except KeyError as e:
            raise_not_acceptable_error('%s is missing.' % e)
        form = forms.NewNordunetL2vpnServiceForm(bundle.data)
        if form.is_valid():
            bundle.data.update({
                'node_name': form.cleaned_data['name'],
                'creator': '/api/%s/user/%d/' % (self._meta.api_name, bundle.request.user.pk),
                'modifier': '/api/%s/user/%d/' % (self._meta.api_name, bundle.request.user.pk)
            })
            node_data = bundle.data.get('node', {})
            node_data.update({
                'service_type': form.cleaned_data['service_type'],
                'service_class': form.cleaned_data['service_class'],
                'ncs_service_name': form.cleaned_data['ncs_service_name'],
                'vpn_type': form.cleaned_data['vpn_type'],
                'vlan': form.cleaned_data['vlan'],
                'vrf_target': form.cleaned_data['vrf_target'],
                'route_distinguisher': form.cleaned_data['route_distinguisher'],
                'operational_state': form.cleaned_data['operational_state'],
                'description': form.cleaned_data['description'],
            })
            bundle.data['node'] = node_data
            del bundle.data['name']
            # Ensure that we have all the data needed to create the L2VPN service
            end_point_nodes = self.get_end_point_nodes(bundle)
            # Create the new service
            bundle = super(ServiceL2VPNResource, self).obj_create(bundle, **kwargs)
            unique_ids.register_unique_id(NordunetUniqueId, bundle.data['node_name'])
            # Depend the created service on provided end points
            node = bundle.obj.get_node()
            for end_point in end_point_nodes:
                helpers.set_depends_on(bundle.request.user, node, end_point.handle_id)
            return self.hydrate_node(bundle)
        else:
            raise_not_acceptable_error(["%s is missing or incorrect." % key for key in form.errors.keys()])

    def obj_update(self, bundle, **kwargs):
        bundle = super(ServiceL2VPNResource, self).obj_update(bundle, **kwargs)
        end_point_nodes = self.get_end_point_nodes(bundle)
        node = bundle.obj.get_node()
        if end_point_nodes:
            for item in node.get_dependencies().get('Depends_on', []):
                helpers.delete_relationship(bundle.request.user, item['relationship_id'])
            for end_point in end_point_nodes:
                helpers.set_depends_on(bundle.request.user, node, end_point.handle_id)
        return bundle

    def dehydrate(self, bundle):
        bundle = super(ServiceL2VPNResource, self).dehydrate(bundle)
        bundle.data['vrf_target'] = bundle.data['node'].get('vrf_target', '')
        bundle.data['route_distinguisher'] = bundle.data['node'].get('route_distinguisher', '')
        bundle.data['vpn_type'] = bundle.data['node'].get('vpn_type', '')
        del bundle.data['end_points']
        return bundle

    def get_object_list(self, request, **kwargs):
        q = """
            MATCH (node:Service)
            WHERE node.service_type = "L2VPN" OR node.service_type = "Interface Switch"
            RETURN collect(node.handle_id) as handle_ids
            """
        hits = nc.query_to_dict(neo4jdb, q)
        return NodeHandle.objects.filter(pk__in=hits['handle_ids'])

    def obj_get_list(self, request=None, **kwargs):
        return self.get_object_list(request, **kwargs)

    def get_port(self, bundle, device_name, device_type, port_name):
        node_type = helpers.slug_to_node_type(slugify(device_type), create=True)
        parent_node = nc.get_unique_node_by_name(neo4jdb, device_name, node_type.type)
        if not parent_node:
            raise_not_acceptable_error("End point {0} {1} not found.".format(device_type, device_name))
        result = parent_node.get_port(port_name).get('Has', [])
        if len(result) > 1:
            raise_not_acceptable_error('Multiple port objects returned for a unique port name.')
        if result:
            port_node = result[0]['node']
        else:
            port_node = helpers.create_port(parent_node, port_name, bundle.request.user)
        return port_node

    def get_unit(self, bundle, port_node, unit_name):
        result = port_node.get_unit(unit_name).get('Part_of', [])
        if len(result) > 1:
            raise_not_acceptable_error('Multiple unit objects returned for a unique unit name.')
        if result:
            unit_node = result[0]['node']
        else:
            unit_node = helpers.create_unit(port_node, unit_name, bundle.request.user)
        return unit_node

    def get_vlan(self, bundle):
        vlan = bundle.data.get('vlan', None)
        if vlan:
            if '<->' in str(vlan):  # VLAN rewrite, VLAN needs to be specified on each end point.
                return None
            vlan = str(bundle.data.get('vlan')).split('-')[0]  # Use lowest vlan if a range, "5-10" -> "5"
        return vlan

    def get_end_point_nodes(self, bundle):
        end_point_nodes = []
        for end_point in bundle.data.get('end_points', []):
            try:
                port_node = self.get_port(bundle, end_point['device'], 'Router', end_point['port'])
                if end_point.get('unit', None):
                    unit_node = self.get_unit(bundle, port_node, end_point.get('unit'))
                elif end_point.get('vlan', None) or self.get_vlan(bundle):
                    vlan = end_point.get('vlan', None)
                    if not vlan:
                        vlan = self.get_vlan(bundle)
                    unit_node = self.get_unit(bundle, port_node, vlan)
                    unit_properties = {'vlan': vlan}
                    helpers.dict_update_node(bundle.request.user, unit_node.handle_id, unit_properties,
                                             unit_properties.keys())
                else:
                    # Use Unit 0 if nothing else is specified
                    unit_node = self.get_unit(bundle, port_node, '0')
                end_point_nodes.append(unit_node)
            except ObjectDoesNotExist:
                raise_not_acceptable_error('End point %s not found.' % end_point)
        return end_point_nodes


class SiteResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='site')
        resource_name = 'site'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }
        
        
class SiteOwnerResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='site-owner')
        resource_name = 'site-owner'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }


class SwitchResource(NodeHandleResource):
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='switch')
        resource_name = 'switch'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }


class UnitResource(NodeHandleResource):

    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='unit')
        resource_name = 'unit'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }


