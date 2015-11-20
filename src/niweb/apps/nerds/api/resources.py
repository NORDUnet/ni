# -*- coding: utf-8 -*-

"""
API resources for scan feature

@author: markus
"""
from tastypie.resources import Resource, ModelResource
from tastypie.authentication import ApiKeyAuthentication
from tastypie.authorization import Authorization
from tastypie.exceptions import BadRequest

from ..nerds import NmapConsumer


class NerdsResource(Resource):
    class Meta:
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        list_allowed_methods=['post']
        detail_allowed_methods=None


    def obj_create(self, bundle, **kwargs):
        consumer = self.get_consumer(bundle.data)
        if consumer:
            consumer.process()
        else:
            raise BadRequest('Could not find a nerds consumer that matches supplied data')
    
    def get_consumer(self,data):
        consumer = None
        if "nmap_services_py" in data['host']:
            consumer = NmapConsumer(data)
        return consumer


