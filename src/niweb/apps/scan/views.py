from django.shortcuts import render
from django.views import generic
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages

from .models import QueueItem

# Create your views here.

class QueueIndexView(generic.ListView):
    template_name="scan/queue_index.html"
    context_object_name = "queue_list"

    def get_queryset(self):
        return QueueItem.objects.order_by("-created_at")[:10]

def host(request):
    if request.POST:
        if request.POST["data"]: 
            hostname = request.POST["data"]
            item = QueueItem(type="Host", data=hostname)
            item.save()
            # Do stuff with hostname
            messages.success(request, "Added {0} to the scan queue".format(hostname))
    else:
        messages.warning(request, "GET request not allowed")
    return HttpResponseRedirect(reverse("scan:queue"))
