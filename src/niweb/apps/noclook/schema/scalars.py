# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from graphql.language.ast import BooleanValue, IntValue, StringValue
from graphene.types import Scalar
from io import StringIO

import graphene

class IPAddr(Scalar):
    '''IPAddr scalar to be matched with the IPAddrField in a django form'''
    @staticmethod
    def serialize(value):
        # this would be to_python method
        if isinstance(value, list):
            return value
        else:
            return none

    @staticmethod
    def parse_value(value):
        # and this would be the clean method
        result = []
        for line in StringIO(value):
            ip = line.replace('\n','').strip()
            if ip:
                try:
                    ipaddress.ip_address(ip)
                    result.append(ip)
                except ValueError as e:
                    errors.append(str(e))
        if errors:
            raise ValidationError(errors)
        return result

    parse_literal = parse_value


class JSON(Scalar):
    '''JSON scalar to be matched with the JSONField in a django form'''
    @staticmethod
    def serialize(value):
        if value:
            value = json.dumps(value)

        return value

    @staticmethod
    def parse_value(value):
        try:
            if value:
                value = json.loads(value)
        except ValueError:
            raise ValidationError(self.error_messages['invalid'], code='invalid')
        return value


class RoleScalar(Scalar):
    '''This is a POC scalar that may be used in the contact mutation input'''
    @staticmethod
    def serialize(value):
        roles_dict = get_roles_dropdown()

        if value in roles_dict.keys():
            return roles_dict[value]
        else:
            raise Exception('The selected role ("{}") doesn\'t exists'
                                .format(value))

    @staticmethod
    def parse_value(value):
        roles_dict = get_roles_dropdown()

        key = value.replace(' ', '_').lower()
        if key in roles_dict.keys():
            return roles_dict[key]
        else:
            return value

    @staticmethod
    def get_roles_dropdown():
        ret = {}
        roles = nc.models.RoleRelationship.get_all_roles()
        for role in roles:
            name = role.replace(' ', '_').lower()
            ret[name] = role

        return ret


class ChoiceScalar(Scalar):
    '''This scalar represents a choice field in query/mutation'''
    @staticmethod
    def coerce_choice(value):
        num = None
        try:
            num = int(value)
        except ValueError:
            try:
                num = int(float(value))
            except ValueError:
                pass
        if num:
            return graphene.Int.coerce_int(value)
        else:
            return graphene.String.coerce_string(value)


    serialize = coerce_choice
    parse_value = coerce_choice

    @staticmethod
    def parse_literal(ast):
        if isinstance(ast, IntValue):
            return graphene.Int.parse_literal(ast)
        elif isinstance(ast, StringValue):
            return graphene.String.parse_literal(ast)

    @classmethod
    def get_roles_dropdown(cls):
        pass


class NullBoolean(graphene.Boolean):
    """
    Just like the `Boolean` graphene scalar but it could be set on null/None
    """
    @staticmethod
    def serialize(value):
        if value in (True, 'True', 'true', '1'):
            return True
        elif value in (False, 'False', 'false', '0'):
            return False
        else:
            return None

    @staticmethod
    def parse_value(value):
        if value != None:
            return bool(value)

        return None

    @staticmethod
    def parse_literal(ast):
        ret = None
        if isinstance(ast, BooleanValue):
            ret = ast.value

        return ret
