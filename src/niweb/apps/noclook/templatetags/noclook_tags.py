from django import template
register = template.Library()

@register.inclusion_tag('type_menu.html')
def type_menu():
    '''
    Returns a list with all wanted NodeType objects for easy menu
    handling.
    Just chain .exclude(type='name') to remove unwanted types.
    '''
    from niweb.apps.noclook.models import NodeType
    types = NodeType.objects.exclude(type='PIC').exclude(type='Unit')
    return {'types': types}

@register.simple_tag
def noclook_node_to_url(node):
    '''
    Takes a node id as a string and returns the relative url for a node.
    '''
    try:
        import norduni_client as nc
    except ImportError:
        raise template.VariableDoesNotExist('Import error, can not import \
norduni_client module.')
        return ''
    return nc.get_node_url(node)