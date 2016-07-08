from __future__ import absolute_import

from django import template
from apps.noclook.templatetags.noclook_tags import noclook_node_to_link
from neo4j.v1.types import Node

register = template.Library()


@register.simple_tag(takes_context=True)
def table_column(context, item):
    if not item:
        return u''
    elif isinstance(item, basestring) or isinstance(item, int) or isinstance(item, bool):
        return item
    elif isinstance(item, list):
        return u'<br> '.join([table_column(context, i) for i in item])
    elif isinstance(item, dict) or isinstance(item, Node):
        if "handle_id" in item:
            # item is a node
            return noclook_node_to_link(context, item)
        elif "url" in item:
            # it is a 'link'
            return u'<a href="{}">{}</a>'.format(item.get('url', ''), item.get('name', ''))
    else:
        raise(Exception('Unhandled table column data: {!s} of type {!s}'.format(item, type(item))))

