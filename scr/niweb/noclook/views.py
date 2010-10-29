from django.shortcuts import render_to_response, get_object_or_404
from niweb.noclook.models import NodeHandle
import neo4jclient

def index(request):
    node_handle_list = NodeHandle.objects.all()
    return render_to_response('noclook/index.html',
        {'node_handle_list': node_handle_list})


def detail(request, handle_id, slug):
    nh = get_object_or_404(NodeHandle, pk=handle_id)
    # Get node from neo4j-database
    nc = neo4jclient.Neo4jClient()
    node = nc.get_node_by_id(nh.node_id)
    return render_to_response('noclook/detail.html',
        {'node_handle': nh, 'node': node})
