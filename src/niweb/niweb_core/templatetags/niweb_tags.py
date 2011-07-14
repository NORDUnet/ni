from django import template

register = template.Library()

@register.simple_tag
def niweb_url():
    '''
    Returns the string contained in the setting NIWEB_URL.
    '''
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
    '''
    Returns the string contained in the setting NIWEB_MEDIA_URL.
    '''
    try:
        from django.conf import settings
    except ImportError:
        raise template.VariableDoesNotExist('Import error, can not import settings from django.conf.')
        return ''
    if settings.NIWEB_MEDIA_URL is '':
        raise template.VariableDoesNotExist('Please set the NIWEB_MEDIA_URL in you settings file.')
    return settings.NIWEB_MEDIA_URL
    
@register.simple_tag
def niweb_node_id_to_url(node_id):
    '''
    Takes a node id as a string and returns the relative url for a node.
    '''
    try:
        import norduni_client as nc
    except ImportError:
        raise template.VariableDoesNotExist('Import error, can not import norduni_client module.')
        return ''
    return nc.get_node_url(node_id)

#register.simple_tag(niweb_url)
#register.simple_tag(niweb_media_url)
#register.simple_tag(node_type_list)
