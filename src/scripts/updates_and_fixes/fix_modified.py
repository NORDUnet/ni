# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from apps.noclook.models import NodeHandle

for nh in NodeHandle.objects.all():
    try:
        latest_action = nh.action_object_actions.order_by('timestamp').reverse()[0]
        modified = latest_action.timestamp
        modifier = latest_action.actor
    except IndexError:
        modified = nh.created
        modifier = nh.creator

    NodeHandle.objects.filter(pk=nh.pk).update(modified=modified, modifier=modifier)