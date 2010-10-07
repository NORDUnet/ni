from django.shortcuts import render_to_response, get_object_or_404
from niweb.noclook.models import NodeHandle
import neo4jclient

def index(request):
    node_handle_list = NodeHandle.objects.all()
    return render_to_response('noclook/index.html',
        {'node_handle_list': node_handle_list})


def detail(request, node_handle_id):
    nh = get_object_or_404(NodeHandle, pk=node_handle_id)
    # Get node from neo4j-database
    return render_to_response('noclook/detail.html',
        {'node_handle': nh, 'node': n})
