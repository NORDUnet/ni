
from django import template
import string
import random
from apps.noclook import forms

register = template.Library()
 
OPTIONS_MAP = {
  'operational_state': forms.OPERATIONAL_STATES,
  'port_type': forms.PORT_TYPES,
  'responsible_group': forms.RESPONSIBLE_GROUPS,
  'support_group': forms.RESPONSIBLE_GROUPS,
  'security_class': forms.SECURITY_CLASSES
}

def generate_id(length=5):
    return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(5))

@register.inclusion_tag('noclook/import/type_form.html', takes_context=True)
def type_form(context, item, idx=None, parent_id=None):
    id = u"{}{}".format(item["type"], idx)
    if parent_id:
      id = u"{}.{}".format(parent_id,id)
    return {'item': item, 'id': id, 'errors': context.get('errors', {})}

@register.inclusion_tag('noclook/import/input_field.html', takes_context=True)
def field_if(context, item, key, parent_id=None):
    if parent_id:
        name = u"{}.{}".format(parent_id, key)
    else:
        name = key
    label = key.replace("_"," ").capitalize()
    errors = context.get("errors", {}).get(name)
    return {'show': key in item, 'label': label,'val': item.get(key), 'name': name, 'errors': errors}
    
@register.inclusion_tag('noclook/import/select_field.html', takes_context=True)
def select_if(context, item, key, parent_id=None):
    if parent_id:
        name = u"{}.{}".format(parent_id, key)
    else:
        name = key
    label = key.replace("_"," ").capitalize()
    options = OPTIONS_MAP.get(key, [('', '---UNKNOWN FIELD--')])
    errors = context.get("errors", {}).get(name)
    return {'show': key in item, 'label': label,'val': item.get(key), 'name': name, 'options':options, 'errors': errors}
