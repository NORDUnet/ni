from django.conf import settings
from django.conf.urls import *
from tastypie.api import Api
from niweb.apps.noclook.api.resources import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

v1_api = Api(api_name='v1')
# Resources
v1_api.register(NodeTypeResource())
v1_api.register(RelationshipResource())
v1_api.register(UserResource())
v1_api.register(FullUserResource())
# Inheritated from NodeHandleResource
v1_api.register(CableResource())
v1_api.register(CustomerResource())
v1_api.register(EndUserResource())
v1_api.register(HostResource())
v1_api.register(HostProviderResource())
v1_api.register(HostServiceResource())
v1_api.register(HostUserResource())
v1_api.register(ODFResource())
v1_api.register(OpticalNodeResource())
v1_api.register(PeeringGroupResource())
v1_api.register(PeeringPartnerResource())
v1_api.register(PortResource())
v1_api.register(ProviderResource())
v1_api.register(RackResource())
v1_api.register(RouterResource())
v1_api.register(ServiceResource())
v1_api.register(ServiceL2VPNResource())
v1_api.register(SiteResource())
v1_api.register(SiteOwnerResource())
v1_api.register(UnitResource())

urlpatterns = patterns('',

    # Uncomment the admin/doc line below to enable admin documentation:
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),

    # Static serve
    (r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT}),

    # Django Generic Login
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),

    # Federated login
    #(r'^saml2/', include('djangosaml2.urls')),

    # Tastypie URLs
    (r'^api/', include(v1_api.urls)),

    # Django Generic Comments
    (r'^comments/', include('django.contrib.comments.urls')),

    # Activity Streams
    ('^activity/', include('actstream.urls')),

    # User Profiles
    ('^userprofile/', include('niweb.apps.userprofile.urls')),

    # NOCLook URLs
    (r'', include('niweb.apps.noclook.urls')),
)
