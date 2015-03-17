# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from apps.noclook.models import NodeHandle
from apps.noclook import helpers
import norduniclient as nc


@login_required
def generic_debug(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    return render_to_response('noclook/debug.html',
                              {'node_handle': nh, 'node': node},
                              context_instance=RequestContext(request))
