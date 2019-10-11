# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from datetime import datetime
from graphql_jwt import signals
from graphql_jwt.settings import jwt_settings
from graphql_jwt.shortcuts import get_token

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
                expires=expires,
                httponly=False,
                secure=jwt_settings.JWT_COOKIE_SECURE,
            )
        else:
            response.delete_cookie(jwt_settings.JWT_COOKIE_NAME)

        return response
