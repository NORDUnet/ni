from django.conf import settings
import os
def page_flash(request):
    path = os.path.join(settings.NIWEB_ROOT, "niweb", "page_message.txt")
    msg = None
    if os.path.isfile(path):
        with open(path, 'r') as f:
            msg = f.read()
    return {'page_flash': msg}
