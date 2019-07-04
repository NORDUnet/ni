# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django.db import IntegrityError, transaction
from django.core.exceptions import ObjectDoesNotExist
from django.utils.text import slugify
from django.conf import settings
from .models import NordunetUniqueId, UniqueIdGenerator


def unique_id_map(slug):
    """
    :param slug: A slug that specifies the type of object that we want to generate ID for.
    :return: Tuple of UniqueIdGenerator instance and an optional subclass of UniqueId collection.
    """
    # turn slug into id
    name = '{}_id'.format(slug.replace('-', '_').lower())
    return UniqueIdGenerator.objects.get(name=name), NordunetUniqueId


def generator_links():
    result = []
    for gen in UniqueIdGenerator.objects.all():
        slug = slugify(gen.name.replace('_id', '')).replace('_', '-')
        name = gen.name.replace('_', ' ').title().replace(settings.BRAND.title(), settings.BRAND)

        result.append({'slug': slug, 'title': name})

    return result


def is_free_unique_id(unique_id_collection, unique_id):
    """
    Checks if a Unique ID is unused or reserved.
    :param unique_id_collection: Instance of a UniqueId subclass.
    :param unique_id: String
    :return: Boolean
    """
    try:
        obj = unique_id_collection.objects.get(unique_id=unique_id)
        if obj.reserved:
            return True
    except ObjectDoesNotExist:
        return True
    return False


def get_collection_unique_id(unique_id_generator, unique_id_collection):
    """
    Return the next available unique id by counting up the id generator until an available id is found
    in the unique id collection.
    :param unique_id_generator: UniqueIdGenerator instance
    :param unique_id_collection: UniqueId subclass instance
    :return: String unique id
    """
    created = False
    while not created:
        unique_id = unique_id_generator.get_id()
        obj, created = unique_id_collection.objects.get_or_create(unique_id=unique_id)
    return unique_id


def register_unique_id(unique_id_collection, unique_id):
    """
    Creates a new Unique ID or unreserves an already created but reserved id.
    :param unique_id_collection: Instance of a UniqueId subclass.
    :param unique_id: String
    :return: True for success, False for failure.
    """
    obj, created = unique_id_collection.objects.get_or_create(unique_id=unique_id)
    if not created and not obj.reserved:
        raise IntegrityError('ID: %s already in the db and in use.' % unique_id)
    elif obj.reserved:  # ID was reserved, unreserv it.
        obj.reserved = False
        obj.save()
    return True


def bulk_reserve_id_range(start, end, unique_id_generator, unique_id_collection, reserve_message, reserver, site=None):
    """
    Reserves IDs start to end in the format used in the unique id generator in the unique id collection without
    incrementing the unique ID generator.

    bulk_reserve_ids(100, 102, nordunet_service_unique_id_generator, nordunet_unique_id_collection...) would try to
    reserve NU-S000100, NU-S000101 and NU-S000102 in the NORDUnet unique ID collection.

    :param start: Integer
    :param end: Integer
    :param unique_id_generator: Instance of UniqueIdGenerator
    :param unique_id_collection: Instance of UniqueId subclass
    :param reserve_message: String
    :param reserver: Django user object
    :return: List of reserved unique_id_collection objects.
    """
    reserve_list = []
    prefix = suffix = ''
    if unique_id_generator.prefix:
        prefix = unique_id_generator.prefix
    if unique_id_generator.suffix:
        suffix = unique_id_generator.suffix
    for unique_id in range(start, end+1):
        reserve_list.append(unique_id_collection(
            unique_id='%s%s%s' % (prefix, str(unique_id).zfill(unique_id_generator.base_id_length), suffix),
            reserved=True,
            reserve_message=reserve_message,
            reserver=reserver,
            site=site,
        ))
    unique_id_collection.objects.bulk_create(reserve_list)
    return reserve_list


def reserve_id_sequence(num_of_ids, unique_id_generator, unique_id_collection, reserve_message, reserver, site=None):
    """
    Reserves IDs by incrementing the unique ID generator.
    :param num_of_ids: Number of IDs to reserve.
    :param unique_id_generator: Instance of UniqueIdGenerator
    :param unique_id_collection: Instance of UniqueId subclass
    :param reserve_message: String
    :param reserver: Django user object
    :return: List of dicts with reserved ids, reserve message and eventual error message.
    """
    reserve_list = []
    for x in range(0, num_of_ids):
        unique_id = unique_id_generator.get_id()
        error_message = ''
        try:
            with transaction.atomic():
                unique_id_collection.objects.create(unique_id=unique_id, reserved=True,
                                                    reserve_message=reserve_message, reserver=reserver, site=site)
        except IntegrityError:
            error_message = 'ID already in database. Manual check needed.'
        reserve_list.append({'unique_id': unique_id, 'reserve_message': reserve_message, 'error_message': error_message})
    return reserve_list
