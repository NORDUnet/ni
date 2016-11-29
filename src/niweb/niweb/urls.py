from django.conf import settings
from django.conf.urls import *
from tastypie.api import Api
from apps.noclook.api.resources import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

def if_installed(appname, *args, **kwargs):
    ret = url(*args, **kwargs)
    if appname not in settings.INSTALLED_APPS:
        ret.resolve = lambda *args: None
    return ret

v1_api = Api(api_name='v1')
# Resources
v1_api.register(NodeTypeResource())
v1_api.register(RelationshipResource())
v1_api.register(UserResource())
v1_api.register(FullUserResource())
# Inheritated from NodeHandleResource
v1_api.register(CableResource())
v1_api.register(NordunetCableResource())
v1_api.register(CustomerResource())
v1_api.register(EndUserResource())
v1_api.register(ExternalEquipmentResource())
v1_api.register(FirewallResource())
v1_api.register(HostResource())
v1_api.register(HostProviderResource())
v1_api.register(HostServiceResource())
v1_api.register(HostUserResource())
v1_api.register(ODFResource())
v1_api.register(OpticalLinkResource())
v1_api.register(OpticalMultiplexSectionResource())
v1_api.register(OpticalNodeResource())
v1_api.register(OpticalPathResource())
v1_api.register(PDUResource())
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
v1_api.register(SwitchResource())
v1_api.register(UnitResource())
if "apps.scan" in settings.INSTALLED_APPS:
    from apps.scan.api.resources import *
    v1_api.register(ScanQueryItemResource())
if "apps.nerds" in settings.INSTALLED_APPS:
    from apps.nerds.api.resources import NerdsResource
    v1_api.register(NerdsResource())

urlpatterns = patterns('',

    # Uncomment the admin/doc line below to enable admin documentation:
    #(r'^admin/doc/', include('django.contrib.admindocs.urls')),

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
    (r'^comments/', include('django_comments.urls')),

    # Activity Streams
    ('^activity/', include('actstream.urls')),

    # User Profiles
    ('^userprofile/', include('apps.userprofile.urls')),

    # Scan
    if_installed('apps.scan', r'^scan/', include('apps.scan.urls', namespace="scan")),

    (r'^attachments/', include('attachments.urls', namespace='attachments')),
    # NOCLook URLs
    (r'', include('apps.noclook.urls')),
)
