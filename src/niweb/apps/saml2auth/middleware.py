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


class NDNOnlySaml2Backend(Saml2Backend):
    def is_authorized(self, attributes, attribute_mapping):
        # check if employee or member
        affiliations = attributes.get('eduPersonScopedAffiliation', [])
        for ok_val in ['employee@nordu.net', 'member@nordu.net']:
            if ok_val in affiliations:
                return True
        return False
