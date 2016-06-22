from django import template
from apps.noclook.templatetags.noclook_tags import noclook_node_to_link

register = template.Library()

@register.simple_tag(takes_context=True)
def table_column(context,item):
    if not item:
        result = ''
    elif "handle_id" in item:
        # item is a node
        result = noclook_node_to_link(context, item)
    elif type(item) is list:
        result = "<br> ".join([table_column(context, i) for i in item])
    else:
        # Just print it
        result = item
    return result
