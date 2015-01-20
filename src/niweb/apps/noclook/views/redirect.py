# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.template import RequestContext
import ipaddr

from apps.noclook.models import NodeHandle
from apps.noclook import helpers
import norduniclient as nc


@login_required
def node_redirect(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    return redirect(nh.get_absolute_url(), True)
