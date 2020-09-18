from django.utils.text import slugify
from django.conf import settings


def brand(request):
    return {
        'noclook': {
            'brand': settings.BRAND,
            'brand_slug': slugify(settings.BRAND),
            'link_color': settings.LINK_COLOR,
            'link_hover': settings.LINK_HOVER,
            'logo_color': settings.LOGO_COLOR or '#4ba0e0',
            'logo_subtext': settings.LOGO_SUBTEXT,
        }
    }


def url_script_name(request):
    return {
        'script_name': settings.FORCE_SCRIPT_NAME,
    }
