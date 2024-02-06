from django.db import models
from django.contrib.auth.models import User
from django.dispatch.dispatcher import receiver
from django.db.models.signals import post_save
from django.urls import reverse
import logging


class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)
    display_name = models.CharField(max_length=255, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "%s [%s]" % (self.user.username, self.display_name)

    def get_absolute_url(self):
        return self.url()

    def url(self):
        return reverse('userprofile_detail', args=[self.pk])
    
def log_data(data):
    logger = logging.getLogger(__name__)
    logger.warning(f"{data}")

@receiver(post_save, sender=User)
def create_user_profile(sender, **kwargs):
    user = kwargs['instance']
    attr_list = {}
    for field in user._meta.get_fields():
        if field.concrete:
            try:
                attr_list[field.name] = getattr(user, field.name)
            except:
                continue
    log_data(attr_list)
    UserProfile.objects.get_or_create(user=user)
