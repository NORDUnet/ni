from django.contrib import admin
from tastypie.admin import ApiKeyInline
from tastypie.models import ApiAccess, ApiKey
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import NodeHandle, NodeType, UniqueIdGenerator, NordunetUniqueId, OpticalNodeType, ServiceType, ServiceClass

class UserModelAdmin(UserAdmin):
    inlines = [ApiKeyInline]

class NodeHandleAdmin(admin.ModelAdmin):
    list_filter = ('node_type', 'creator')
    search_fields = ['node_name']
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
    delete_object.short_description = "Delete the selected NodeHandle(s)"
        

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
    delete_object.short_description = "Delete the selected NodeType and all NodeHandles of that type"


class UniqueIdGeneratorAdmin(admin.ModelAdmin):
    readonly_fields=('last_id', 'next_id',)


class UniqueIdAdmin(admin.ModelAdmin):
    list_filter = ('reserved', 'created',)
    list_display = ('unique_id', 'reserve_message', 'created')
    readonly_fields=('unique_id',)
    search_fields = ['unique_id']

class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'service_class')

admin.site.register(NodeHandle, NodeHandleAdmin)
admin.site.register(NodeType, NodeTypeAdmin)
admin.site.register(ApiAccess)
admin.site.unregister(User)
admin.site.register(User, UserModelAdmin)
admin.site.register(UniqueIdGenerator, UniqueIdGeneratorAdmin)
admin.site.register(NordunetUniqueId, UniqueIdAdmin)
admin.site.register(OpticalNodeType)
admin.site.register(ServiceType, ServiceTypeAdmin)
admin.site.register(ServiceClass)
