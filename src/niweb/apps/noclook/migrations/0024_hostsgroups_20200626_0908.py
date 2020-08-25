from apps.nerds.lib.consumer_util import get_user
from django.db import migrations
from django.utils.text import slugify

import norduniclient as nc
import time

try:
    from neo4j.exceptions import CypherError
except ImportError:
    try:
        # pre neo4j 1.4
        from neo4j.v1.exceptions import CypherError
    except ImportError:
        # neo4j 1.1
        from neo4j.v1.api import CypherError

import apps.noclook.vakt.utils as sriutils


host_types = [
    'Host', 'Switch', 'Firewall',
]

def forwards_func(apps, schema_editor):
    NodeType = apps.get_model('noclook', 'NodeType')
    NodeHandle = apps.get_model('noclook', 'NodeHandle')
    Context = apps.get_model('noclook', 'Context')
    NodeHandleContext = apps.get_model('noclook', 'NodeHandleContext')
    Dropdown = apps.get_model('noclook', 'Dropdown')
    Choice = apps.get_model('noclook', 'Choice')
    User = apps.get_model('auth', 'User')

    # wait for neo4j to be available
    neo4j_inited = False
    failure_count = 3
    while not neo4j_inited and failure_count != 0:
        if nc.graphdb.manager:
            neo4j_inited = True
        else:
            failure_count = failure_count - 1
            time.sleep(2)

    if neo4j_inited:
        username = 'noclook'
        passwd = User.objects.make_random_password(length=30)
        user = None

        try:
            user = User.objects.get(username=username)
        except:
            user = User(username=username, password=passwd).save()

        # get the values from the old group dropdown
        groups_dropname = 'responsible_groups'

        groupdropdown, created = \
            Dropdown.objects.get_or_create(name=groups_dropname)
        choices = Choice.objects.filter(dropdown=groupdropdown)

        group_type, created = NodeType.objects.get_or_create(type='Group',
                                                                slug='group')
        groups_dict = {}

        community_context = sriutils.get_community_context(Context)

        host_type_objs = []
        for host_type_str in host_types:
            host_type, created = NodeType.objects.get_or_create(
                type=host_type_str,
                slug=slugify(host_type_str)
            )
            host_type_objs.append(host_type)

        if NodeHandle.objects.filter(node_type__in=host_type_objs).exists():
            for choice in choices:
                node_name = choice.name

                group_nh, created = NodeHandle.objects.get_or_create(
                    node_name=node_name, node_type=group_type,
                    node_meta_type=nc.META_TYPES[1], # Logical
                    creator=user,
                    modifier=user,
                )

                if created:
                    try:
                        nc.create_node(
                                nc.graphdb.manager,
                            node_name,
                            group_nh.node_meta_type,
                            group_type.type,
                            group_nh.handle_id
                        )
                    except CypherError:
                        pass

                    NodeHandleContext(
                        nodehandle=group_nh,
                        context=community_context
                    ).save()

                groups_dict[node_name] = group_nh

            # if there's nodes on the db, create groups with these values
            prop_methods = {
                'responsible_group': 'set_takes_responsibility',
                'support_group': 'set_supports',
            }

            # loop over entity types
            for host_type in host_type_objs:
                nhs = NodeHandle.objects.filter(node_type=host_type)

                # loop over entities of this type
                for nh in nhs:
                    host_node = nc.get_node_model(nc.graphdb.manager,
                                                    nh.handle_id)

                    for prop, method_name in prop_methods.items():
                        # get old data
                        prop_value = host_node.data.get(prop, None)

                        # link matched group
                        if prop_value and prop_value in groups_dict:
                            group_nh = groups_dict[prop_value]
                            group_node = nc.get_node_model(nc.graphdb.manager,\
                                group_nh.handle_id)

                            method = getattr(group_node, method_name, None)

                            if method:
                                method(nh.handle_id)

                            # remove old property
                            host_node.remove_property(prop)


def backwards_func(apps, schema_editor):
    NodeType = apps.get_model('noclook', 'NodeType')
    NodeHandle = apps.get_model('noclook', 'NodeHandle')
    Dropdown = apps.get_model('noclook', 'Dropdown')
    Choice = apps.get_model('noclook', 'Choice')
    User = apps.get_model('auth', 'User')
    user = get_user(usermodel=User)

    # get the values from the old group dropdown
    groups_dropname = 'responsible_groups'

    groupdropdown, created = \
        Dropdown.objects.get_or_create(name=groups_dropname)
    choices = Choice.objects.filter(dropdown=groupdropdown)

    # get group options
    groups_opts_dict = {}

    host_type_objs = []
    for host_type_str in host_types:
        host_type, created = NodeType.objects.get_or_create(
            type=host_type_str,
            slug=slugify(host_type_str)
        )
        host_type_objs.append(host_type)

    if NodeHandle.objects.filter(node_type__in=host_type_objs).exists():
        # fill choice dict
        for choice in choices:
            choice_name = choice.name
            groups_opts_dict[choice_name] = choice

        # loop over entity types
        for host_type_str in host_types:
            host_type, created = NodeType.objects.get_or_create(
                type=host_type_str,
                slug=slugify(host_type_str)
            )

            nhs = NodeHandle.objects.filter(node_type=host_type)

            # loop over entities of this type
            for nh in nhs:
                host_node = nc.get_node_model(nc.graphdb.manager, nh.handle_id)

                attr_val_dict = {
                    'responsible_group': host_node.incoming.get('Takes_responsibility'),
                    'support_group': host_node.incoming.get('Supports'),
                }

                for attr_name, rels in attr_val_dict.items():
                    if rels:
                        # unlink group and get its name
                        relationship = rels[0]
                        node = relationship['node']
                        ngroup_name = node.data.get('name', None)

                        if ngroup_name in groups_opts_dict:
                            group_choice = groups_opts_dict[ngroup_name]

                            # add old property value
                            host_node.add_property(attr_name, group_choice.value)

                        # delete relationship anyways
                        nc.delete_relationship(
                            nc.graphdb.manager, relationship['relationship_id'])

    # delete created groups (both postgresql and neo4j)
    group_type, created = NodeType.objects.get_or_create(type='Group', slug='group')
    groups_nhs = NodeHandle.objects.filter(node_type=group_type)
    for group_nh in groups_nhs:
        q = """
            MATCH (n:Group {handle_id:{handle_id}}) DETACH DELETE n
            """
        nc.query_to_dict(nc.graphdb.manager, q, handle_id=group_nh.handle_id)

        group_nh.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('noclook', '0023_activitylog_context_20200604_1226'),
    ]

    operations = [
        migrations.RunPython(forwards_func, backwards_func),
    ]
