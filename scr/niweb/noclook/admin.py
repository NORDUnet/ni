from noclook.models import NodeHandle, NodeType
from django.contrib import admin

class NodeHandleAdmin(admin.ModelAdmin):
    {
    'fields': ('node_name', 'node_type', 'creator')
    }

class NodeTypeAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('type',)}

admin.site.register(NodeHandle)
admin.site.register(NodeType, NodeTypeAdmin)
