from __future__ import absolute_import
import collections

from django import template
from apps.noclook.templatetags.noclook_tags import noclook_node_to_link
from django.utils.safestring import mark_safe
from django.utils.html import format_html, format_html_join

register = template.Library()


@register.simple_tag(takes_context=True)
def table_column(context, item):
    if not item:
        result = u''
    elif type(item) is list:
        result = format_html_join(mark_safe(u'\n<br>'),
                                  u'{}', ([table_column(context, i)] for i in item))
    elif type(item) in (str, unicode):
        result = item
    elif isinstance(item, collections.Iterable):
        if "handle_id" in item:
            # item is a node
            result = noclook_node_to_link(context, item)
        elif "url" in item:
            # it is a 'link'
            result = format_html(u'<a href="{}">{}</a>', item.get('url', ''), item.get('name', ''))
        else:
            # fallback to default
            result = item
    else:
        # Just print it
        result = item
    return result


@register.simple_tag()
def info_row(header, item, postfix=u'', prefix=u''):
    result = u''
    if item:
        result = format_html(u'<tr><th>{}</th><td>{}{}{}</td></tr>', header, prefix, item, postfix)
    return result
