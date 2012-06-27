# -*- coding: utf-8 -*-
"""
Created on Thu Apr 12 15:56:38 2012

@author: lundberg

For use with neo4j-embedded >= 1.7.M3.
"""

from tastypie.resources import Resource, ModelResource
from tastypie.bundle import Bundle
from tastypie import fields, utils
from tastypie.http import HttpGone, HttpMultipleChoices
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.constants import ALL
from tastypie.exceptions import NotFound
from tastypie.authentication import ApiKeyAuthentication
from tastypie.authorization import Authorization
from django.contrib.auth.models import User
from django.conf.urls import url
from django.core.urlresolvers import reverse, resolve
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.http import HttpResponseNotAllowed
from django.template.defaultfilters import slugify
from niweb.apps.noclook.models import NodeHandle, NodeType
from niweb.apps.noclook.helpers import item2dict, update_noclook_auto_manage
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
    
def resource_uri2id(resource_uri):
    '''
    Takes a resource uri and returns the id.
    '''
    return resolve(resource_uri).kwargs.get('pk', None)
                            
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
    
    created = fields.ToManyField('niweb.apps.noclook.api.resources.NodeHandleResource', 
                                      'creator', related_name='creator')
    modified = fields.ToManyField('niweb.apps.noclook.api.resources.NodeHandleResource', 
                                      'modifier', related_name='modifier')

class UserResource(ModelResource):
    class Meta:
        queryset = User.objects.all()
        resource_name = 'user'
        authorization = Authorization()
        authentication = ApiKeyAuthentication()
        excludes = ['email', 'password', 'is_staff', 'is_superuser']

class NodeTypeResource(ModelResource):
    
    node_handles = fields.ToManyField('niweb.apps.noclook.api.resources.NodeHandleResource', 
                                      'nodehandle_set', related_name='node_type')
    
    class Meta:
        queryset = NodeType.objects.all()
        resource_name = 'node_type'
        authentication = ApiKeyAuthentication()
        authorization = Authorization() 
    
    
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
    
    handle_id = fields.IntegerField(attribute='handle_id', readonly=True, unique=True)
    node_id = fields.IntegerField(attribute='node_id', readonly=True)
    node_name = fields.CharField(attribute='node_name')
    node_type = fields.ForeignKey(NodeTypeResource, 'node_type')
    node_meta_type = fields.CharField(attribute='node_meta_type')
    creator = fields.ForeignKey(UserResource, 'creator')
    created = fields.DateTimeField(attribute='created', readonly=True)
    modifier = fields.ForeignKey(UserResource, 'modifier', blank=True,
                                 null=True)
    modified = fields.DateTimeField(attribute='modified', readonly=True)
    node = fields.DictField(attribute='node', default={}, blank=True)
        
    class Meta:
        queryset = NodeHandle.objects.all()
        resource_name = 'node_handle'
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post']
        filtering = {
            "node_name": ALL,
        }


    def obj_create(self, bundle, request=None, **kwargs):
        bundle = super(NodeHandleResource, self).obj_create(bundle, request,
                                                            **kwargs)
        return self.hydrate_node(bundle)

    def override_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/relationships%s$" % (self._meta.resource_name, utils.trailing_slash()),
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
        
    def hydrate_node(self, bundle):
        try:
            node = bundle.obj.get_node()
            nc.update_item_properties(nc.neo4jdb, node, 
                                      bundle.data['node'])
            update_noclook_auto_manage(nc.neo4j, node)
        except TypeError:
            # Node is not yet created, obj_create will take care of that.
            pass
        return bundle
        
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
    properties = fields.DictField(attribute='properties', default={},
                                  blank=True)
    
    class Meta:
        resource_name = 'relationship'
        object_class = RelationshipObject
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        allowed_methods = ['get', 'put', 'post', 'delete']

    def _new_obj(self, rel):
        new_obj = RelationshipObject()
        new_obj.id = rel.getId()
        new_obj.type = rel.type.name()
        new_obj.properties.update(item2dict(rel))
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
                results.append(self._new_obj(rel))
            return results
        else:
            raise ImmediateHttpResponse(HttpResponseNotAllowed(['POST']))
    
    def obj_get_list(self, request = None, **kwargs):
        return self.get_object_list(request, **kwargs)
        
    def obj_get(self, request = None, **kwargs):
        pk = int(kwargs['pk'])
        try:
            return self._new_obj(nc.neo4jdb.relationships[pk])
        except KeyError:
            raise NotFound("Object not found") 
    
    def obj_create(self, bundle, request=None, **kwargs):
        start_pk = resource_uri2id(bundle.data['start'])
        start_nh = NodeHandle.objects.get(pk=start_pk)
        start_node = start_nh.get_node()
        end_pk = resource_uri2id(bundle.data['end'])        
        end_nh = NodeHandle.objects.get(pk=end_pk)
        end_node = end_nh.get_node()
        rel = nc.create_relationship(nc.neo4jdb, start_node, end_node,
                                              bundle.data['type'])
        nc.update_item_properties(nc.neo4jdb, rel, bundle.data['properties'])
        update_noclook_auto_manage(nc.neo4jdb, rel)
        bundle.obj = self._new_obj(rel)
        return bundle
    
    def obj_update(self, bundle, request=None, **kwargs):
        rel = nc.get_relationship_by_id(nc.neo4jdb, kwargs['pk'])
        updated_rel = nc.update_item_properties(nc.neo4jdb, rel,
                                                bundle.data['properties'])
        update_noclook_auto_manage(nc.neo4jdb, updated_rel)                                        
        bundle.obj = self._new_obj(updated_rel)
        return bundle
    
    def obj_delete(self, request=None, **kwargs):
        rel = nc.get_relationship_by_id(nc.neo4jdb, kwargs['pk'])
        nc.delete_relationship(nc.neo4jdb, rel)
    
    def obj_delete_list():
        pass
    
    def rollback():
        pass


class CableResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='cable')
        resource_name = 'cable'
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
        
        
class IPServiceResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='ip-service')
        resource_name = 'ip-service'
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
        
        
class PICResource(NodeHandleResource):
    
    class Meta:
        queryset = NodeHandle.objects.filter(node_type__slug__exact='pic')
        resource_name = 'pic'
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
           
