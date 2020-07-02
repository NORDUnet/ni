from django import template

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
