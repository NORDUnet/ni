import collections
from django import template
from apps.noclook.templatetags.noclook_tags import noclook_node_to_link

register = template.Library()

@register.simple_tag(takes_context=True)
def table_column(context,item):
    if not item:
        result = u''
    elif type(item) is list:
        result = u'<br> '.join([table_column(context, i) for i in item])
    elif isinstance(item, collections.Iterable):
        if "handle_id" in item:
            # item is a node
            result = noclook_node_to_link(context, item)
        elif "url" in item:
            # it is a 'link'
            result = u'<a href="{}">{}</a>'.format(item.get('url',''),item.get('name',''))
        else:
            result = u''
    else:
        # Just print it
        result = item
    return result
