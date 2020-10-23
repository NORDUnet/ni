# Generated by Django 2.2.12 on 2020-06-04 12:26

from django.db import migrations
import apps.noclook.vakt.utils as sriutils


def forwards_func(apps, schema_editor):
    Action = apps.get_model('actstream', 'Action')
    NodeHandle = apps.get_model('noclook', 'NodeHandle')

    for action in Action.objects.all():
        contenttype = action.action_object_content_type

        if contenttype and contenttype.app_label == 'noclook' and \
            contenttype.model == 'nodehandle':
            # get contexts for action_object
            node_exists = NodeHandle.objects.\
                filter(handle_id=action.action_object_object_id).exists()

            if node_exists:
                action_object = NodeHandle.objects.get(
                    handle_id=action.action_object_object_id
                )
                contexts = sriutils.get_nh_named_contexts(action_object)
                action_data = action.data

                if action_data and 'noclook' in action_data:
                    action_data['noclook']['contexts'] = contexts
                    action.data = action_data
                    action.save()


def backwards_func(apps, schema_editor):
    Action = apps.get_model('actstream', 'Action')
    NodeHandle = apps.get_model('noclook', 'NodeHandle')

    for action in Action.objects.all():
        contenttype = action.action_object_content_type

        if contenttype and contenttype.app_label == 'noclook' and \
            contenttype.model == 'nodehandle':
            action_data = action.data

            if action_data and 'noclook' in action_data:
                del action_data['noclook']['contexts']
                action.data = action_data
                action.save()


class Migration(migrations.Migration):

    dependencies = [
        ('noclook', '0022_network_types_20200423_0646'),
    ]

    operations = [
        migrations.RunPython(forwards_func, backwards_func),
    ]
