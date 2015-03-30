# -*- coding: utf-8 -*-
__author__ = 'lundberg'

import os
import sys

## Need to change this path depending on where the Django project is
## located.
base_path = '../../niweb/'
sys.path.append(os.path.abspath(base_path))
niweb_path = os.path.join(base_path, 'niweb')
sys.path.append(os.path.abspath(niweb_path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

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