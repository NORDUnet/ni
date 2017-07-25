
from django import template
import string
import random
from django.utils.functional import lazy
from apps.noclook import forms, models

register = template.Library()


def choices(name):
    def f():
        return models.Dropdown.get(name).as_choices()
    return lazy(f, list)


OPTIONS_MAP = {
  'operational_state': choices('operational_states'),
  'port_type': choices('port_type'),
  'responsible_group': choices('responsible_groups'),
  'support_group': choices('responsible_groups'),
  'security_class': choices('security_classes'),
  'type': choices('optical_node_types')
}

def generate_id(length=5):
    return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(5))

@register.inclusion_tag('noclook/import/type_form.html', takes_context=True)
def type_form(context, item, idx=None, parent_id=None):
    id = u"{}{}".format(item["node_type"], idx)
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
