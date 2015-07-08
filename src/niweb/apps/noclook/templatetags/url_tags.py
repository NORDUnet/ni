from django import template
register = template.Library()


@register.simple_tag(takes_context=True)
def paginate_path(context, value, param="page"):
    """
      Adds or replaces a page param to the current page query params.
    """
    query = context['request'].GET.copy()

    query[param] = value
    return query.urlencode()
  
@register.simple_tag(takes_context=True)
def export_as(context, file_type, param_del=["page"]):
    if not file_type:
      return ""
    req = context['request']
    params = req.GET.copy()
    for param,val in  req.GET.items():
      if param in param_del or not val:
        del params[param]
    if req.path.endswith("/"):
        path = req.path[:-1]
    else:
        path = req.path
    path += "." + file_type
    if params:
        path +="?" + params.urlencode() 
    return path 

