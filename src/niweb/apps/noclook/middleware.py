# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from datetime import datetime
from django.conf import settings
from django.contrib.auth.middleware import get_user
from django.utils.functional import SimpleLazyObject
from django.contrib.sessions.middleware import SessionMiddleware
from graphql_jwt import signals
from graphql_jwt.settings import jwt_settings
from graphql_jwt.shortcuts import get_token, get_user_by_token
from graphql_jwt.utils import get_credentials, get_http_authorization
from importlib import import_module

class SRIJWTMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = None
        user = request.user

        if user.is_authenticated:
            token = get_token(user)
            signals.token_issued.send(
                sender=SRIJWTMiddleware, request=request, user=user)

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
        self.session_middleware = SessionMiddleware(get_response)

    def __call__(self, request):
        # add session
        session_engine = import_module(settings.SESSION_ENGINE)
        session_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
        request.session = session_engine.SessionStore(session_key)

        # add user
        request.user = SimpleLazyObject(lambda: get_user(request))
        token = get_credentials(request)

        if token is not None:
            user = get_user_by_token(token, request)
            request.user = user

        # process response with inner middleware
        response = self.get_response(request)
        response = self.session_middleware.process_response(request, response)

        return response
