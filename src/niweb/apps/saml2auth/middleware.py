from os import environ
from django.shortcuts import render
from saml2.s_utils import UnsupportedBinding
from djangosaml2.backends import Saml2Backend
from niweb.settings import prod as prod_settings
from .utils import get_authorized_users


ENABLE_AUTHORIZATION_BY_FILE = environ.get("ENABLE_AUTHORIZATION_BY_FILE", 'False').lower() == 'true'
AUTH_GROUP_FILE = environ.get("AUTH_GROUP_FILE", "/opt/ni/src/niweb/auth_groups.ini")
authorized_users = get_authorized_users(AUTH_GROUP_FILE, allowed_groups=['*']) if ENABLE_AUTHORIZATION_BY_FILE else {}


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

    def is_authorized(self, attributes, attribute_mapping, idp_entityid, assertion_info):
        email = self.get_attribute_value('email', attributes, attribute_mapping)
        # email = attributes.get('email', (None, ))[0]
        if not ENABLE_AUTHORIZATION_BY_FILE:
            return True
        if email in authorized_users:
            return True
        return False

    def _update_user(self, user, attributes: dict, attribute_mapping: dict, force_save: bool = False):
        email = self.get_attribute_value('email', attributes, attribute_mapping)
        if not ENABLE_AUTHORIZATION_BY_FILE:
            return super()._update_user(user, attributes, attribute_mapping, force_save)

        if email in authorized_users:
            user.is_staff = False
            user.is_superuser = False
            force_save = False
            if authorized_users[email]['is_superuser']:
                user.is_staff = True
                user.is_superuser = True
            elif authorized_users[email]['is_staff']:
                user.is_staff = True
        return super()._update_user(user, attributes, attribute_mapping, force_save)

    def _get_attribute_value(self, django_field: str, attributes: dict, attribute_mapping: dict):
        """Update attribute mappings based on the Idp issuer"""
        default = prod_settings.SAML_ATTRIBUTE_MAPPING
        issuer = attributes["issuer"]
        attribute_mapping = prod_settings.CUSTOM_IDP_SAML_ATTRIBUTE_MAPPINGS.get(issuer, default)
        return super()._get_attribute_value(django_field, attributes, attribute_mapping)

    def clean_attributes(self, attributes: dict, idp_entityid: str, **kwargs) -> dict:
        """Hook to clean or filter attributes from the SAML response. No-op by default."""
        attributes.update({"issuer": idp_entityid})
        return attributes

class NDNOnlySaml2Backend(Saml2Backend):
    def is_authorized(self, attributes, attribute_mapping, idp_entityid, assertion_info):
        # check if employee or member
        affiliations = attributes.get('eduPersonScopedAffiliation', [])
        for ok_val in ['employee@nordu.net', 'member@nordu.net']:
            if ok_val in affiliations:
                return True
        return False
