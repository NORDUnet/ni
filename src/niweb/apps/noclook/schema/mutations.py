# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene

from apps.noclook import helpers
from apps.noclook.forms import *
from django import forms
from django.test import RequestFactory
from graphene import relay
from graphql import GraphQLError
from norduniclient.exceptions import UniqueNodeError, NoRelationshipPossible
from pprint import pprint

from .types import *

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
    def from_input_to_request(cls, **input):
        '''
        Gets the input data from the input inner class, and this is build using
        the fields in the django form. It returns a nodehandle of the type
        defined by the NIMetaClass
        '''
        # get ni metaclass data
        ni_metaclass   = getattr(cls, 'NIMetaClass')
        form_class     = getattr(ni_metaclass, 'django_form', None)
        node_type      = getattr(ni_metaclass, 'node_type')
        node_meta_type = getattr(ni_metaclass, 'node_meta_type')
        request_path   = getattr(ni_metaclass, 'request_path', '/')
        is_create      = getattr(ni_metaclass, 'is_create', False)

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
        request.user = get_logger_user()

        return (request, dict(form_class=form_class, node_type=node_type,
                                node_meta_type=node_meta_type))

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        reqinput = cls.from_input_to_request(**input)
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
        node_type      = None
        node_meta_type = None
        request_path   = None
        is_create      = True

    @classmethod
    def do_request(cls, request, **kwargs):
        form_class     = kwargs.get('form_class')
        node_type      = kwargs.get('node_type')
        node_meta_type = kwargs.get('node_meta_type')

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
            raise GraphQLError('Form errors: {}'.format(form))

class UpdateNIMutation(AbstractNIMutation):
    class NIMetaClass:
        node_type      = None
        node_meta_type = None
        request_path   = None

    @classmethod
    def do_request(cls, request, **kwargs):
        form_class     = kwargs.get('form_class')
        node_type      = kwargs.get('node_type')
        node_meta_type = kwargs.get('node_meta_type')
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
    class NIMetaClass:
        node_type      = None
        node_meta_type = None
        request_path   = None

    @classmethod
    def do_request(cls, request, **kwargs):
        pass

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
        node_type      = getattr(ni_metaclass, 'node_type', None)
        node_meta_type = getattr(ni_metaclass, 'node_meta_type', None)
        request_path   = getattr(ni_metaclass, 'request_path', None)
        nodetype       = getattr(ni_metaclass, 'nodetype', NodeHandleType)

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
            'node_type': node_type,
            'node_meta_type': node_meta_type,
            'request_path': request_path,
            'is_create': True,
        }

        create_metaclass = type(metaclass_name, (object,), attr_dict)

        cls._create_mutation = type(
            class_name,
            (cls.create_mutation_class,),
            {
                nh_field: graphene.Field(nodetype, required=True),
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
                nh_field: graphene.Field(nodetype, required=True),
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
                nh_field: graphene.Field(nodetype, required=True),
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

class NIRoleMutationFactory(NIMutationFactory):
    create_form    = NewRoleForm
    update_form    = EditRoleForm

    class NIMetaClass:
        node_type      = 'role'
        node_meta_type = 'Logical'
        request_path   = '/'
        form           = NewRoleForm
        nodetype       = RoleType

    class Meta:
        abstract = False

class CreateRoleNIMutation(CreateNIMutation):
    '''This class is not used but left out as documentation in the case that as
    finer grain of control is needed'''
    nodehandle = graphene.Field(RoleType, required=True)

    class NIMetaClass:
        node_type      = 'role'
        node_meta_type = 'Logical'
        request_path   = '/'
        django_form    = NewRoleForm

    class Meta:
        abstract = False

class NOCRootMutation(graphene.ObjectType):
    create_role = NIRoleMutationFactory.get_create_mutation().Field()
    update_role = NIRoleMutationFactory.get_update_mutation().Field()
    delete_role = NIRoleMutationFactory.get_delete_mutation().Field()
