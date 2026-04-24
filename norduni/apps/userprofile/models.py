from django.db import models
from django.contrib.auth.models import User
from django.dispatch.dispatcher import receiver
from django.db.models.signals import post_save, pre_save
from django.urls import reverse
import logging
logger = logging.getLogger(__name__)


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
    UserProfile.objects.get_or_create(user=user)


# This can be used to change the user send to the auth_user by djangosaml2
@receiver(pre_save, sender=User)
def custom_update_user(sender, **kwargs):
    user = kwargs['instance']
    # setattr(user, 'username', "Dc69_f4384h69hinr8u35u5_66")
    # TODO: try user.proprety e.g. user.is_staff
    return True  # I modified the user object
