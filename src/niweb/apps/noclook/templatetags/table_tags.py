from __future__ import absolute_import
import collections

from django import template
from apps.noclook.templatetags.noclook_tags import noclook_node_to_link
from neo4j.v1.types import Node

register = template.Library()


@register.simple_tag(takes_context=True)
def table_column(context, item):
    if not item:
        result = u''
    elif type(item) is list:
        result = u'<br> '.join([table_column(context, i) for i in item])
    elif type(item) in (str, unicode):
        result = item
    elif isinstance(item, collections.Iterable):
        if "handle_id" in item:
            # item is a node
            result = noclook_node_to_link(context, item)
        elif "url" in item:
            # it is a 'link'
            result = u'<a href="{}">{}</a>'.format(item.get('url', ''), item.get('name', ''))
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
        result = u'<tr><th>{}</th><td>{}{}{}</td></tr>'.format(header, prefix, item, postfix)
    return result
