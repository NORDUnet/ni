# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import re
from apps.noclook import helpers
from apps.noclook.models import NodeType, NodeHandle
from collections import OrderedDict
from django import forms
from django.db.models import Q
from django.test import RequestFactory
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.types import DjangoObjectTypeOptions
from graphql import GraphQLError
from norduniclient.exceptions import UniqueNodeError, NoRelationshipPossible

from ..models import NodeType, NodeHandle

class DictEntryType(graphene.ObjectType):
    '''
    This type represents an key value pair in a dictionary for the data
    dict of the norduniclient nodes
    '''
    key = graphene.String(required=True)
    value = graphene.String(required=True)

def resolve_nidata(self, info, **kwargs):
    '''
    Resolvers norduniclient nodes data dictionary
    '''
    ret = []

    alldata = self.get_node().data
    for key, value in alldata.items():
        ret.append(DictEntryType(key=key, value=value))

    return ret

class NIBasicField():
    '''
    Super class of the type fields
    '''
    def __init__(self, field_type=graphene.String, manual_resolver=False,
                    type_kwargs=None, **kwargs):

        self.field_type      = field_type
        self.manual_resolver = manual_resolver
        self.type_kwargs     = type_kwargs

    def get_resolver(self, **kwargs):
        field_name = kwargs.get('field_name')
        if not field_name:
            raise Exception(
                'Field name for field {} should not be empty for a {}'.format(
                    field_name, self.__class__
                )
            )
        def resolve_node_string(self, info, **kwargs):
            return self.get_node().data.get(field_name)

        return resolve_node_string

    def get_field_type(self):
        return self.field_type

class NIStringField(NIBasicField):
    '''
    String type
    '''
    pass

class NIIntField(NIBasicField):
    '''
    Int type
    '''
    def __init__(self, field_type=graphene.Int, manual_resolver=False,
                    type_kwargs=None, **kwargs):
        super(NIIntField, self).__init__(field_type, manual_resolver,
                        type_kwargs, **kwargs)

class NIListField(NIBasicField):
    '''
    Object list type
    '''
    def __init__(self, field_type=graphene.List, manual_resolver=False,
                    type_args=None, rel_name=None, rel_method=None,
                    not_null_list=False, **kwargs):

        self.field_type      = field_type
        self.manual_resolver = manual_resolver
        self.type_args       = type_args
        self.rel_name        = rel_name
        self.rel_method      = rel_method
        self.not_null_list   = not_null_list

    def get_resolver(self, **kwargs):
        rel_name   = kwargs.get('rel_name')
        rel_method = kwargs.get('rel_method')

        def resolve_relationship_list(self, info, **kwargs):
            neo4jnode = self.get_node()
            relations = getattr(neo4jnode, rel_method)()
            nodes = relations.get(rel_name)

            # this may be the worst way to do it, but it's just for a PoC
            handle_id_list = []
            if nodes:
                for node in nodes:
                    node = node['node']
                    node_id = node.data.get('handle_id')
                    handle_id_list.append(node_id)

            ret = NodeHandle.objects.filter(handle_id__in=handle_id_list)

            return ret

        return resolve_relationship_list

class NIObjectType(DjangoObjectType):
    '''
    This class expands graphene_django object type adding the defined fields in
    the types subclasses and extracts the data from the norduniclient nodes and
    adds a resolver for each field, a nidata field is also added to hold the
    values of the node data dict.
    '''
    @classmethod
    def __init_subclass_with_meta__(
        cls,
        sri_fields=None,
        **options,
    ):
        fields_names = ''
        allfields = cls.__dict__
        graphfields = OrderedDict()

        # getting all not magic attributes, also filter non NI fields
        for name, field in allfields.items():
            pattern = re.compile("^__.*__$")
            is_nibasicfield = issubclass(field.__class__, NIBasicField)
            if pattern.match(name) or callable(field) or not is_nibasicfield:
                continue
            graphfields[name] = field

        # run over the fields defined and adding graphene fields and resolvers
        for name, field in graphfields.items():
            fields_names = fields_names + ' ' + '({} / {})'.format(name, field.__dict__)
            field_fields = field.__dict__

            field_type      = field_fields.get('field_type')
            manual_resolver = field_fields.get('manual_resolver')
            type_kwargs     = field_fields.get('type_kwargs')
            type_args       = field_fields.get('type_args')
            rel_name        = field_fields.get('rel_name')
            rel_method      = field_fields.get('rel_method')
            not_null_list   = field_fields.get('not_null_list')

            # adding the field
            field_value = None
            if type_kwargs:
                field_value = field_type(**type_kwargs)
            elif type_args:
                field_value = field_type(*type_args)
                if not_null_list:
                    field_value = graphene.NonNull(field_type(*type_args))
            else:
                field_value = field_type(**{})

            setattr(cls, name, field_value)

            # adding the resolver
            if not manual_resolver:
                setattr(cls, 'resolve_{}'.format(name), \
                    field.get_resolver(
                        field_name=name,
                        rel_name=rel_name,
                        rel_method=rel_method,
                    )
                )

            elif callable(manual_resolver):
                setattr(cls, 'resolve_{}'.format(name), manual_resolver)
            else:
                raise Exception(
                    'NIObjectField manual_resolver must be a callable in field {}'\
                        .format(name)
                )

        # add data field and resolver
        setattr(cls, 'nidata', graphene.List(DictEntryType))
        setattr(cls, 'resolve_nidata', resolve_nidata)

        options['model'] = NIObjectType._meta.model
        options['interfaces'] = NIObjectType._meta.interfaces

        super(NIObjectType, cls).__init_subclass_with_meta__(
            **options
        )

    @classmethod
    def get_queryset(cls, queryset, info):
        if info.context.user.is_anonymous:
            return queryset.none()
        else:
            return queryset.filter(
                Q(creator=info.context.user) | Q(modifier=info.context.user)
            )

    class Meta:
        model = NodeHandle
        interfaces = (relay.Node, )

class NodeHandleType(NIObjectType):
    pass

class AbstractNIMutation(relay.ClientIDMutation):
    nodehandle = graphene.Field(NodeHandleType, required=True) # the type should be replaced

    @classmethod
    def __init_subclass_with_meta__(
        cls, output=None, input_fields=None, arguments=None, name=None, **options
    ):
        ''' In this method we'll build an input nested object using the form
        '''
        # read form
        ni_metaclass  = getattr(cls, 'NIMetaClass')
        django_form   = getattr(ni_metaclass, 'django_form', None)
        mutation_name = getattr(ni_metaclass, 'mutation_name', cls.__name__)
        is_create     = getattr(ni_metaclass, 'is_create', False)

        # build fields into Input
        inner_fields = {}
        if django_form:
            for class_field_name, class_field in django_form.__dict__.items():
                if class_field_name == 'declared_fields' or class_field_name == 'base_fields':
                    for field_name, field in class_field.items():
                        # convert form field into mutation input field
                        graphene_field = cls.form_to_graphene_field(field)

                        if graphene_field:
                            if hasattr(django_form, 'Meta') and hasattr(django_form.Meta, 'exclude'):
                                if field not in django_form.Meta.exclude:
                                    inner_fields[field_name] = graphene_field
                            else:
                                inner_fields[field_name] = graphene_field

        # add handle_id
        if not is_create:
            inner_fields['handle_id'] = graphene.Int(required=True)

        # add Input attribute to class
        inner_class = type('Input', (object,), inner_fields)
        setattr(cls, 'Input', inner_class)

        super(AbstractNIMutation, cls).__init_subclass_with_meta__(
            output, inner_fields, arguments, name=mutation_name, **options
        )

    @classmethod
    def form_to_graphene_field(cls, form_field):
        '''Django form to graphene field conversor
        '''
        graphene_field = None

        # get attributes
        graph_kwargs = {}
        disabled = False
        for attr_name, attr_value in form_field.__dict__.items():
            if attr_name == 'required':
                graph_kwargs['required'] = attr_value
            elif attr_name == 'disabled':
                disabled = attr_value
            elif attr_name == 'initial':
                graph_kwargs['default_value'] = attr_value

        # compare types
        if not disabled:
            if isinstance(form_field, forms.BooleanField):
                graphene_field = graphene.Boolean(**graph_kwargs)
            elif isinstance(form_field, forms.CharField):
                graphene_field = graphene.String(**graph_kwargs)
            elif isinstance(form_field, forms.ChoiceField):
                graphene_field = graphene.String(**graph_kwargs)
            elif isinstance(form_field, forms.FloatField):
                graphene_field = graphene.Float(**graph_kwargs)
            elif isinstance(form_field, forms.IntegerField):
                graphene_field = graphene.Int(**graph_kwargs)
            elif isinstance(form_field, forms.MultipleChoiceField):
                graphene_field = graphene.String(**graph_kwargs)
            elif isinstance(form_field, forms.NullBooleanField):
                graphene_field = graphene.String(**graph_kwargs)
            elif isinstance(form_field, forms.URLField):
                graphene_field = graphene.String(**graph_kwargs)
            else:
                graphene_field = graphene.String(**graph_kwargs)

            ### fields to be implement: ###
            # IPAddrField (CharField)
            # JSONField (CharField)
            # NodeChoiceField (ModelChoiceField)
            # DatePickerField (DateField)
            # description_field (CharField)
            # relationship_field (ChoiceField / IntegerField)
        else:
            return None

        return graphene_field

    @classmethod
    def get_type(cls):
        ni_metaclass = getattr(cls, 'NIMetaClass')
        return getattr(ni_metaclass, 'typeclass')

    @classmethod
    def from_input_to_request(cls, user, **input):
        '''
        Gets the input data from the input inner class, and this is build using
        the fields in the django form. It returns a nodehandle of the type
        defined by the NIMetaClass
        '''
        # get ni metaclass data
        ni_metaclass   = getattr(cls, 'NIMetaClass')
        form_class     = getattr(ni_metaclass, 'django_form', None)
        request_path   = getattr(ni_metaclass, 'request_path', '/')
        is_create      = getattr(ni_metaclass, 'is_create', False)

        graphql_type   = getattr(ni_metaclass, 'graphql_type')
        nimetatype     = getattr(graphql_type, 'NIMetaType')
        node_type      = getattr(nimetatype, 'ni_type').lower()
        node_meta_type = getattr(nimetatype, 'ni_metatype').capitalize()

        # get input values
        input_class = getattr(cls, 'Input', None)
        input_params = {}
        if input_class:
            for attr_name, attr_field in input_class.__dict__.items():
                attr_value = input.get(attr_name)
                input_params[attr_name] = attr_value

        if not is_create:
            input_params['handle_id'] = input.get('handle_id')

        # forge request
        request_factory = RequestFactory()
        request = request_factory.post(request_path, data=input_params)
        request.user = user

        return (request, dict(form_class=form_class, node_type=node_type,
                                node_meta_type=node_meta_type))

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if not info.context or not info.context.user.is_authenticated:
            raise GraphQLAuthException()

        reqinput = cls.from_input_to_request(info.context.user, **input)
        ret = cls.do_request(reqinput[0], **reqinput[1])

        return cls(nodehandle=ret)

    class Meta:
        abstract = True

class CreateNIMutation(AbstractNIMutation):
    '''
    This class is used by the Mutation factory but it could be used as the
    superclass of a manualy coded class in case it's needed.
    '''
    class NIMetaClass:
        request_path   = None
        is_create      = True
        graphql_type   = None

    @classmethod
    def do_request(cls, request, **kwargs):
        form_class     = kwargs.get('form_class')
        nimetaclass    = getattr(cls, 'NIMetaClass')
        graphql_type   = getattr(nimetaclass, 'graphql_type')
        nimetatype     = getattr(graphql_type, 'NIMetaType')
        node_type      = getattr(nimetatype, 'ni_type').lower()
        node_meta_type = getattr(nimetatype, 'ni_metatype').capitalize()

        ## code from role creation
        form = form_class(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form,
                        node_type, node_meta_type)
            except UniqueNodeError:
                raise GraphQLError(
                    'A {} with that name already exists.'.format(node_type)
                )
            helpers.form_update_node(request.user, nh.handle_id, form)
            return nh
        else:
            # get the errors and return them
            raise GraphQLError('Form errors: {}'.format(form._errors))

class UpdateNIMutation(AbstractNIMutation):
    class NIMetaClass:
        request_path   = None
        graphql_type   = None

    @classmethod
    def do_request(cls, request, **kwargs):
        form_class     = kwargs.get('form_class')
        nimetaclass    = getattr(cls, 'NIMetaClass')
        graphql_type   = getattr(nimetaclass, 'graphql_type')
        nimetatype     = getattr(graphql_type, 'NIMetaType')
        node_type      = getattr(nimetatype, 'ni_type').lower()
        node_meta_type = getattr(nimetatype, 'ni_metatype').capitalize()
        handle_id      = request.POST.get('handle_id')

        nh, nodehandler = helpers.get_nh_node(handle_id)
        if request.POST:
            form = form_class(request.POST)
            if form.is_valid():
                # Generic node update
                helpers.form_update_node(request.user, nodehandler.handle_id, form)
                return nh
        else:
            # get the errors and return them
            raise GraphQLError('Form errors: {}'.format(form))

class DeleteNIMutation(AbstractNIMutation):
    nodehandle = graphene.Boolean(required=True)

    class NIMetaClass:
        request_path   = None
        graphql_type   = None

    @classmethod
    def do_request(cls, request, **kwargs):
        handle_id      = request.POST.get('handle_id')

        nh, node = helpers.get_nh_node(handle_id)
        helpers.delete_node(request.user, node.handle_id)

        return True

class NIMutationFactory():
    '''
    The mutation factory takes a django form, a node type and some parameters
    more and generates a mutation to create/update/delete nodes. If a higher
    degree of control is needed the classes CreateNIMutation, UpdateNIMutation
    and DeleteNIMutation could be subclassed to override any method's behaviour.
    '''

    node_type      = None
    node_meta_type = None
    request_path   = None

    create_mutation_class = CreateNIMutation
    update_mutation_class = UpdateNIMutation
    delete_mutation_class = DeleteNIMutation

    def __init_subclass__(cls, **kwargs):
        metaclass_name = 'NIMetaClass'
        nh_field = 'nodehandle'

        cls._create_mutation = None
        cls._update_mutation = None
        cls._delete_mutation = None

        # check defined form attributes
        ni_metaclass   = getattr(cls, metaclass_name)
        form           = getattr(ni_metaclass, 'form', None)
        create_form    = getattr(ni_metaclass, 'create_form', None)
        update_form    = getattr(ni_metaclass, 'update_form', None)
        request_path   = getattr(ni_metaclass, 'request_path', None)
        graphql_type   = getattr(ni_metaclass, 'graphql_type', NodeHandleType)

        # we'll retrieve these values NI type/metatype from the GraphQLType
        nimetatype     = getattr(graphql_type, 'NIMetaType')
        node_type      = getattr(nimetatype, 'ni_type').lower()

        # specify and set create and update forms
        assert form and not create_form and not update_form or\
            create_form and update_form and not form, \
            'You must specify form or both create_form and edit_form in {}'\
            .format(cls.__name__)

        if form:
            create_form = form
            update_form = form

        # create mutations
        class_name = 'CreateNI{}Mutation'.format(node_type.capitalize())
        attr_dict = {
            'django_form': create_form,
            'mutation_name': class_name,
            'request_path': request_path,
            'is_create': True,
            'graphql_type': graphql_type,
        }

        create_metaclass = type(metaclass_name, (object,), attr_dict)

        cls._create_mutation = type(
            class_name,
            (cls.create_mutation_class,),
            {
                nh_field: graphene.Field(graphql_type, required=True),
                metaclass_name: create_metaclass,
            },
        )

        class_name = 'UpdateNI{}Mutation'.format(node_type.capitalize())
        attr_dict['django_form']   = update_form
        attr_dict['mutation_name'] = class_name
        attr_dict['is_create']     = False
        update_metaclass = type(metaclass_name, (object,), attr_dict)

        cls._update_mutation = type(
            class_name,
            (cls.update_mutation_class,),
            {
                nh_field: graphene.Field(graphql_type, required=True),
                metaclass_name: update_metaclass,
            },
        )

        class_name = 'DeleteNI{}Mutation'.format(node_type.capitalize())
        del attr_dict['django_form']
        attr_dict['mutation_name'] = class_name
        delete_metaclass = type(metaclass_name, (object,), attr_dict)

        cls._delete_mutation = type(
            class_name,
            (cls.delete_mutation_class,),
            {
                metaclass_name: delete_metaclass,
            },
        )

    @classmethod
    def get_create_mutation(cls, *args, **kwargs):
        return cls._create_mutation

    @classmethod
    def get_update_mutation(cls, *args, **kwargs):
        return cls._update_mutation

    @classmethod
    def get_delete_mutation(cls, *args, **kwargs):
        return cls._delete_mutation

class GraphQLAuthException(Exception):
    def __init__(self, message=None):
        message = 'You must be logged in the system: {}'.format(
            ': {}'.format(message) if message else ''
        )
        super().__init__(message)

def get_connection_resolver(nodetype):
    def generic_list_resolver(self, info, **args):
        node_type = NodeType.objects.get(type=nodetype)

        if info.context and info.context.user.is_authenticated:
            ret = NodeHandle.objects.filter(node_type=node_type)
            """ret.filter(
                Q(creator=info.context.user) | Q(modifier=info.context.user)
            )"""

            if not ret:
                ret = []

            return ret
        else:
            raise GraphQLAuthException()

    return generic_list_resolver

def get_byid_resolver(nodetype):
    def generic_byid_resolver(self, info, **args):
        handle_id = args.get('handle_id')
        node_type = NodeType.objects.get(type=nodetype)

        ret = None

        if info.context and info.context.user.is_authenticated:
            if handle_id:
                ret = NodeHandle.objects.filter(node_type=node_type).get(handle_id=handle_id)
            else:
                raise GraphQLError('A handle_id must be provided')

            if not ret:
                raise GraphQLError("There isn't any {} with handle_id {}".format(nodetype, handle_id))

            return ret
        else:
            raise GraphQLAuthException()

    return generic_byid_resolver

class NOCAutoQuery(graphene.ObjectType):
    node = relay.Node.Field()
    getNodeById = graphene.Field(NodeHandleType, handle_id=graphene.Int())

    def resolve_getNodeById(self, info, **args):
        handle_id = args.get('handle_id')

        ret = None

        if info.context and info.context.user.is_authenticated:
            if handle_id:
                ret = NodeHandle.objects.get(handle_id=handle_id)
            else:
                raise GraphQLError('A valid handle_id must be provided')

            if not ret:
                raise GraphQLError("There isn't any {} with handle_id {}".format(nodetype, handle_id))

            return ret
        else:
            raise GraphQLAuthException()


    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        _nimeta = getattr(cls, 'NIMeta')
        graphql_types = getattr(_nimeta, 'graphql_types')

        assert graphql_types, \
            'A tuple with the types should be set in the Meta class of {}'.format(cls.__name__)

        # add list with pagination resolver
        # add by id resolver
        for graphql_type in graphql_types:
            ## extract values
            _nimetatype   = getattr(graphql_type, 'NIMetaType')

            ni_type = getattr(_nimetatype, 'ni_type')
            assert ni_type, '{} has not set its ni_type attribute'.format(cls.__name__)
            ni_metatype = getattr(_nimetatype, 'ni_metatype')
            assert ni_metatype, '{} has not set its ni_metatype attribute'.format(cls.__name__)

            node_type     = NodeType.objects.filter(type=ni_type).first()
            type_name     = node_type.type
            type_slug     = node_type.slug

            # add connection attribute
            field_name    = '{}s'.format(type_slug)
            resolver_name = 'resolve_{}'.format(field_name)

            connection_input = cls.build_filter_and_order(graphql_type, type_name)
            connection_meta = type('Meta', (object, ), dict(node=graphql_type))
            connection_class = type(
                '{}Connection'.format(graphql_type.__name__),
                (graphene.relay.Connection,),
                #(connection_type,),
                dict(Meta=connection_meta)
            )

            setattr(cls, field_name, graphene.relay.ConnectionField(connection_class, filter=graphene.Argument(connection_input)))
            setattr(cls, resolver_name, get_connection_resolver(type_name))

            ## build field and resolver byid
            field_name    = 'get{}ById'.format(type_name)
            resolver_name = 'resolve_{}'.format(field_name)

            setattr(cls, field_name, graphene.Field(graphql_type, handle_id=graphene.Int()))
            setattr(cls, resolver_name, get_byid_resolver(type_name))

    @classmethod
    def build_filter_and_order(cls, graphql_type, type_name):
        ## Maybe the input class should be declared in the types

        # build filter input class
        filter_attrib = {}
        #raise Exception(graphql_type.__dict__)
        for name, field in graphql_type.__dict__.items():
            if field and not isinstance(field, str) and field.__module__ == 'graphene.types.scalars':
                # adding filter attributes
                filter_attrib['{}'.format(name)] = field
                filter_attrib['{}_not'.format(name)] = field
                filter_attrib['{}_in'.format(name)] = graphene.List(graphene.NonNull(type(field)))
                filter_attrib['{}_not_in'.format(name)] = graphene.List(graphene.NonNull(type(field)))
                filter_attrib['{}_lt'.format(name)] = field
                filter_attrib['{}_lte'.format(name)] = field
                filter_attrib['{}_gt'.format(name)] = field
                filter_attrib['{}_gte'.format(name)] = field

                if isinstance(field, graphene.String):
                    filter_attrib['{}_contains'.format(name)] = field
                    filter_attrib['{}_not_contains'.format(name)] = field
                    filter_attrib['{}_starts_with'.format(name)] = field
                    filter_attrib['{}_not_starts_with'.format(name)] = field
                    filter_attrib['{}_ends_with'.format(name)] = field
                    filter_attrib['{}_not_ends_with'.format(name)] = field

                # adding order attributes

        filter_input = type('{}Filter'.format(type_name), (graphene.InputObjectType, ), filter_attrib)

        return filter_input
