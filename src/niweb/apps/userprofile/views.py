from apps.userprofile.models import UserProfile
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from actstream.models import actor_stream


@login_required
def list_userprofiles(request):
    profile_list = UserProfile.objects.all()
    return render(request, 'userprofile/list_userprofiles.html',
                  {'profile_list': profile_list})


@login_required
def userprofile_detail(request, userprofile_id):
    profile = get_object_or_404(UserProfile, pk=userprofile_id)
    activities = actor_stream(profile.user)
    # Show 50 activities per page
    paginator = Paginator(activities, 50, allow_empty_first_page=True)
    page = request.GET.get('page')
    try:
        activities = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        activities = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        activities = paginator.page(paginator.num_pages)
    return render(request, 'userprofile/userprofile_detail.html',
                  {'profile': profile, 'activities': activities})

    display_name = fields.CharField('display_name')
    email = fields.CharField('user__email')
    #  avatar = fields.FileField('avatar')
    landing_page = fields.CharField('landing_page')
    view_network = fields.BooleanField('view_network')
    view_services = fields.BooleanField('view_services')
    view_community = fields.BooleanField('view_community')


@login_required
def whoami(request):
    if request.method == 'GET':
        user = {
            'userid': request.user.pk,
            'name': request.user.profile.display_name,
            'email': request.user.email,
            'landing_page': request.user.profile.landing_page,
            'view_network': request.user.profile.view_network,
            'view_services': request.user.profile.view_services,
            'view_community': request.user.profile.view_community
        }
        return JsonResponse(user)
    return httpResponse(status_code=405)
