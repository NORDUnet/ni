from django import template

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

register = template.Library()
register.simple_tag(niweb_url)
register.simple_tag(niweb_media_url)
