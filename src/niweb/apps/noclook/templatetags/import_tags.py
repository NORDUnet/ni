
from django import template
import string
import random

register = template.Library()

@register.inclusion_tag('noclook/import/type_form.html')
def type_form(item):
    return {'item': item}

@register.inclusion_tag('noclook/import/input_field.html')
def field_if(item, key):
    id = 'id_'+''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(5))
    return {'show': key in item, 'key': key,'val': item.get(key), 'id': id}
    
