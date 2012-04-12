from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib.auth.views import login
from tastypie.api import Api
from niweb.apps.noclook.api import NodeHandleResource, NodeTypeResource

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

v1_api = Api(api_name='v1')
v1_api.register(NodeHandleResource())
v1_api.register(NodeTypeResource())

urlpatterns = patterns('',

    # Uncomment the admin/doc line below to enable admin documentation:
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),

    # Static serve
    (r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.STATIC_DEV_MEDIA}),

    # Django Generic Login
    #(r'^accounts/login/$', 'django.contrib.auth.views.login'),
    
    # Tastypie URLs
    (r'^api/', include(v1_api.urls)),

    # Django Generic Comments
    (r'^comments/', include('django.contrib.comments.urls')),

    # Federated login
    (r'^accounts/', include('niweb.apps.fedlogin.urls')),

    # NOCLook URLs
    (r'', include('niweb.apps.noclook.urls')),
)