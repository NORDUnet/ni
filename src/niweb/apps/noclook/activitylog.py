# -*- coding: utf-8 -*-
"""
Created on 2012-11-23 10:18 AM

@author: lundberg
"""

from actstream import action
from .models import NodeHandle
import apps.noclook.vakt.utils as sriutils


def update_node_property(user, action_object, property_key, value_before, value_after):
    """
    Creates an Action with the extra information needed to present the user with a history.
    :param user: Django user instance
    :param action_object: NodeHandle instance
    :param property_key: String
    :param value_before: JSON supported value
    :param value_after: JSON supported value
    :return: None
    """
    contexts = sriutils.get_nh_named_contexts(action_object)
    action_object.modifier = user
    action_object.save()

    action.send(
        user,
        verb='update',
        action_object=action_object,
        noclook={
            'action_type': 'node_property',
            'property': property_key,
            'value_before': value_before,
            'value_after': value_after,
            'contexts': contexts,
        }
    )


def create_node(user, action_object, context=None):
    """
    :param user: Django user instance
    :param action_object: NodeHandle instance
    :return: None
    """
    contexts = []

    if context:
        contexts = [{ 'context_name': context.name }]

    action.send(
        user,
        verb='create',
        action_object=action_object,
        noclook={
            'action_type': 'node',
            'contexts': contexts,
        }
    )


def delete_node(user, action_object):
    """
    :param user: Django user instance
    :param action_object: NodeHandle instance
    :return: None
    """
    contexts = sriutils.get_nh_named_contexts(action_object)

    action.send(
        user,
        verb='delete',
        noclook={
            'action_type': 'node',
            'object_name': u'{}'.format(action_object),
            'contexts': contexts,
        }
    )


def update_relationship_property(user, relationship, property_key, value_before, value_after):
    """
    Creates an Action with the extra information needed to present the user with a history.
    :param user: Django user instance
    :param relationship: norduniclient relationship model
    :param property_key: String
    :param value_before: JSON supported value
    :param value_after: JSON supported value
    :return: None
    """
    start_nh = NodeHandle.objects.get(pk=relationship.start['handle_id'])
    start_nh.modifier = user
    start_nh.save()
    end_nh = NodeHandle.objects.get(pk=relationship.end['handle_id'])
    end_nh.modifier = user
    end_nh.save()

    contexts_start = sriutils.get_nh_named_contexts(start_nh)
    contexts_end = sriutils.get_nh_named_contexts(end_nh)
    contexts = contexts_start

    for c in contexts_end:
        if c not in contexts:
            contexts.append(c)

    action.send(
        user,
        verb='update',
        action_object=start_nh,
        target=end_nh,
        noclook={
            'action_type': 'relationship_property',
            'relationship_type': relationship.type,
            'property': property_key,
            'value_before': value_before,
            'value_after': value_after,
            'contexts': contexts,
        }
    )


def create_relationship(user, relationship):
    """
    :param user: Django user instance
    :param relationship: norduniclient relationship model
    :return: None
    """
    start_nh = NodeHandle.objects.get(pk=relationship.start['handle_id'])
    start_nh.modifier = user
    start_nh.save()
    end_nh = NodeHandle.objects.get(pk=relationship.end['handle_id'])
    end_nh.modifier = user
    end_nh.save()

    contexts_start = sriutils.get_nh_named_contexts(start_nh)
    contexts_end = sriutils.get_nh_named_contexts(end_nh)
    contexts = contexts_start

    for c in contexts_end:
        if c not in contexts:
            contexts.append(c)

    action.send(
        user,
        verb='create',
        action_object=start_nh,
        target=end_nh,
        noclook={
            'action_type': 'relationship',
            'relationship_type': relationship.type,
            'contexts': contexts,
        }
    )


def delete_relationship(user, relationship):
    """
    :param user: Django user instance
    :param relationship: norduniclient relationship model
    :return: None
    """
    start_nh = NodeHandle.objects.get(pk=relationship.start['handle_id'])
    start_nh.modifier = user
    start_nh.save()
    end_nh = NodeHandle.objects.get(pk=relationship.end['handle_id'])
    end_nh.modifier = user
    end_nh.save()

    contexts_start = sriutils.get_nh_named_contexts(start_nh)
    contexts_end = sriutils.get_nh_named_contexts(end_nh)
    contexts = contexts_start

    for c in contexts_end:
        if c not in contexts:
            contexts.append(c)

    action.send(
        user,
        verb='delete',
        action_object=start_nh,
        target=end_nh,
        noclook={
            'action_type': 'relationship',
            'relationship_type': relationship.type,
            'object_name': u'{}'.format(relationship.data),
            'contexts': contexts,
        }
    )
