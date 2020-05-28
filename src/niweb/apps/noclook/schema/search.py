# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import json

from apps.noclook.views.other import search_port_typeahead,\
    search_simple_port_typeahead, search
from django.db.utils import ProgrammingError
from django.test import RequestFactory
from django.urls import reverse_lazy
from django.utils.text import slugify

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
        ni_type = cls.get_from_nimetatype('ni_type')
        type_slug = slugify(ni_type)

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
        node_type = NodeType.objects.get(type=ni_type)

        return node_type

    @classmethod
    def get_type_name(cls):
        return cls.get_type().type

    @classmethod
    def get_filter_query_value(cls, filter):
        query_varname = cls.get_from_nimetatype('query_varname', \
            cls._default_query_varname)
        query_value = getattr(filter, query_varname, None)

        return query_value

    @classmethod
    def from_filter_to_request(cls, user, filter, is_post=False):
        view_params_query = cls.get_from_nimetatype('view_params_query', False)
        query_varname = cls.get_from_nimetatype('query_varname', \
            cls._default_query_varname)
        query_value = cls.get_filter_query_value(filter)

        # forge request
        request_factory = RequestFactory()
        request_path = '/'
        request_params = { query_varname: query_value }

        if view_params_query:
            request_params = None

        request = request_factory.get(request_path, request_params)

        if is_post:
            request = request_factory.post(request_path, request_params)

        request.user = user

        return request

    @classmethod
    def get_result_query(cls, user, filter):
        ret = []

        # get view
        is_post = cls.get_from_nimetatype('is_post', False)
        search_view = cls.get_from_nimetatype('search_view')
        json_id_attr = cls.get_from_nimetatype('json_id_attr')
        view_extra_params = cls.get_from_nimetatype('view_extra_params')
        view_search_varname = cls.get_from_nimetatype('view_search_varname')

        # forge request
        request = cls.from_filter_to_request(user, filter, is_post)

        # if the query is passed by view params
        view_params = {}
        view_params_query = cls.get_from_nimetatype('view_params_query', False)

        if view_params_query:
            query_value = cls.get_filter_query_value(filter)
            view_params = {
                view_search_varname: query_value
            }

            if view_extra_params:
                view_params = {
                    **view_params,
                    **view_extra_params,
                }

        # process
        response = search_view(request, **view_params)

        # get json array and parse to dict
        if response.content:
            elements = json.loads(response.content)

            # for elem in json
            for element in elements:
                try:
                    # get handle_id from json
                    handle_id = element[json_id_attr]
                    nh = NodeHandle.objects.get(handle_id=handle_id)
                    list_elem = cls.wrap_node(nh, element)
                    ret.append(list_elem)
                except:
                    pass
        return ret


    @classmethod
    def wrap_node(cls, nh, element):
        ni_type = cls.get_from_nimetatype('ni_type')
        is_nodewrapper = cls.get_from_nimetatype('is_nodewrapper', False)

        if is_nodewrapper:
            wrapper_args = dict(ninode=nh)

            extra_attr_wrap = cls.get_from_nimetatype('extra_attr_wrap')
            if extra_attr_wrap:
                wrapper_args = {
                    **wrapper_args,
                    **{ extra_attr_wrap: element.get(extra_attr_wrap, None) }
                }

            return ni_type(**wrapper_args)
        else:
            return nh

    @classmethod
    def get_connection_resolver(cls):
        ni_type = cls.get_from_nimetatype('ni_type')

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


class GeneralSearch(graphene.ObjectType):
    ninode = graphene.Field(NINode, required=True)
    match_txt = graphene.String()


class GeneralSearchConnection(SearchQueryConnection):
    pass

    class NIMetaType:
        view_params_query = True
        view_search_varname = 'value'
        view_extra_params = { 'form': 'json', 'permission_filter': True }
        search_view = search
        ni_type = GeneralSearch
        json_id_attr = 'handle_id'
        is_nodewrapper = True
        extra_attr_wrap = 'match_txt'

    class Meta:
        node = GeneralSearch


class PortSearchConnection(SearchQueryConnection):
    pass

    class NIMetaType:
        context = sriutils.get_network_context()
        search_view = search_simple_port_typeahead
        ni_type = Port
        json_id_attr = 'handle_id'

    class Meta:
        node = Port
