# -*- coding: utf-8 -*-

"""
API resources for scan feature

@author: markus
"""
from tastypie.resources import Resource, ModelResource
from tastypie.authentication import ApiKeyAuthentication
from tastypie.authorization import Authorization

from ..models import QueueItem

class ScanQueryItemResource(ModelResource):
    class Meta:
        queryset = QueueItem.objects.all()
        resource_name = "scan_queue"
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        filtering = {
            "status": {"exact"},
            "type": {"exact"},
        }
        ordering = ["-created_at"]

