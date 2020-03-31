from django.conf.urls import url

from . import views

app_name = 'scan'

urlpatterns = [
    url(r'^queue/$', views.QueueIndexView.as_view(), name='queue'),
    url(r'^host/$', views.host, name='host'),
    url(r'^queue/(?P<pk>\d+)/rescan$', views.rescan, name='rescan'),
]
