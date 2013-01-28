from apps.userprofile.models import UserProfile
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from actstream.models import actor_stream

@login_required
def list_userprofiles(request):
    profile_list = UserProfile.objects.all()
    return render_to_response('userprofile/list_userprofiles.html',
        {'profile_list': profile_list},
        context_instance=RequestContext(request))

@login_required
def userprofile_detail(request, userprofile_id, num_act=None):
    profile = get_object_or_404(UserProfile, pk=userprofile_id)
    if num_act:
        activities = actor_stream(profile.user)[:num_act]
    else:
        activities = actor_stream(profile.user)
    return render_to_response('userprofile/userprofile_detail.html',
        {'profile': profile, 'activities': activities, 'num_act': num_act},
        context_instance=RequestContext(request))