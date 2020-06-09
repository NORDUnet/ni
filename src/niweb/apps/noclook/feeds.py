# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from actstream.managers import ActionManager, stream
from actstream.models import model_stream
from apps.noclook.models import NodeHandle
import apps.noclook.vakt.utils as sriutils
from actstream.models import Action as ActionModel
from django.db.models import Q


def context_feed(context_name, user=None):
    """
    Stream of most recent actions by any particular model and filter it
    by its context attribute
    """
    ret = ActionModel.objects.none()

    if user:
        # node events
        ret = model_stream(NodeHandle)

        # filter by context and readable ids
        readable_ids = sriutils.get_ids_user_canread(user)
        ret = ret.filter(
            Q(data__contains={'context_name': context_name}),
            Q(action_object_object_id__in=readable_ids))

        # add delete events
        del_qs = ActionModel.objects.filter(
            Q(data__contains={'context_name': context_name}),
            Q(public=True),
            Q(verb="delete")
        )

        ret = (ret | del_qs).distinct()

    return ret
