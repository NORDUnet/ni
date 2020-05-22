# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import json

from apps.noclook.views.other import search_port_typeahead, search_simple_port_typeahead
from django.test import RequestFactory

from .types import *


class GenericFilter(graphene.InputObjectType):
    query = graphene.String(required=True)


class SearchQueryConnection(graphene.relay.Connection):
    _default_query_varname = 'query'

    class Meta:
        abstract = True

    @classmethod
    def get_connection_field(cls):
        return relay.ConnectionField(cls, filter=graphene.Argument(GenericFilter))

    @classmethod
    def get_query_field_resolver(cls):
        type_slug = cls.get_type().slug

        field_name = 'search_{}'.format(type_slug)
        resolver_name = 'resolve_search_{}'.format(type_slug)

        ret = {
            'field': (field_name, cls.get_connection_field()),
            'resolver': (resolver_name, cls.get_connection_resolver()),
        }

        return ret

    @classmethod
    def get_from_nimetatype(cls, attr, default=None):
        ni_metatype = getattr(cls, 'NIMetaType')
        return getattr(ni_metatype, attr, default)

    @classmethod
    def get_type(cls):
        ni_type = cls.get_from_nimetatype('ni_type')
        node_type = NodeType.objects.filter(type=ni_type).first()
        return node_type

    @classmethod
    def get_type_name(cls):
        return cls.get_type().type

    @classmethod
    def from_filter_to_request(cls, user, filter):
        query_varname = cls.get_from_nimetatype('query_varname', \
            cls._default_query_varname)

        query_value = getattr(filter, query_varname, None)

        # forge request
        request_factory = RequestFactory()
        request = request_factory.get('/', { query_varname: query_value })
        request.user = user

        return request

    @classmethod
    def get_result_query(cls, user, filter):
        ret = []

        # get view
        search_view = cls.get_from_nimetatype('search_view')
        json_id_attr = cls.get_from_nimetatype('json_id_attr')

        # forge request
        request = cls.from_filter_to_request(user, filter)
        # process
        response = search_view(request)

        # get json array and parse to dict
        if response.content:
            elements = json.loads(response.content)

            # for elem in json
            for element in elements:
                try:
                    # get handle_id from json
                    handle_id = element[json_id_attr]
                    nh = NodeHandle.objects.get(handle_id=handle_id)
                    ret.append(nh)
                except:
                    pass
        return ret


    @classmethod
    def get_connection_resolver(cls):
        type_name = cls.get_type().type

        def search_list_resolver(self, info, **args):
            ret = []
            filter = args.get('filter', None)

            if info.context and info.context.user.is_authenticated:
                # check the context only if it's set
                context = cls.get_from_nimetatype('context')
                authorized = False

                if context:
                    authorized = sriutils.authorize_list_module(
                        info.context.user, context
                    )
                else:
                    authorized = True

                if authorized:
                    ret = cls.get_result_query(info.context.user, filter)
                else:
                    #403
                    pass
            else:
                # 401
                raise GraphQLAuthException()

            return ret

        return search_list_resolver


class PortSearchConnection(SearchQueryConnection):
    pass

    class NIMetaType:
        context = sriutils.get_network_context()
        query_var_name = 'query'
        search_view = search_simple_port_typeahead
        ni_type = Port
        json_id_attr = 'handle_id'

    class Meta:
        node = Port
