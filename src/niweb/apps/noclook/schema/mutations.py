# -*- coding: utf-8 -*-

import graphene

from django import forms
from graphene import relay
from apps.noclook.forms import *
from pprint import pprint

# what we actually need here:
# A relay.ClientIDMutation subclass (NIMutation) that wraps a django form inside
# it should use the form to generate the input fields of the mutation
# the mutate_and_get_payload method should contain the create/edit django view
# code. It also may be a good idea to implement the most of the boilerplate of
# these views in this class.
# it could be a good idea to encapsulate the create, update and delete mutations
# into a single class

class MockupNIMutation():
    pass
    # get_create_mutation()
    # get_update_mutation()
    # get_delete_mutation()

    @classmethod
    def edit_mutate_and_get_payload(cls, root, info, **input):
        pass
        # in the template methods of the superclass is where the boilerplate code
        # should be called, like checking form.is_valid() to trigger all the clean
        # validation.
        # Also it should get the errors from the form to be added to the output

def empty_mutate_and_get_payload(cls):
    pass

def create_mutate_and_get_payload(cls):
    pass

def edit_mutate_and_get_payload(cls):
    pass

def delete_mutate_and_get_payload(cls):
    pass

def form_to_graphene_field(form_field):
    graphene_field = None

    # get attributes
    graph_kwargs = {}

    for attr_name, attr_value in form_field.__dict__.items():
        if attr_name == 'required':
            graph_kwargs['required'] = attr_value

    # compare types
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

    return graphene_field

class AbstractNIMutation(relay.ClientIDMutation):
    @classmethod
    def __init_subclass_with_meta__(
        cls, **options
    ):
        # read form
        django_form = getattr(cls, 'django_form', None)

        # build fields into Input
        inner_fields = {}
        if django_form:
            for class_field_name, class_field in django_form.__dict__.items():
                if class_field_name == 'declared_fields' or class_field_name == 'base_fields':
                    for name, field in class_field.items():
                        # convert form field into mutation input field
                        graphene_field = form_to_graphene_field(field)

                        if  hasattr(django_form, 'Meta') and hasattr(django_form.Meta, 'exclude'):
                            if field not in django_form.Meta.exclude:
                                inner_fields[name] = graphene_field
                        else:
                            inner_fields[name] = graphene_field

        # add Input attribute to class
        inner_class = type('Input', (object,), inner_fields)
        setattr(cls, 'Input', inner_class)

        # build and set mutate_and_get_payload
        setattr(cls, 'mutate_and_get_payload', classmethod(empty_mutate_and_get_payload))

        foo = options.get('abstract')

        super(AbstractNIMutation, cls).__init_subclass_with_meta__(
            **options
        )

    class Meta:
        abstract = True

'''class CreateNIMutation(AbstractNIMutation):
    pass

class UpdateNIMutation(AbstractNIMutation):
    pass

class DeleteNIMutation(AbstractNIMutation):
    pass'''

class CreateNIRoleMutation(AbstractNIMutation):
    django_form = NewRoleForm

    class Meta:
        abstract = False

class NIMutationFactory():
    def __init_subclass__(cls, default_name, **kwargs):
        pass
        # check defined form attributes

"""class RoleMutation(NIMutationFactory):
    # only form | create_form and edit_form should be defined at the same time
    form = 'NewRoleForm' # we'll get the input fields from the form, single form for Create/Edit
    create_form = 'NewRoleForm' # use different forms to create
    edit_form = 'EditRoleForm'  # or to edit, both or none should be defined

    @classmethod
    def create_mutate_and_get_payload(cls, root, info, ship_name, faction_id, client_mutation_id=None):
        '''
        this method would override be the mutate_and_get_payload for the get_create_mutation
        '''
        pass"""
