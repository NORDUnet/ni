# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from datetime import datetime
from django.conf import settings
from django.contrib.auth.middleware import get_user
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.contrib.sessions.backends.base import UpdateError
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.utils.cache import patch_vary_headers
from django.utils.functional import SimpleLazyObject
from django.utils.http import cookie_date
from graphql_jwt import signals
from graphql_jwt.settings import jwt_settings
from graphql_jwt.shortcuts import get_token, get_user_by_token
from graphql_jwt.refresh_token.shortcuts import refresh_token_lazy
from graphql_jwt.refresh_token.signals import refresh_token_rotated
from graphql_jwt.utils import get_credentials, get_payload
from graphql_jwt.exceptions import JSONWebTokenError, JSONWebTokenExpired
from importlib import import_module

import time
import logging

logger = logging.getLogger(__name__)

def token_is_expired(token):
    ret = False

    try:
        get_payload(token)
    except JSONWebTokenError:
        ret = True
    except JSONWebTokenExpired:
        ret = True

    return ret


def get_user_from_session_key(session_key):
    session = Session.objects.get(session_key=session_key)
    session_data = session.get_decoded()
    uid = session_data.get('_auth_user_id')
    user = User.objects.get(id=uid)

    return user


class SRIJWTAuthMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session_created = False
        has_token = False

        # add user
        request.user = SimpleLazyObject(lambda: get_user(request))
        token = get_credentials(request)

        if token is not None and token != '' and token != 'None' and \
            not token_is_expired(token):
            user = get_user_by_token(token, request)
            request.user = user
            has_token = True

        # add session
        if not hasattr(request, 'session'):
            session_engine = import_module(settings.SESSION_ENGINE)
            session_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME)

            # if the session cannot be saved, start with an empty session
            try:
                request.session = session_engine.SessionStore(session_key)
                request.session.save()
                session_created = True
            except UpdateError:
                response = redirect(request.get_full_path())
                response.delete_cookie(
                    settings.SESSION_COOKIE_NAME,
                    path=settings.SESSION_COOKIE_PATH,
                    domain=settings.SESSION_COOKIE_DOMAIN,
                )
                response.delete_cookie(jwt_settings.JWT_COOKIE_NAME)
                patch_vary_headers(response, ('Cookie',))
                
                return response

        max_age = request.session.get_expiry_age()
        expires_time = time.time() + max_age
        anti_expires_time = cookie_date(time.time() - max_age)
        cookie_expires = cookie_date(expires_time)

        if request.session.get_expire_at_browser_close():
            max_age = None
            cookie_expires = None

        if token and token_is_expired(token):
            cookie_token = request.COOKIES.get(jwt_settings.JWT_COOKIE_NAME)
            session_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME)

            if cookie_token and cookie_token != '""':
                try:
                    user = get_user_from_session_key(session_key)
                    request.user = user
                    refresh_token_lazy(request.user)
                    token = get_token(request.user)
                    refresh_token_rotated.send(
                        sender=SRIJWTAuthMiddleware,
                        request=request,
                        refresh_token=self,
                    )
                    signals.token_issued.send(
                        sender=SRIJWTAuthMiddleware, request=request, user=request.user)
                except ObjectDoesNotExist:
                    ## fallback solution
                    response = redirect(request.get_full_path())
                    response.set_cookie(
                        jwt_settings.JWT_COOKIE_NAME,
                        '',
                        domain=settings.COOKIE_DOMAIN,
                        expires=anti_expires_time,
                        httponly=False,
                        secure=jwt_settings.JWT_COOKIE_SECURE,
                    )
                    response.delete_cookie(jwt_settings.JWT_COOKIE_NAME)
                    patch_vary_headers(response, ('Cookie',))

                    return response

        # process response with inner middleware
        response = self.get_response(request)

        if request.user.is_authenticated and not has_token:
            token = get_token(request.user)
            signals.token_issued.send(
                sender=SRIJWTAuthMiddleware, request=request, user=request.user)

            # if token is expired, refresh it
            if token_is_expired(token):
                refresh_token_lazy(request.user)
                token = get_token(request.user)
                refresh_token_rotated.send(
                    sender=SRIJWTAuthMiddleware,
                    request=request,
                    refresh_token=self,
                )
                signals.token_issued.send(
                    sender=SRIJWTAuthMiddleware, request=request, user=request.user)

            #expires = datetime.utcnow() + jwt_settings.JWT_EXPIRATION_DELTA
            response.set_cookie(
                jwt_settings.JWT_COOKIE_NAME,
                token,
                domain=settings.COOKIE_DOMAIN,
                max_age=max_age,
                expires=cookie_expires,
                httponly=False,
                secure=jwt_settings.JWT_COOKIE_SECURE,
            )
            patch_vary_headers(response, ('Cookie',))

        accessed = request.session.accessed
        modified = request.session.modified
        empty = request.session.is_empty()

        # we'll force the session cookie creation if:
        # * we have a valid token but we didn't have a session for the user
        # * the session was not created because the user is logged in
        create_session_cookie = token and session_created \
                                or token and not request.user.is_authenticated

        if settings.SESSION_COOKIE_NAME in request.COOKIES and empty:
            response.delete_cookie(
                settings.SESSION_COOKIE_NAME,
                path=settings.SESSION_COOKIE_PATH,
                domain=settings.SESSION_COOKIE_DOMAIN,
            )
            response.delete_cookie(jwt_settings.JWT_COOKIE_NAME)
            patch_vary_headers(response, ('Cookie',))
        else:
            if accessed:
                patch_vary_headers(response, ('Cookie',))

            try:
                SESSION_SAVE_EVERY_REQUEST = settings.SESSION_SAVE_EVERY_REQUEST
            except AttributeError:
                SESSION_SAVE_EVERY_REQUEST = None

            if (modified or SESSION_SAVE_EVERY_REQUEST) and not empty or create_session_cookie:
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
                        expires=cookie_expires, domain=settings.SESSION_COOKIE_DOMAIN,
                        path=settings.SESSION_COOKIE_PATH,
                        secure=settings.SESSION_COOKIE_SECURE or None,
                        httponly=settings.SESSION_COOKIE_HTTPONLY or None,
                    )

        return response
