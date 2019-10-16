# -*- coding: utf-8 -*-
from time import sleep

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404

from apps.noclook.models import NodeHandle
from apps.noclook import helpers


@login_required
def node_redirect(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    return redirect(nh.get_absolute_url())


@login_required
def node_slow_redirect(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    sleep(10)
    return redirect(nh.get_absolute_url())


@login_required
def redirect_back(request):
    nexturl = request.GET.get('next')
    return redirect(nexturl)
