from apps.noclook.models import NodeHandle, NodeType
from django.contrib import admin

class NodeHandleAdmin(admin.ModelAdmin):
    list_filter = ('node_type', 'creator')
    actions = ['delete_object']
    
    # Remove the bulk delete option from the admin interface as it does not
    # run the NodeHandle delete-function.
    def get_actions(self, request):
        actions = super(NodeHandleAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions
        
    def delete_object(self, request, queryset):
        deleted = 0
        for obj in queryset:
            obj.delete()
            deleted += 1
        if deleted == 1:
            message_bit = "1 NodeHandle was"
        else:
            message_bit = "%s NodeHandles were" % deleted
        self.message_user(request, "%s successfully deleted." % message_bit)
    delete_object.short_description = "Deletes the selected NodeHandles using the delete method"
        

class NodeTypeAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('type',)}
    actions = ['delete_object']
    
    # Remove the bulk delete option from the admin interface as it does not
    # run the NodeHandle delete-function.
    def get_actions(self, request):
        actions = super(NodeTypeAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions
        
    def delete_object(self, request, queryset):
        deleted = 0
        for obj in queryset:
            obj.delete()
            deleted += 1
        if deleted == 1:
            message_bit = "1 NodeType was"
        else:
            message_bit = "%s NodeTypes were" % deleted
        self.message_user(request, "%s successfully deleted." % message_bit)
    delete_object.short_description = "Deletes the selected NodeType and all NodeHandles of that type"


admin.site.register(NodeHandle, NodeHandleAdmin)
admin.site.register(NodeType, NodeTypeAdmin)
