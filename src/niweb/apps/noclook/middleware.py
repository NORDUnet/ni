# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from datetime import datetime
from django.conf import settings
from django.contrib.auth.middleware import get_user
from django.utils.cache import patch_vary_headers
from django.utils.functional import SimpleLazyObject
from django.utils.http import cookie_date
from graphql_jwt import signals
from graphql_jwt.settings import jwt_settings
from graphql_jwt.shortcuts import get_token, get_user_by_token
from graphql_jwt.utils import get_credentials
from importlib import import_module

import time

class SRIJWTCookieMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = None
        user = request.user

        if user.is_authenticated:
            token = get_token(user)
            signals.token_issued.send(
                sender=SRIJWTCookieMiddleware, request=request, user=user)

        response = self.get_response(request)

        if token:
            expires = datetime.utcnow() + jwt_settings.JWT_EXPIRATION_DELTA
            response.set_cookie(
                jwt_settings.JWT_COOKIE_NAME,
                token,
                domain=settings.COOKIE_DOMAIN,
                expires=expires,
                httponly=False,
                secure=jwt_settings.JWT_COOKIE_SECURE,
            )
        else:
            response.delete_cookie(jwt_settings.JWT_COOKIE_NAME)

        return response

class SRIJWTAuthMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session_created = False

        # add session
        if not hasattr(request, 'session'):
            session_engine = import_module(settings.SESSION_ENGINE)
            session_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
            request.session = session_engine.SessionStore(session_key)
            session_created = True

        # add user
        request.user = SimpleLazyObject(lambda: get_user(request))
        token = get_credentials(request)

        if token is not None:
            user = get_user_by_token(token, request)
            request.user = user

        # process response with inner middleware
        response = self.get_response(request)

        accessed = request.session.accessed
        modified = request.session.modified
        empty = request.session.is_empty()

        if settings.SESSION_COOKIE_NAME in request.COOKIES and empty:
            response.delete_cookie(
                settings.SESSION_COOKIE_NAME,
                path=settings.SESSION_COOKIE_PATH,
                domain=settings.SESSION_COOKIE_DOMAIN,
            )
            patch_vary_headers(response, ('Cookie',))
        else:
            if accessed:
                patch_vary_headers(response, ('Cookie',))

            try:
                SESSION_SAVE_EVERY_REQUEST = settings.SESSION_SAVE_EVERY_REQUEST
            except AttributeError:
                SESSION_SAVE_EVERY_REQUEST = None

            if (modified or SESSION_SAVE_EVERY_REQUEST) and not empty or session_created:
                if request.session.get_expire_at_browser_close():
                    max_age = None
                    expires = None
                else:
                    max_age = request.session.get_expiry_age()
                    expires_time = time.time() + max_age
                    expires = cookie_date(expires_time)

                # Save the session data and refresh the client cookie.
                # Skip session save for 500 responses, refs #3881.
                if response.status_code != 500:
                    try:
                        request.session.save()
                    except UpdateError:
                        raise SuspiciousOperation(
                            "The request's session was deleted before the "
                            "request completed. The user may have logged "
                            "out in a concurrent request, for example."
                        )
                    response.set_cookie(
                        settings.SESSION_COOKIE_NAME,
                        request.session.session_key, max_age=max_age,
                        expires=expires, domain=settings.SESSION_COOKIE_DOMAIN,
                        path=settings.SESSION_COOKIE_PATH,
                        secure=settings.SESSION_COOKIE_SECURE or None,
                        httponly=settings.SESSION_COOKIE_HTTPONLY or None,
                    )
        return response
