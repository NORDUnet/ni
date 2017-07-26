from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^queue/$', views.QueueIndexView.as_view(), name='queue'),
    url(r'^host/$', views.host, name='host'),
    url(r'^queue/(?P<pk>\d+)/rescan$', views.rescan, name='rescan'),
]
