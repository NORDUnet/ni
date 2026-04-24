from django.contrib import admin

from .models import QueueItem

class QueueItemAdmin(admin.ModelAdmin):
    list_display = ("type", "status", "created_at", "updated_at")

# Register your models here.
admin.site.register(QueueItem, QueueItemAdmin)
