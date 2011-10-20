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
