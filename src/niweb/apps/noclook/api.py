# -*- coding: utf-8 -*-
"""
Created on Thu Apr 12 15:56:38 2012

@author: lundberg
"""

from tastypie.resources import ModelResource
from tastypie import fields
#from tastypie.authentication import ApiKeyAuthentication
from niweb.apps.noclook.models import NodeHandle, NodeType

class NodeTypeResource(ModelResource):
    
    class Meta:
        queryset = NodeType.objects.all()
        resource_name = 'node_type'
        #authentication = ApiKeyAuthentication()


class NodeHandleResource(ModelResource):
    
    node_type = fields.ForeignKey(NodeTypeResource, 'node_type')    
    
    class Meta:
        queryset = NodeHandle.objects.all()
        resource_name = 'node_handle'
        #authentication = ApiKeyAuthentication()