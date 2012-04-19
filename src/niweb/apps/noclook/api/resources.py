# -*- coding: utf-8 -*-
"""
Created on Thu Apr 12 15:56:38 2012

@author: lundberg

For use with neo4j-embedded >= 1.7.M3.
"""

from tastypie.resources import Resource, ModelResource
from tastypie.bundle import Bundle
from tastypie import fields
from tastypie.http import HttpGone, HttpMultipleChoices
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.utils import trailing_slash
from tastypie.constants import ALL_WITH_RELATIONS
from tastypie.exceptions import NotFound
from tastypie.authentication import Authentication
from django.conf.urls import url
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.http import HttpResponseNotAllowed
from django.template.defaultfilters import slugify
from niweb.apps.noclook.models import NodeHandle, NodeType
from niweb.apps.noclook.helpers import item2dict
import norduni_client as nc

def handle_id2resource_uri(handle_id):
    '''
    Returns a  NodeHandleResource URI from a Neo4j node.
    '''
    if not handle_id:
        return 'Meta Node'
    # str() is a neo4j-embedded hack handle_id can be a java.lang.Integer.
    nh = NodeHandle.objects.get(pk=str(handle_id))
    view = 'api_dispatch_detail'
    kwargs = {                   
            'resource_name': slugify(nh.node_type),
            'pk': nh.handle_id
        }
    nhr = NodeHandleResource()
    if nhr._meta.urlconf_namespace:
        view = "%s:%s" % (nhr._meta.urlconf_namespace, view)
    if nhr._meta.api_name is not None:
            kwargs['api_name'] = nhr._meta.api_name
    return reverse(view, args=None, kwargs=kwargs)
    
    
class NodeTypeResource(ModelResource):
    
    node_handles = fields.ToManyField('niweb.apps.noclook.api.resources.NodeHandleResource', 
                                      'nodehandle_set', related_name='node_type')
    
    class Meta:
        queryset = NodeType.objects.all()
        resource_name = 'node_type'
        #authentication = ApiKeyAuthentication()  
    
    
    def override_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<slug>[-\w]+)/$" % self._meta.resource_name,
                self.wrap_view('dispatch_detail'), name="api_dispatch_detail"),
        ]
    
    def dehydrate(self, bundle):
        bundle.data['resource_uri'] = bundle.data['resource_uri'].replace(
                           '/%d/' % bundle.obj.pk,'/%s/' % bundle.obj.slug)
        return bundle  


class NodeHandleResource(ModelResource):
    
    node_type = fields.ToOneField(NodeTypeResource, 'node_type')
    node = fields.DictField(attribute='node', default={})
        
    class Meta:
        queryset = NodeHandle.objects.all()
        resource_name = 'node_handle'
        authentication = Authentication()


    def override_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/relationships%s$" % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_relationships'), name="api_get_relationships"),
        ]
    
    def get_relationships(self, request, **kwargs):
        try:
            obj = self.cached_obj_get(request=request,
                                      **self.remove_api_resource_names(kwargs))
        except ObjectDoesNotExist:
            return HttpGone()
        except MultipleObjectsReturned:
            return HttpMultipleChoices("More than one resource is found at this URI.")
        
        child_resource = RelationshipResource()
        return child_resource.get_list(request, parent_obj=obj.pk)
        
    def dehydrate_node(self, bundle):
        return item2dict(bundle.obj.get_node())
        
    def dehydrate_node_type(self, bundle):
        return bundle.data['node_type'].replace(
                                        '/%d/' % bundle.obj.node_type_id,
                                        '/%s/' % slugify(bundle.obj.node_type))

    def dehydrate(self, bundle):
        bundle.data['resource_uri'] = bundle.data['resource_uri'].replace(
                   '/%s/' % self.Meta.resource_name,
                   '/%s/' % slugify(bundle.obj.node_type))
        bundle.data['relationships'] = []
        rr = RelationshipResource()
        tmp_obj = RelationshipObject()
        for rel in bundle.obj.get_node().relationships:            
            tmp_obj.id = rel.id
            bundle.data['relationships'].append(rr.get_resource_uri(tmp_obj))
        return bundle


class RelationshipObject(object):
    def __init__(self, initial=None):
        self.__dict__['_data'] = {'properties':{}}

        if hasattr(initial, 'items'):
            self.__dict__['_data']['properties'] = initial

    def __getattr__(self, name):
        return self._data.get(name, None)

    def __setattr__(self, name, value):
        self.__dict__['_data'][name] = value

    def to_dict(self):
        return self._data


class RelationshipResource(Resource):
    
    id = fields.IntegerField(attribute='id')
    type = fields.CharField(attribute='type')
    start = fields.CharField(attribute='start')
    end = fields.CharField(attribute='end')
    properties = fields.DictField(attribute='properties')
    
    class Meta:
        resource_name = 'relationship'
        object_class = RelationshipObject

    def _new_rel_obj(self, rel):
        new_obj = RelationshipObject(initial=item2dict(rel))
        new_obj.id = rel.getId()
        new_obj.type = rel.type.name()
        new_obj.start = handle_id2resource_uri(
                                    rel.start.getProperty('handle_id', None))
        new_obj.end = handle_id2resource_uri(
                                    rel.end.getProperty('handle_id', None))
        return new_obj

    def get_resource_uri(self, bundle_or_obj):
        kwargs = {
            'resource_name': self._meta.resource_name,
        }
        if isinstance(bundle_or_obj, Bundle):
            kwargs['pk'] = bundle_or_obj.obj.id
        else:
            kwargs['pk'] = bundle_or_obj.id

        if self._meta.api_name is not None:
            kwargs['api_name'] = self._meta.api_name
        return self._build_reverse_url('api_dispatch_detail', kwargs=kwargs)
    
    def get_object_list(self, request, **kwargs):
        results = []
        if kwargs.get('parent_obj', None):
            nh = NodeHandle.objects.get(pk=kwargs['parent_obj'])
            parent = nh.get_node()
            for rel in parent.relationships:
                results.append(self._new_rel_obj(rel))
            return results
        else:
            raise ImmediateHttpResponse(HttpResponseNotAllowed(['POST']))
    
    def obj_get_list(self, request = None, **kwargs):
        return self.get_object_list(request, **kwargs)
        
    def obj_get(self, request = None, **kwargs):
        pk = int(kwargs['pk'])
        try:
            return self._new_rel_obj(nc.neo4jdb.relationships[pk])
        except KeyError:
            raise NotFound("Object not found") 
    
    def obj_create():
        pass
    
    def obj_update():
        pass
    
    def obj_delete_list():
        pass
    
    def obj_delete():
        pass
    
    def rollback():
        pass


class CableResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='cable')
        resource_name = 'cable'
        
        
class HostResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='host')
        resource_name = 'host'
        

class HostProviderResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='host-provider')
        resource_name = 'host-provider'
        

class HostServiceResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='host-service')
        resource_name = 'host-service'
        
        
class HostUserResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='host-user')
        resource_name = 'host-user'
        
        
class IPServiceResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='ip-service')
        resource_name = 'ip-service'
        
        
class ODFResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='odf')
        resource_name = 'odf'
        

class OpticalNodeResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='optical-node')
        resource_name = 'optical-node'
        

class PeeringPartnerResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='peering-partner')
        resource_name = 'peering-partner'
        
        
class PICResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='pic')
        resource_name = 'pic'
        
      
class PortResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='port')
        resource_name = 'port'
        

class RackResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='rack')
        resource_name = 'rack'
        
        
class RouterResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='router')
        resource_name = 'router'
        
        
class SiteResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='site')
        resource_name = 'site'
        
        
class SiteOwnerResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='site-owner')
        resource_name = 'site-owner'
        

class UnitResource(NodeHandleResource):

    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='unit')
        resource_name = 'unit'
           
