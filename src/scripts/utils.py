import os
import logging
import json
from configparser import SafeConfigParser
import random
import django_hack  # Keep

from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
from apps.noclook import activitylog
from apps.noclook.models import NodeType, NodeHandle

logger = logging.getLogger('noclook_utils')
django_hack.nop()


def load_json(json_dir, starts_with='', with_filename=False):
    """
    Thinks all files in the supplied dir are text files containing json.
    """
    logger.info('Loading data from {!s}.'.format(json_dir))
    try:
        for subdir, dirs, files in os.walk(json_dir):
            gen = (_file for _file in files if _file.startswith(starts_with))
            for a_file in gen:
                try:
                    f = open(os.path.join(subdir, a_file), 'r')
                    if with_filename:
                        yield json.load(f), a_file
                    else:
                        yield json.load(f)
                except ValueError as e:
                    logger.error('Encountered a problem with {f}.'.format(f=a_file))
                    logger.error(e)
    except IOError as e:
        logger.error('Encountered a problem with {d}.'.format(d=json_dir))
        logger.error(e)


def init_config(p):
    """
    Initializes the configuration file located in the path provided.
    """
    try:
        config = SafeConfigParser()
        config.read(p)
        return config
    except IOError as e:
        logger.error("I/O error({0}): {1}".format(e))


def get_user(username='noclook'):
    """
    Gets or creates a user that can be used to insert data.
    """
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        passwd = generate_password(30)
        user = User.objects.create_user(username, '', passwd)
    return user


def generate_password(n):
    return ''.join([random.SystemRandom().choice('abcdefghijklmnopqrstuvwxyz0123456789@#$%^&*(-_=+)') for i in range(n)])


NODE_TYPE_CACHE = {}


def get_node_type(type_name):
    """
    Returns or creates and returns the NodeType object with the supplied
    name.
    """
    if type_name in NODE_TYPE_CACHE:
        return NODE_TYPE_CACHE[type_name]

    node_type, created = NodeType.objects.get_or_create(type=type_name, defaults={'slug': slugify(type_name)})
    NODE_TYPE_CACHE[type_name] = node_type
    return node_type


def get_unique_node_handle(node_name, node_type_name, node_meta_type, case_insensitive=True):
    """
    Takes the arguments needed to create a NodeHandle, if there already
    is a NodeHandle with the same name and type it will be considered
    the same one.
    Returns a NodeHandle object.
    """
    user = get_user()
    node_type = get_node_type(node_type_name)
    query = {
        'node_type': node_type,
        'defaults': {
            'node_meta_type': node_meta_type,
            'creator': user,
            'modifier': user,
            'node_name': node_name
        }
    }
    if case_insensitive:
        query['node_name__iexact'] = node_name
    else:
        query['node_name'] = node_name
    node_handle, created = NodeHandle.objects.get_or_create(**query)
    if created:
        print('Created node: {}'.format(node_name))
        activitylog.create_node(user, node_handle)
    return node_handle


def get_unique_node_handle_by_name(node_name, node_type_name, node_meta_type, allowed_node_types=None):
    """
    Takes the arguments needed to create a NodeHandle, if there already
    is a NodeHandle with the same name considered the same one.

    If the allowed_node_types is set the supplied node types will be used for filtering.

    Returns a NodeHandle object.
    """
    try:
        if not allowed_node_types:
            allowed_node_types = [node_type_name]
        return NodeHandle.objects.filter(node_type__type__in=allowed_node_types).get(node_name__iexact=node_name)
    except NodeHandle.DoesNotExist:
        return get_unique_node_handle(node_name, node_type_name, node_meta_type)
    except NodeHandle.MultipleObjectsReturned:
        logger.error("Assumed unique node not unique: {0}".format(node_name))
        return None


def create_node_handle(node_name, node_type_name, node_meta_type):
    """
    Takes the arguments needed to create a NodeHandle.
    Returns a NodeHandle object.
    """
    user = get_user()
    node_type = get_node_type(node_type_name)
    node_handle = NodeHandle.objects.create(node_name=node_name, node_type=node_type, node_meta_type=node_meta_type,
                                            creator=user, modifier=user)
    node_handle.save()
    activitylog.create_node(user, node_handle)
    return node_handle
