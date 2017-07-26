# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

from apps.noclook.models import NodeHandle


@login_required
def generic_debug(request, handle_id):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    node = nh.get_node()
    return render(request, 'noclook/debug.html',
                  {'node_handle': nh, 'node': node})
