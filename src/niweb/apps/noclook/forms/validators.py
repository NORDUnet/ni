# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.noclook.models import NodeType, NodeHandle

def validate_nodetype(value, type):
    nh = NodeHandle.objects.get(handle_id=value)

    if nh.node_type != type:
        raise ValidationError(
            _('This field requires a %(type) but a %(badtype) was provided'),
            params={'type': str(type), 'badtype': str(nh.node_type)},
        )

def validate_organization(value):
    type_str = 'Organization'
    type = NodeType.objects.get_or_create(
                            type=type_str, slug=type_str.lower())[0]

    return validate_nodetype(value, type)

def validate_contact(value):
    type_str = 'Contact'
    type = NodeType.objects.get_or_create(
                            type=type_str, slug=type_str.lower())[0]

    return validate_nodetype(value, type)

def validate_group(value):
    type_str = 'Group'
    type = NodeType.objects.get_or_create(
                            type=type_str, slug=type_str.lower())[0]

    return validate_nodetype(value, type)

def validate_procedure(value):
    type_str = 'Procedure'
    type = NodeType.objects.get_or_create(
                            type=type_str, slug=type_str.lower())[0]

    return validate_nodetype(value, type)
