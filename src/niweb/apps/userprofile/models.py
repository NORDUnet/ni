from django.db import models
from django.contrib.auth.models import User
from django.dispatch.dispatcher import receiver
from django.db.models.signals import post_save
from django.urls import reverse
from django.utils.encoding import python_2_unicode_compatible


LANDING_CHOICES = (
        ('network', 'Network'),
        ('services', 'Services'),
        ('community', 'Community'),
    )


@python_2_unicode_compatible
class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile')
    display_name = models.CharField(max_length=255, blank=True, null=True)
    avatar = models.ImageField()
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    landing_page = models.CharField(max_length=255,
                                    choices=LANDING_CHOICES,
                                    default='community')
    view_network = models.BooleanField(default=True)
    view_services = models.BooleanField(default=True)
    view_community = models.BooleanField(default=True)

    def __str__(self):
        return "%s [%s]" % (self.user.username, self.display_name)

    def get_absolute_url(self):
        return self.url()

    def url(self):
        return reverse('userprofile_detail', args=[self.pk])


@receiver(post_save, sender=User)
def create_user_profile(sender, **kwargs):
    user = kwargs['instance']
    UserProfile.objects.get_or_create(user=user)
