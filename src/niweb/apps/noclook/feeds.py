# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from actstream.managers import ActionManager, stream
from actstream.models import model_stream
from apps.noclook.models import NodeHandle


def context_feed(context_name, user=None):
    """
    Stream of most recent actions by any particular model and filter it
    by its context attribute
    """
    # get all NodeHande queryset
    ret = model_stream(NodeHandle)

    # filter by contextname
    ret = ret.filter(data__contains={'context_name': context_name})

    if user:
        ret = ret.filter(actor_object_id=user.pk)

    return ret
