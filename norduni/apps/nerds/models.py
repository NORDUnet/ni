from django.db import models

# Create your models here.

class HostUserMap(models.Model):
    domain = models.CharField(max_length=255, unique=True)
    host_user = models.CharField(max_length=255)   
