from django import template

register = template.Library()

@register.simple_tag
def niweb_url():
    """
    Returns the string contained in the setting NIWEB_URL.
    """
    try:
        from django.conf import settings
    except ImportError:
        raise template.VariableDoesNotExist('Import error, can not import settings from django.conf.')
        return ''
    if settings.NIWEB_URL is '':
        raise template.VariableDoesNotExist('Please set the NIWEB_URL in you settings file.')
    return settings.NIWEB_URL

@register.simple_tag
def niweb_media_url():
    """
    Returns the string contained in the setting NIWEB_MEDIA_URL.
    """
    try:
        from django.conf import settings
    except ImportError:
        raise template.VariableDoesNotExist('Import error, can not import settings from django.conf.')
        return ''
    if settings.NIWEB_MEDIA_URL is '':
        raise template.VariableDoesNotExist('Please set the NIWEB_MEDIA_URL in you settings file.')
    return settings.NIWEB_MEDIA_URL

@register.inclusion_tag('type_menu.html')
def type_menu():
    """
    Returns a list with all NodeType objects for easy menu handling.
    """
    from niweb.noclook.models import NodeType
    types = NodeType.objects.all()
    return {'types': types}


#register.simple_tag(niweb_url)
#register.simple_tag(niweb_media_url)
#register.simple_tag(node_type_list)
