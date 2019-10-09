# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import NodeHandle, AuthzAction, GroupContextAuthzAction, NodeHandleContext, Context
from djangovakt.storage import DjangoStorage
from vakt import Guard, RulesChecker, Inquiry

READ_AA_NAME  = 'read'
WRITE_AA_NAME = 'write'
ADMIN_AA_NAME = 'admin'

NETWORK_CTX_NAME = 'Network'
COMMUNITY_CTX_NAME = 'Community'
CONTRACTS_CTX_NAME = 'Contracts'


def trim_readable_queryset(qs, user):
    # get all readable contexts for this user
    user_groups = user.groups.all()
    read_aa = get_read_authaction()

    gcaas = GroupContextAuthzAction.objects.filter(
        group__in=user.groups.all(),
        authzprofile=read_aa
    )

    readable_contexts = []
    for gcaa in gcaas:
        readable_contexts.append(gcaa.context)

    # queryset only will match nodes that the user can read
    if readable_contexts:
        # the hard way
        readable_ids = NodeHandleContext.objects.filter(
            context__in=readable_contexts
        ).values_list('nodehandle_id', flat=True)

        qs = qs.filter(handle_id__in=readable_ids)
    else:
        # the user doesn't have rights to any context
        qs.none()

    return qs


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

    # get authaction
    authaction = get_aa_func()

    # get contexts for this resource
    nodehandle = NodeHandle.objects.prefetch_related('contexts').get(handle_id=handle_id)
    contexts = [ c.name for c in nodehandle.contexts.all() ]

    # forge read resource inquiry
    inquiry = Inquiry(
        action=authaction.name,
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
        action=authaction.name,
        resource=None,
        subject=user,
        context={'module': (context.name,)}
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
        action=authaction.name,
        resource=None,
        subject=user,
        context={'module': (context.name,)}
    )

    ret = guard.is_allowed(inquiry)

    return ret
