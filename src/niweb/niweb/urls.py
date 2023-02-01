from django.conf import settings
from django.urls import include, path
from tastypie.api import Api
import apps.noclook.api.resources as niapi
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()


def if_installed(appname, *args, **kwargs):
    ret = path(*args, **kwargs)
    if appname not in settings.INSTALLED_APPS:
        ret.resolve = lambda *args: None
    return ret


v1_api = Api(api_name='v1')
# Resources
v1_api.register(niapi.NodeTypeResource())
v1_api.register(niapi.RelationshipResource())
v1_api.register(niapi.UserResource())
v1_api.register(niapi.FullUserResource())
# Inheritated from NodeHandleResource
v1_api.register(niapi.CableResource())
v1_api.register(niapi.NordunetCableResource())
v1_api.register(niapi.CustomerResource())
v1_api.register(niapi.EndUserResource())
v1_api.register(niapi.ExternalEquipmentResource())
v1_api.register(niapi.FirewallResource())
v1_api.register(niapi.HostResource())
v1_api.register(niapi.HostProviderResource())
v1_api.register(niapi.HostServiceResource())
v1_api.register(niapi.HostUserResource())
v1_api.register(niapi.ODFResource())
v1_api.register(niapi.OpticalLinkResource())
v1_api.register(niapi.OpticalMultiplexSectionResource())
v1_api.register(niapi.OpticalNodeResource())
v1_api.register(niapi.OpticalFilterResource())
v1_api.register(niapi.OpticalPathResource())
v1_api.register(niapi.PDUResource())
v1_api.register(niapi.PeeringGroupResource())
v1_api.register(niapi.PeeringPartnerResource())
v1_api.register(niapi.PortResource())
v1_api.register(niapi.ProviderResource())
v1_api.register(niapi.RackResource())
v1_api.register(niapi.RouterResource())
v1_api.register(niapi.ServiceResource())
v1_api.register(niapi.ServiceL2VPNResource())
v1_api.register(niapi.ServiceEVPNResource())
v1_api.register(niapi.SiteResource())
v1_api.register(niapi.SiteOwnerResource())
v1_api.register(niapi.SwitchResource())
v1_api.register(niapi.UnitResource())
# other
v1_api.register(niapi.HostScanResource())
if "apps.scan" in settings.INSTALLED_APPS:
    from apps.scan.api.resources import ScanQueryItemResource
    v1_api.register(ScanQueryItemResource())
if "apps.nerds" in settings.INSTALLED_APPS:
    from apps.nerds.api.resources import NerdsResource
    v1_api.register(NerdsResource())

urlpatterns = [
    # Uncomment the next line to enable the admin:
    path('admin/', admin.site.urls),
]

if not settings.DJANGO_LOGIN_DISABLED:
    urlpatterns += [
        path('accounts/login/', auth_views.LoginView.as_view(), name='django_login'),
    ]

# Federated login
if settings.SAML_ENABLED:
    urlpatterns += [
        path('saml2/', include('djangosaml2.urls')),
    ]

urlpatterns += [
    # Tastypie URLs
    path('api/', include(v1_api.urls)),

    # Django Generic Comments
    path('comments/', include('django_comments.urls')),

    # Activity Streams
    path('activity/', include('actstream.urls')),

    # User Profiles
    path('userprofile/', include('apps.userprofile.urls')),

    # Scan
    if_installed('apps.scan', 'scan/', include('apps.scan.urls', namespace="scan")),

    path('attachments/', include('attachments.urls', namespace='attachments')),
    path('userprofile/', include('apps.userprofile.urls')),
    # NOCLook URLs
    path('', include('apps.noclook.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
