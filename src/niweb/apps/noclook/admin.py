from apps.noclook.models import NodeHandle, NodeType
from django.contrib import admin

class NodeHandleAdmin(admin.ModelAdmin):
    list_filter = ('node_type', 'creator')

class NodeTypeAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('type',)}

admin.site.register(NodeHandle, NodeHandleAdmin)
admin.site.register(NodeType, NodeTypeAdmin)
