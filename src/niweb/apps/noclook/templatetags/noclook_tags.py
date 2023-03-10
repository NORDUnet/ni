from apps.noclook.models import NodeType
from apps.noclook.helpers import neo4j_data_age, neo4j_report_age, get_node_type
import norduniclient as nc
from datetime import datetime, timedelta
from django import template
import json
import re
from django.utils.html import escape, format_html
from dynamic_preferences.registries import global_preferences_registry


register = template.Library()


@register.inclusion_tag('type_menu.html')
def type_menu():
    """
    Returns a list with all wanted NodeType objects for easy menu
    handling.
    Just chain .exclude(type='name') to remove unwanted types.
    """
    types = NodeType.objects.exclude(hidden=True)
    return {'types': types}


@register.simple_tag(takes_context=True)
def noclook_node_to_url(context, handle_id):
    """
    Takes a node id as a string and returns the absolute url for a node.
    """
    if handle_id and not isinstance(handle_id, int):
        if hasattr(handle_id, 'handle_id'):
            handle_id = handle_id.handle_id
        if 'handle_id' in handle_id:
            handle_id = handle_id['handle_id']
    # handle fallback
    urls = context.get('urls')
    if urls and handle_id in urls:
        return urls.get(handle_id)
    else:
        return "/nodes/%s" % handle_id


@register.simple_tag(takes_context=True)
def noclook_node_to_link(context, node):

    if node and "handle_id" in node:
        url = noclook_node_to_url(context, node.get("handle_id"))
        result = format_html(u'<a class="handle" href="{}" title="{}">{}</a>', url, node.get("name"), node.get("name"))
    else:
        result = None
    return result


@register.simple_tag
def noclook_last_seen_to_dt(noclook_last_seen):
    """
    Returns noclook_last_seen property (ex. 2011-11-01T14:37:13.713434) as a
    datetime.datetime. If a datetime cant be made None is returned.
    """
    try:
        dt = datetime.strptime(noclook_last_seen, '%Y-%m-%dT%H:%M:%S.%f')
    except (ValueError, TypeError):
        dt = None
    return dt


@register.inclusion_tag('noclook/table_date_column.html')
def noclook_last_seen_as_td(date):
    """
    Returns noclook_last_seen property (ex. 2011-11-01T14:37:13.713434) as a
    table column.
    """
    if type(date) is datetime:
        last_seen = date    
    else:
        last_seen = noclook_last_seen_to_dt(date)
    return {'last_seen': last_seen}


@register.simple_tag
def timestamp_to_td(seconds):
    """
    Converts a UNIX timestamp to a timedelta object.
    """
    try:
        td = timedelta(seconds=float(seconds))
    except (AttributeError, ValueError, TypeError):
        td = None
    return td


@register.simple_tag
def noclook_has_expired(item):
    """
    Returns True if the item has a noclook_last_seen property and it has expired.
    """
    last_seen, expired = neo4j_data_age(item)
    return expired


@register.simple_tag
def noclook_get_model(handle_id):
    """
    :param handle_id: unique id
    :return: Node model
    """
    try:
        return nc.get_node_model(nc.graphdb.manager, handle_id)
    except nc.exceptions.NodeNotFound:
        return ''


@register.simple_tag(takes_context=True)
def noclook_get_type(context, handle_id):
    urls = context.get('urls')
    if urls and handle_id in urls:
        raw_type = urls[handle_id].split('/')[1]
        return raw_type.replace('-', ' ').title()
    else:
        try:
            return get_node_type(handle_id)
        except nc.exceptions.NodeNotFound:
            return ''


@register.simple_tag
def noclook_get_ports(handle_id):
    """
    Return port nodes that are either dependencies or connected to item. Also returns the
    ports top parent.
    :param handle_id: unique id
    :return: list
    """
    return nc.get_node_model(nc.graphdb.manager, handle_id).get_ports()


@register.simple_tag
def noclook_get_location(handle_id):
    return nc.get_node_model(nc.graphdb.manager, handle_id).get_location()


@register.simple_tag
def noclook_report_age(item, old, very_old):
    """
    :param item: Neo4j node
    :return: String, current, old, very_old
    """
    try:
        return neo4j_report_age(item, old, very_old)
    except TypeError:
        return ''


@register.simple_tag
def noclook_has_rogue_ports(handle_id):
    """
    :param handle_id: unique id
    :return: Boolean
    """
    q = """
        MATCH (host:Node {handle_id: $handle_id})<-[r:Depends_on]-()
        RETURN count(r.rogue_port) as count
        """
    d = nc.query_to_dict(nc.graphdb.manager, q, handle_id=handle_id)
    if d['count']:
        return True
    return False


class BlockVar(template.Node):

    def __init__(self, nodelist, context_var):
        self.nodelist = nodelist
        self.context_var = context_var

    def render(self, context):
        output = self.nodelist.render(context)
        context[self.context_var] = output
        return ''


@register.tag
def blockvar(parser, token):
    tagname, args= token.contents.split(None, 1)
    out_var = args.split(None,1)[0]
    nodelist = parser.parse("endblockvar",)
    parser.delete_first_token()
    return BlockVar(nodelist, out_var)


@register.inclusion_tag("noclook/table.html")
def table(th, tbody, *args, **kwargs):
    context = {'th': th, 'tbody': tbody}
    context.update(kwargs)
    return context


@register.inclusion_tag("noclook/table_search.html")
def table_search(target=None, field_id=None):
    return {"target": target, "field_id":field_id}


@register.filter
def as_json(value):
    return json.dumps(value, indent=4, sort_keys=True)


@register.simple_tag
def hardware_module(module, level=0):
    result = ""
    indent = " "*4*level
    keys = ["name",
            "version",
            "part_number",
            "part-number",
            "serial_number",
            "serial-number",
            "description",
            "hardware_description",
            "model_number",
            "model-number",
            "clei_code",
            "clei-code"]
    module_keys = ['modules', 'sub_modules', 'sub-modules']
    if module:
        result += "\n".join([u"{0}{1}: {2}".format(indent,key,module[key]) for key in keys if key in module ])
        if any(key in module for key in module_keys):
            result += "\n{0}Modules:\n\n".format(indent)
            for key in module_keys:
                result += "\n".join([ hardware_module(mod, level+1) for mod in module.get(key,[]) ])
        result += "\n{0}{1}\n".format(indent,"-"*8)
    
    return result


@register.simple_tag
def scan_data(host_node):
    return escape(json.dumps({"target": host_node.data.get("hostnames", ["unknown"])[0], "ipv4s": host_node.data.get("ip_addresses",[])}))


@register.inclusion_tag("noclook/dynamic_ports.html", takes_context=True)
def dynamic_ports(context,bulk_ports, *args, **kwargs):
    port_names, port_types = [], []
    if context.request.POST:
        port_names = context.request.POST.getlist("port_name")
        port_types = context.request.POST.getlist("port_type")
    ports = zip(port_names, port_types)
    bulk_ports.auto_id = False
    
    export = {}
    export.update({"bulk_ports": bulk_ports, "ports": ports})
    export.update(kwargs)
    return export


@register.simple_tag
def more_info_url(name):
    global_preferences = global_preferences_registry.manager()
    base_url = global_preferences['general__more_info_link']
    return u'{}{}'.format(base_url, name)


@register.tag
def accordion(parser, token):
    tokens = token.split_contents()
    title = tokens[1]
    _id = tokens[2]
    try:
        parent_id = tokens[3]
    except IndexError:
        parent_id = None
    nodelist = parser.parse("endaccordion",)
    parser.delete_first_token()
    return AccordionNode(_id, title, nodelist, parent_id)


def is_quoted(what):
    return re.match(r'^[\'"].*[\'"]$', what)


def resolve_arg(arg, context):
    if not arg:
        result = arg
    elif is_quoted(arg):
        result = arg[1:-1]
    else:
        result = template.Variable(arg).resolve(context)
    return result


class AccordionNode(template.Node):
    def __init__(self, _id, title, nodelist, parent_id=None, template='noclook/tags/accordion_tag.html'):
        self.nodelist = nodelist
        self.id = _id
        self.title = title
        self.template = template
        self.parent_id = parent_id

    def render(self, context):
        t = context.render_context.get(self)
        if t is None:
            t = context.template.engine.get_template(self.template)
            context.render_context[self] = t
        new_context = context.new({
            'accordion_id': resolve_arg(self.id, context),
            'accordion_parent_id': resolve_arg(self.parent_id, context),
            'accordion_title': resolve_arg(self.title, context),
            'csrf_token': context.get('csrf_token'),
            'body': self.nodelist.render(context)})
        return t.render(new_context)


@register.inclusion_tag('noclook/tags/json_combo.html')
def json_combo(form_field, urls, initial=None, skip_field=False):
    urls = [url.strip() for url in urls.split(",")]
    first_url = None

    if initial:
        if isinstance(initial, str):
            initial = initial.split(',')
        choices = [u"['{}',' {}']".format(val, val.title().replace("-", " ")) for val in initial]
        initial = u",\n".join(choices)
    else:
        first_url = urls[0]
        if len(urls) > 1:
            urls = urls[1:]
        else:
            urls = []
    return {
        'first_url': first_url,
        'initial': initial,
        'urls': urls,
        'field': form_field,
        'skip_field': skip_field,
    }


@register.inclusion_tag('noclook/tags/typeahead.html')
def typeahead(form_field, url, placeholder=None, has_parent=False, min_length=3, node_types=None):

    return {
        'url': url,
        'placeholder': placeholder,
        'field': form_field,
        'has_parent': has_parent,
        'min_length': min_length,
        'node_types': node_types,
    }


@register.filter
def attr(item, attr):
    return getattr(item, attr)


@register.filter
def has_label(item, label):
    return label in item.labels


@register.inclusion_tag('noclook/tags/ticket_info.html')
def ticket_info(services, tid='inTicketInfo'):
    """
    A helpful button for the NOC when they create service tickets
    """
    q = """
    MATCH (n:Node)<-[:Uses]-(u:Node) where n.handle_id in $handle_ids return DISTINCT(u.name) as Uses
    """
    d = nc.query_to_list(nc.graphdb.manager, q, handle_ids=[s['handle_id'] for s in services])

    impacted_users = {u['Uses'] for u in d}
    service_ids = {s.get('name') for s in services}
    impacts = ["{} - {}".format(s.get('name'), s.get('description')) for s in services]

    return {
        'impacted_users': impacted_users,
        'service_ids': service_ids,
        'impacts': impacts,
        'tid': tid,
    }


@register.filter
def split(item, sep):
    return item.split(sep)
