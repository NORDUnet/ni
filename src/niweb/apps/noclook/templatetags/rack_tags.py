from django import template
import re
from collections.abc import Iterable
from apps.noclook.templatetags.noclook_tags import noclook_node_to_link

register = template.Library()
RACK_SIZE_PX = 20
MARGIN_HEIGHT = 2


def _rack_unit_to_height(units):
    # for every unit over 1 add a 2 px margin
    margin = (units - 1) * MARGIN_HEIGHT
    return units * RACK_SIZE_PX + margin


def _equipment_spacer(units):
    return {
        'units': units,
        'spacer': True,
        'height': "{}px".format(_rack_unit_to_height(units)),
    }


def _rack_sort(item):
    # Sort by rack position, sencoded by unit size
    pos = int(item.get('node').data.get('rack_position', -1))
    size = int(item.get('node').data.get('rack_units', 0)) * -1

    return (pos, size)


def _equipment(item):
    data = item.get('node').data
    units = int(data.get('rack_units', 1))
    return {
        'units': units,
        'position': int(data.get('rack_position', 0) or 0),
        'position_end': units + int(data.get('rack_position', 1)) - 1,
        'height': "{}px".format(_rack_unit_to_height(units)),
        'sub_equipment': [],
        'is_back': data.get('rack_back'),
        'data': data,
    }


def place_equipment(view_data, current_idx, last_eq, result):
    spacing = view_data['position'] - current_idx
    if spacing < 0:
        # Equipment overlaps with previous
        last_eq['sub_equipment'].append(view_data)
    else:
        if spacing > 0:
            result.append(_equipment_spacer(spacing))
        result.append(view_data)
        new_idx = view_data['position'] + view_data['units']
        return new_idx, view_data
    return current_idx, last_eq


@register.inclusion_tag('noclook/tags/rack.html')
def noclook_rack(rack, equipment):
    if equipment:
        equipment.sort(key=_rack_sort)
    racked_equipment = []
    racked_equipment_back = []
    unracked_equipment = []

    # mem
    front_idx = 1
    front_last_eq = None
    back_idx = 1
    back_last_eq = None

    for item in equipment:
        view_data = _equipment(item)
        is_rack_front = not view_data.get('is_back')
        if view_data['position'] > 0:
            if is_rack_front:
                front_idx, front_last_eq = place_equipment(view_data, front_idx, front_last_eq, racked_equipment)
            else:
                back_idx, back_last_eq = place_equipment(view_data, back_idx, back_last_eq, racked_equipment_back)
        else:
            unracked_equipment.append(item)
    return {
        'rack_size': _rack_unit_to_height(rack.data.get('rack_units', 42)),
        'racked_equipment': racked_equipment,
        'racked_equipment_back': racked_equipment_back,
        'unracked_equipment': unracked_equipment,
    }


@register.filter
def rack_sort(equipment):
    if equipment:
        equipment.sort(key=_rack_sort, reverse=True)
    return equipment



class Floorplan():
    def __init__(self, width, height):
        self.floorplan = {}
        self.cols = range(1, width + 1)
        self.rows = range(1, height +1)
        self.unplaced = []

    def set_tile(self, x, y, tile):
        #TODO: check if inside floor grid
        if x == -1 or y == -1:
            self.unplaced += [tile]
        self.floorplan[(x,y)] = tile

    def get_tile(self, x, y):
        return self.floorplan.get((x,y))

    def add_node(self, node):
        if not node:
            return
        # if node has floorplan_x + floorplan_y
        if node.data.get('floorplan_x') and node.data.get('floorplan_y'):
            x = node.data.get('floorplan_x')
            y = node.data.get('floorplan_y')
        else:
            x, y = parse_xy(node.data.get('name'))
        self.set_tile(x, y, Tile(node))

    def add_door(self, x, y):
        door = Tile("Access Door")
        door.css_classes.append("door")
        self.set_tile(x, y, door)


    def tile_rows(self):
        tile_set = {}
        for row in self.rows:
            tile_set[row] = [ self.get_tile(col, row) for col in self.cols]
        return tile_set

class Tile():
    def __init__(self, content):
        self._content = content
        self.label = ''
        if hasattr(content, 'data'):
            self.label = content.data.get('label', '')
        self.css_classes = []
        if content:
            self.css_classes.append('occupied')

    def content(self):
        item = self._content
        if not item:
            result = u''
        elif isinstance(item, str):
            result = item
        elif isinstance(item, Iterable):
            if 'handle_id' in item:
                # item is a node
                result = noclook_node_to_link({}, item)
        elif item.data:
            result = noclook_node_to_link({}, item.data)
        return result

    def __str__(self):
        return self.content()

    def css(self):
        return ' '.join(self.css_classes)

ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
def parse_xy(s):
    # A0.03
    m = re.search(r'(^[a-zA-Z][0-9]?).([0-9][0-9]?)', s)
    if m:
        row_raw = m.group(1)
        col = int(m.group(2))
        row = ALPHABET.index(row_raw[0].upper()) +1
        if len(row_raw) == 2 and row_raw[1] != '0':
            row += 10
        return col, row
    return -1, -1


@register.inclusion_tag('noclook/tags/floorplan.html')
def noclook_floorplan(site):
    if not site:
        return
    row = site.data.get('floorplan_row')
    col = site.data.get('floorplan_col')
    if not (row and col):
        return

    floorplan = Floorplan(col, row)
    for r in site.get_has().get('Has'):
        floorplan.add_node(r.get('node'))

    door_x = site.data.get('floorplan_door_x')
    door_y = site.data.get('floorplan_door_y')
    if door_x and door_y:
        print("got door")
        floorplan.add_door(door_x, door_y)
    return {
        'floorplan': floorplan,
    }


@register.inclusion_tag('noclook/tags/floorplan_placement.html')
def noclook_floorplan_placement(site, field_x, field_y, title="Floorplan placement"):
    row = site.data.get('floorplan_row')
    col = site.data.get('floorplan_col')
    if not (row and col):
        return
    floorplan = Floorplan(col, row)

    for r in site.get_has().get('Has'):
        floorplan.add_node(r.get('node'))
    door_x = site.data.get('floorplan_door_x')
    door_y = site.data.get('floorplan_door_y')
    if door_x and door_y:
        print("got door")
        floorplan.add_door(door_x, door_y)


    return {
        'floorplan': floorplan,
        'field_x': field_x,
        'field_y': field_y,
        'title': title,
    }
