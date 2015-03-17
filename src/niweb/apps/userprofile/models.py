from django.db import models
from django.contrib.auth.models import User
from django.dispatch.dispatcher import receiver
from django.db.models.signals import post_save

class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile')
    display_name = models.CharField(max_length=255, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "%s [%s]" % (self.user.username, self.display_name)

    @models.permalink
    def get_absolute_url(self):
        return('apps.userprofile.views.userprofile_detail', (),
               {'userprofile_id': self.pk})


@receiver(post_save,sender=User)
def create_user_profile(sender,**kwargs):
    user = kwargs['instance']
    UserProfile.objects.get_or_create(user=user)
