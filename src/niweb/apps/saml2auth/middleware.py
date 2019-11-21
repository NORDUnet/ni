from django.shortcuts import render
from saml2.s_utils import UnsupportedBinding


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
