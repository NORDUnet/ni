# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import NodeHandle, AuthzAction, NodeHandleContext, Context
from djangovakt.storage import DjangoStorage
from vakt import Guard, RulesChecker, Inquiry

READ_AA_NAME  = 'read'
WRITE_AA_NAME = 'write'
ADMIN_AA_NAME = 'admin'

NETWORK_CTX_NAME = 'Network'
COMMUNITY_CTX_NAME = 'Community'
CONTRACTS_CTX_NAME = 'Contracts'

def get_vakt_storage_and_guard():
    storage = DjangoStorage()
    guard = Guard(storage, RulesChecker())

    return storage, guard


def get_authaction_by_name(name, aamodel=AuthzAction):
    authzaction = aamodel.objects.get(name=name)
    return authzaction


def get_read_authaction():
    return get_authaction_by_name(READ_AA_NAME)


def get_write_authaction():
    return get_authaction_by_name(WRITE_AA_NAME)


def get_admin_authaction():
    return get_authaction_by_name(ADMIN_AA_NAME)


def get_context_by_name(name, cmodel=Context):
    context = cmodel.objects.get(name=name)
    return context


def get_network_context(cmodel=Context):
    return get_context_by_name(NETWORK_CTX_NAME, cmodel)


def get_community_context(cmodel=Context):
    return get_context_by_name(COMMUNITY_CTX_NAME, cmodel)


def get_contracts_context(cmodel=Context):
    return get_context_by_name(CONTRACTS_CTX_NAME, cmodel)


def get_default_context(cmodel=Context):
    return get_community_context(cmodel)

def authorize_aa_resource(user, handle_id, get_aa_func):
    ret = False # deny by default

    # get storage and guard
    storage, guard = get_vakt_storage_and_guard()

    # get nodehandle
    nodehandle = NodeHandle.objects.get(handle_id=handle_id)

    # get authaction
    authaction = get_aa_func()

    # get contexts for this resource
    nhctxs = NodeHandleContext.objects.filter(
        nodehandle=nodehandle,
    )
    contexts = [ nhctx.context for nhctx in nhctxs ]

    # forge read resource inquiry
    inquiry = Inquiry(
        action=authaction,
        resource=nodehandle,
        subject=user,
        context={'module': contexts}
    )

    ret = guard.is_allowed(inquiry)

    return ret


def authorice_read_resource(user, handle_id):
    return authorize_aa_resource(user, handle_id, get_read_authaction)


def authorice_write_resource(user, handle_id):
    return authorize_aa_resource(user, handle_id, get_write_authaction)


def authorize_create_resource(user, context):
    ret = False # deny by default

    # get storage and guard
    storage, guard = get_vakt_storage_and_guard()

    # get authaction
    authaction = get_write_authaction()

    # forge read resource inquiry
    inquiry = Inquiry(
        action=authaction,
        resource=None,
        subject=user,
        context={'module': (context,)}
    )

    ret = guard.is_allowed(inquiry)

    return ret


def authorize_admin_module(user, context):
    ret = False # deny by default

    # get storage and guard
    storage, guard = get_vakt_storage_and_guard()

    # get authaction
    authaction = get_admin_authaction()

    # forge read resource inquiry
    inquiry = Inquiry(
        action=authaction,
        resource=None,
        subject=user,
        context={'module': (context,)}
    )

    ret = guard.is_allowed(inquiry)

    return ret
