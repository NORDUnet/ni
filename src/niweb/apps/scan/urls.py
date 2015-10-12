from django.conf.urls import patterns, url

from . import views

urlpatterns = [
    url(r'^host/(?P<hostname>[^/]+)/$', views.host, name='host'),
]
