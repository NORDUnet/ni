from django.utils.text import slugify
from django.conf import settings


def brand(request):
    return {'noclook': {'brand': settings.BRAND, 'brand_slug': slugify(settings.BRAND)}}
