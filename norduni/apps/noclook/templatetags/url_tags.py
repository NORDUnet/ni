from django import template
register = template.Library()


@register.simple_tag(takes_context=True)
def paginate_path(context, value, param="page"):
    """
      Adds or replaces a page param to the current page query params.
    """
    query = context['request'].GET.copy()

    query[param] = value
    query = clean_queryparams(query)
    return query.urlencode()
  
@register.simple_tag(takes_context=True)
def export_as(context, file_type, param_del=["page"]):
    if not file_type:
      return ""
    req = context['request']
    params = req.GET.copy()
    for param in  param_del:
        if param in params:
          del params[param]
    params = clean_queryparams(params)
    if req.path.endswith("/"):
        path = req.path[:-1]
    else:
        path = req.path
    path += "." + file_type
    if params:
        path +="?" + params.urlencode() 
    return path 

def clean_queryparams(params):
    out = params.copy()
    for param,val in params.items():
      if not val:
        del out[param]
    return out


