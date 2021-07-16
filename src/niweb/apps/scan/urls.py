from django.urls import path

from . import views

app_name = 'scan'

urlpatterns = [
    path('queue/', views.QueueIndexView.as_view(), name='queue'),
    path('host/', views.host, name='host'),
    path('queue/<int:pk>/rescan', views.rescan, name='rescan'),
]
