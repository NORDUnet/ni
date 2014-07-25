# -*- coding: utf-8 -*-
"""
Created on 2012-11-23 10:18 AM

@author: lundberg
"""

from actstream import action
from models import NodeHandle
import helpers as h

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
    action.send(
        user,
        verb='update',
        action_object=action_object,
        noclook={
            'action_type': 'node_property',
            'property': property_key,
            'value_before': value_before,
            'value_after': value_after
        }
    )


def create_node(user, action_object):
    """
    :param user: Django user instance
    :param action_object: NodeHandle instance
    :return: None
    """
    action.send(
        user,
        verb='create',
        action_object=action_object,
        noclook={
            'action_type': 'node',
        }
    )


def delete_node(user, action_object):
    """
    :param user: Django user instance
    :param action_object: NodeHandle instance
    :return: None
    """
    action.send(
        user,
        verb='delete',
        noclook={
            'action_type': 'node',
            'object_name': unicode(action_object)
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
    start_nh = NodeHandle.get(pk=relationship.start.handle_id)
    end_nh = NodeHandle.get(pk=relationship.end.handle_id)
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
            'value_after': value_after
        }
    )


def create_relationship(user, relationship):
    """
    :param user: Django user instance
    :param relationship: norduniclient relationship model
    :return: None
    """
    start_nh = NodeHandle.get(pk=relationship.start.handle_id)
    end_nh = NodeHandle.get(pk=relationship.end.handle_id)
    action.send(
        user,
        verb='create',
        action_object=start_nh,
        target=end_nh,
        noclook={
            'action_type': 'relationship',
            'relationship_type': relationship.type
        }
    )


def delete_relationship(user, relationship):
    """
    :param user: Django user instance
    :param relationship: norduniclient relationship model
    :return: None
    """
    start_nh = NodeHandle.get(pk=relationship.start.handle_id)
    end_nh = NodeHandle.get(pk=relationship.end.handle_id)
    action.send(
        user,
        verb='delete',
        action_object=start_nh,
        target=end_nh,
        noclook={
            'action_type': 'relationship',
            'relationship_type': relationship.type,
            'object_name': unicode(relationship.data)
        }
    )