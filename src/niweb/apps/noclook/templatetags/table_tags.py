from django import template
from apps.noclook.templatetags.noclook_tags import noclook_node_to_link

register = template.Library()

@register.simple_tag(takes_context=True)
def table_column(context,item):
    if not item:
        result = u''
    # Hot fix for production since type(dict) does not work
    elif type(item) is int:
        result = item
    elif type(item) is list:
        result = u'<br> '.join([table_column(context, i) for i in item])
    #TODO: type(item) is dict fails on production
    #elif type(item) is dict:
    elif "handle_id" in item:
        # item is a node
        result = noclook_node_to_link(context, item)
    elif "url" in item:
        # it is a 'link'
        result = u'<a href="{}">{}</a>'.format(item.get('url',''),item.get('name',''))
    else:
        # Just print it
        result = item
    return result
