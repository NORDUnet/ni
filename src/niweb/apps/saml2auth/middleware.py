from django.shortcuts import render
from saml2.s_utils import UnsupportedBinding
from djangosaml2.backends import Saml2Backend


class HandleUnsupportedBinding:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, UnsupportedBinding):
            return render(
                request,
                'simplemessage.html',
                {
                    'message': 'Your idp is not supported.'
                },
                status=400)
        else:
            # Not something that we handle
            return None


class ModifiedSaml2Backend(Saml2Backend):
    def _update_user(self, user, attributes: dict, attribute_mapping: dict, force_save: bool = False):
        import logging
        logger = logging.getLogger(__name__)
        logger.debug("***** SAML ATTRIBUTES *****")
        logger.debug(attributes)
        logger.debug("***** SAML ATTRIBUTES *****")
        if 'eduPersonEntitlement' in attributes:
            if 'some-entitlement' in attributes['eduPersonEntitlement']:
                user.is_staff = True
                force_save = False
            else:
                user.is_staff = False
                force_save = False
        return super()._update_user(user, attributes, attribute_mapping, force_save)

    # def save_user(self, user, *args, **kwargs):
    #     user.save()
    #     # user_group = Group.objects.get(name='Default')
    #     # user.groups.add(user_group)
    #     return super().save_user(user, *args, **kwargs)

class NDNOnlySaml2Backend(Saml2Backend):
    def is_authorized(self, attributes, attribute_mapping, idp_entityid, assertion_info):
        # check if employee or member
        affiliations = attributes.get('eduPersonScopedAffiliation', [])
        for ok_val in ['employee@nordu.net', 'member@nordu.net']:
            if ok_val in affiliations:
                return True
        return False
