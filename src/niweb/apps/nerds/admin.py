from django.contrib import admin
from django import forms
from .models import HostUserMap
from apps.noclook.models import NodeHandle


class HostUserMapForm(forms.ModelForm):
    class Meta:
        model=HostUserMap
        fields = '__all__'
        widgets = {
            'host_user': forms.Select(choices=[(node.node_name, node.node_name) for node in NodeHandle.objects.filter(node_type__type="Host User")])
        }
class HostUserMapAdmin(admin.ModelAdmin):
    list_display = ("domain", "host_user")
    form = HostUserMapForm


# Register your models here.
admin.site.register(HostUserMap, HostUserMapAdmin)
