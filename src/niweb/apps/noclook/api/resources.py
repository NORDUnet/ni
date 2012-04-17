# -*- coding: utf-8 -*-
"""
Created on Thu Apr 12 15:56:38 2012

@author: lundberg
"""

from tastypie.resources import ModelResource
from tastypie import fields
from tastypie.http import HttpGone, HttpMultipleChoices
from tastypie.utils import trailing_slash
from tastypie.constants import ALL_WITH_RELATIONS
#from tastypie.authentication import ApiKeyAuthentication
from django.conf.urls import url
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.template.defaultfilters import slugify
from niweb.apps.noclook.models import NodeHandle, NodeType
from niweb.apps.noclook.helpers import node2dict

class NodeTypeResource(ModelResource):
    
    class Meta:
        queryset = NodeType.objects.all()
        resource_name = 'node_type'
        #authentication = ApiKeyAuthentication()  
    
    
    def override_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<slug>[-\w]+)/$" % self._meta.resource_name,
                self.wrap_view('dispatch_detail'), name="api_dispatch_detail"),
            url(r"^(?P<resource_name>%s)/(?P<slug>[-\w]+)/children%s$" % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_children'), name="api_get_children"),
        ]
    
    def get_children(self, request, **kwargs):
        try:
            obj = self.cached_obj_get(request=request,
                                      **self.remove_api_resource_names(kwargs))
        except ObjectDoesNotExist:
            return HttpGone()
        except MultipleObjectsReturned:
            return HttpMultipleChoices("More than one resource is found at this URI.")
        
        child_resource = NodeHandleResource()
        return child_resource.get_list(request, node_type=obj.pk)

    def dehydrate(self, bundle):
        bundle.data['resource_uri'] = bundle.data['resource_uri'].replace(
                           '/%d/' % bundle.obj.pk,'/%s/' % bundle.obj.slug)
        return bundle  


class NodeHandleResource(ModelResource):
    
    node_type = fields.ToOneField(NodeTypeResource, 'node_type') 
    
    class Meta:
        queryset = NodeHandle.objects.all()
        resource_name = 'node_handle'
        #authentication = ApiKeyAuthentication()
        

    def dehydrate(self, bundle):
        bundle.data['node_type'] = bundle.data['node_type'].replace(
                           '/%d/' % bundle.obj.node_type_id,
                           '/%s/' % slugify(bundle.obj.node_type))
        bundle.data['resource_uri'] = bundle.data['resource_uri'].replace(
                   '/%s/' % self.Meta.resource_name,
                   '/%s/' % slugify(bundle.obj.node_type))
        bundle.data['node'] = node2dict(bundle.obj.get_node())
        return bundle
        
	
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
           
