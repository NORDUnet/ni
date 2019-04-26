# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene

from django import forms
from django.test import RequestFactory
from graphene import relay
from graphql import GraphQLError
from apps.noclook import helpers
from apps.noclook.forms import *
from pprint import pprint

# the payload fields should be defined as it isn't something we can guess
class AbstractNIMutation(relay.ClientIDMutation):
    @classmethod
    def __init_subclass_with_meta__(
        cls, output=None, input_fields=None, arguments=None, name=None, **options
    ):
        ''' In this method we'll build an input nested object using the form
        '''
        # read form
        django_form = getattr(cls, 'django_form', None)
        name = getattr(cls, 'mutation_name', None)

        # build fields into Input
        inner_fields = {}
        if django_form:
            for class_field_name, class_field in django_form.__dict__.items():
                if class_field_name == 'declared_fields' or class_field_name == 'base_fields':
                    for name, field in class_field.items():
                        # convert form field into mutation input field
                        graphene_field = cls.form_to_graphene_field(field)

                        if graphene_field:
                            if hasattr(django_form, 'Meta') and hasattr(django_form.Meta, 'exclude'):
                                if field not in django_form.Meta.exclude:
                                    inner_fields[name] = graphene_field
                            else:
                                inner_fields[name] = graphene_field
        else:
            if cls.__name__ in 'Delete':
                raise Exception(cls.__name__)
            # this would set a handle_id for the input param
            inner_fields['handle_id'] = forms.IntegerField(required=True)

        # add Input attribute to class
        inner_class = type('Input', (object,), inner_fields)
        setattr(cls, 'Input', inner_class)

        cls.set_mutate_and_get_payload()

        super(AbstractNIMutation, cls).__init_subclass_with_meta__(
            output, input_fields, arguments, name, **options
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
            # fields left out to implement
            # IPAddrField (CharField)
            # JSONField (CharField)
            # NodeChoiceField (ModelChoiceField)
            # DatePickerField (DateField)
            # description_field (CharField)
            # relationship_field (ChoiceField / IntegerField)
        else:
            return None

        return graphene_field

    # to be implemented by the subclass
    @classmethod
    def get_payload_parameters(cls, *args, **kwargs):
        '''This method should be implemented in the concerning subclasses
        '''
        raise Exception('The class {} doesn\'t implemet the get_payload_parameters method'.format(cls))

    @classmethod
    def set_mutate_and_get_payload(cls):
        '''This method should be implemented in the concerning subclasses
        '''
        raise Exception('The class {} doesn\'t implemet the set_mutate_and_get_payload method'.format(cls.__name__))

    class Meta:
        abstract = True

class CreateNIMutation(AbstractNIMutation):
    node_type      = None
    node_meta_type = None
    request_path   = None

    @classmethod
    def set_mutate_and_get_payload(cls):
        # get operation and check for method overrides
        mutate_function = cls.__dict__.get('create_mutate_and_get_payload')

        # set mutate_and_get_payload
        setattr(cls, 'mutate_and_get_payload', classmethod(mutate_function))

    @classmethod
    def get_payload_parameters(cls):
        for attr_name, attr_value in cls.__dict__.items():
            if attr_name != 'Input':
                pass

    @classmethod
    def create_mutate_and_get_payload(cls, root, info, **input):
        # get input values
        input_class = getattr(cls, 'Input', None)
        input_params = {}
        if input_class:
            for attr_name, attr_field in input_class.__dict__.items():
                print('Attribute {} value {}'.format(attr_name, attr_field))
                attr_value = input.get(attr_name)
                input_params[attr_name] = attr_value

        plparams = cls.get_payload_parameters()

        # get node_type and node_metatype
        # get request_path and request_data
        node_type      = getattr(cls, node_type)
        node_meta_type = getattr(cls, node_meta_type)
        request_path   = getattr(cls, request_path)

        ret = cls.do_create(
            node_type=node_type, node_metatype=node_meta_type,
            request_path=request_path, request_data=input_params
        )

        return cls(**plparams)

    @classmethod
    def do_create(cls, *args, **kwargs):
        # get form
        form_class = getattr(cls, 'django_form', None)
        node_type = kwargs.get('node_type')
        node_metatype = kwargs.get('node_metatype')
        input_params = kwargs.get('input_params')

        request_factory = RequestFactory()
        request_path = kwargs.get('request_path', '/')
        request_data = kwargs.get('request_data', {})
        request = request_factory.post(request_path, data=request_data)

        ## code from role creation
        form = form_class(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form,
                        node_type, node_metatype)
            except UniqueNodeError:
                raise GraphQLError(
                    'A {} with that name already exists.'.format(node_type)
                )
            helpers.form_update_node(request.user, nh.handle_id, form)
            #return redirect(nh.get_absolute_url())
        else:
            # get the errors and return them
            raise GraphQLError('Form errors: {}'.format(vars(form.errors)))

    class Meta:
        abstract = False

class UpdateNIMutation(AbstractNIMutation):
    @classmethod
    def set_mutate_and_get_payload(cls):
        # get operation and check for method overrides
        mutate_function = cls.__dict__.get('edit_mutate_and_get_payload')

        # set mutate_and_get_payload
        setattr(cls, 'mutate_and_get_payload', classmethod(mutate_function))

    @classmethod
    def edit_mutate_and_get_payload(cls, root, info, **input):
        pass

    # to be implemented by the subclass
    @classmethod
    def do_edit(cls, *args, **kwargs):
        raise Exception('The class {} doesn\'t implemet the \
            do_edit method'.format(cls))

    class Meta:
        abstract = False

class DeleteNIMutation(AbstractNIMutation):
    @classmethod
    def set_mutate_and_get_payload(cls):
        # get operation and check for method overrides
        mutate_function = cls.__dict__.get('delete_mutate_and_get_payload')

        # set mutate_and_get_payload
        setattr(cls, 'mutate_and_get_payload', classmethod(mutate_function))

    @classmethod
    def delete_mutate_and_get_payload(cls, root, info, **input):
        pass

    # to be implemented by the subclass
    @classmethod
    def do_delete(cls, *args, **kwargs):
        raise Exception('The class {} doesn\'t implemet the \
            do_delete method'.format(cls))

    class Meta:
        abstract = False

class NIMutationFactory():
    '''
    This class could have the methods create|update|delete_mutate_and_get_payload
    implemented to override the default functionality, but it must implement
    do_create|do_update|do_delete so these methods could be added to the generated
    classes that would be part of the schema
    '''

    node_type      = None
    node_meta_type = None
    request_path   = None

    def __init_subclass__(cls, **kwargs):
        cls._create_mutation = None
        cls._update_mutation = None
        cls._delete_mutation = None

        # check defined form attributes
        form        = getattr(cls, 'form', None)
        create_form = getattr(cls, 'create_form', None)
        update_form   = getattr(cls, 'update_form', None)

        assert form and not create_form and not update_form or\
            create_form and update_form and not form, \
            'You must specify form or both create_form and edit_form in {}'\
            .format(cls.__name__)

        if form:
            create_form = form
            update_form = form

        node_type      = getattr(cls, 'node_type', None)
        node_meta_type = getattr(cls, 'node_meta_type', None)
        request_path   = getattr(cls, 'request_path', None)
        class_name = 'CreateNI{}Mutation'.format(node_type.capitalize())

        attr_dict = {
            'django_form': create_form,
            'mutation_name': class_name,
            'node_type': node_type,
            'node_meta_type': node_meta_type,
            'request_path': request_path,
        }

        cls._create_mutation = type(
            class_name,
            (CreateNIMutation,),
            attr_dict,
        )

        class_name = 'UpdateNI{}Mutation'.format(node_type.capitalize())
        attr_dict['django_form'] = update_form
        attr_dict['mutation_name'] = class_name

        cls._update_mutation = type(
            class_name,
            (UpdateNIMutation,),
            attr_dict,
        )

        class_name = 'DeleteNI{}Mutation'.format(node_type.capitalize())
        del attr_dict['django_form']
        attr_dict['mutation_name'] = class_name

        cls._delete_mutation = type(
            class_name,
            (DeleteNIMutation,),
            attr_dict,
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
    node_type      = 'role'
    node_meta_type = 'Logical'
    request_path   = '/'

    create_form    = NewRoleForm
    update_form    = EditRoleForm

class NOCRootMutation(graphene.ObjectType):
    create_role = NIRoleMutationFactory.get_create_mutation().Field()
    #update_role = NIRoleMutationFactory.get_update_mutation().Field()
    #delete_role = NIRoleMutationFactory.get_delete_mutation().Field()
