from django.conf.urls import patterns, url

from . import views

urlpatterns = [
    url(r'^queue/$', views.QueueIndexView.as_view(), name='queue'),
    url(r'^host/$', views.host, name='host'),
]
