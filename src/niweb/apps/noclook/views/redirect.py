# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404, render
from django.http import Http404
from time import sleep

from apps.noclook.models import NodeHandle
from apps.noclook import helpers


@login_required
def node_redirect(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    return redirect(nh.get_absolute_url())


@login_required
def docker_image_by_tag_redirect(request, tag):
    try:
        nh = NodeHandle.objects.get(node_name=tag)
        return redirect(nh.get_absolute_url())
    except NodeHandle.DoesNotExist:
        pass
    results = helpers.docker_images_by_tag(tag)
    if len(results) == 1:
        return redirect(results[0].get_absolute_url())
    if len(results) <= 0:
        raise Http404
    # render links
    return render(request, 'noclook/docker_image_by_tag.html', {'tag': tag, 'nodes': results})


@login_required
def node_slow_redirect(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    sleep(10)
    return redirect(nh.get_absolute_url())
