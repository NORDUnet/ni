from django.utils.html import format_html
from django import template
from django.urls import reverse
from django.contrib.auth.models import User
from apps.userprofile.models import UserProfile

register = template.Library()


@register.simple_tag
def userprofile_link(user):
    # if user is django user, find profile..
    if isinstance(user, User):
        userprofile = UserProfile.objects.get(user=user)
    elif isinstance(user, UserProfile):
        # if profile just do the url lookup
        userprofile = user
        user = userprofile.user
    else:
        return None

    url = reverse('userprofile_detail', args=[userprofile.id])
    # return link
    return format_html('<a href="{url}">{name}</a>', url=url, name=user)
