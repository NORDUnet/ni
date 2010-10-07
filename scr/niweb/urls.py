from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^niweb/', include('niweb.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),

    # Django Generic Login
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),

    # Django Generic Comments
    (r'^comments/', include('django.contrib.comments.urls')),

    # NOCLook URLs
    ('/$', include('niweb.noclook.urls')),
)
