from niweb.apps.noclook.models import NodeType
from niweb.apps.noclook.helpers import get_node_url
from django import template
register = template.Library()

@register.inclusion_tag('type_menu.html')
def type_menu():
    '''
    Returns a list with all wanted NodeType objects for easy menu
    handling.
    Just chain .exclude(type='name') to remove unwanted types.
    '''
    types = NodeType.objects.exclude(type='PIC').exclude(type='Unit').exclude(type='Port')
    return {'types': types}

@register.simple_tag
def noclook_node_to_url(node):
    '''
    Takes a node id as a string and returns the absolute url for a node.
    '''
    return get_node_url(node)