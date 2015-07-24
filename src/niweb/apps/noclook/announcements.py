from dynamic_preferences import global_preferences_registry


def page_flash(request):
    global_preferences = global_preferences_registry.manager()
    msg = global_preferences['announcements__page_flash_message']
    level = global_preferences['announcements__page_flash_message_level']
    return {'page_flash': {'level': level, 'message': msg}}
