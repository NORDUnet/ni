# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import *
from apps.noclook.tests.stressload.data_generator import NetworkFakeDataGenerator
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

logger = logging.getLogger('noclook.management.datafaker')

class Command(BaseCommand):
    help = 'Create fake data for the Network module'
    generated_types = [
        'Customer', 'End User', 'Site Owner', 'Provider', 'Peering Group', 'Peering Partner',
        'Cable', 'Port', 'Host', 'Router', 'Switch']

    option_organizations = 'organizations'
    option_equipment = 'equipmentcables'
    option_deleteall = 'deleteall'
    cmd_name = 'datafaker'

    def add_arguments(self, parser):
        parser.add_argument("--{}".format(self.option_organizations),
                    help="Create organization nodes", type=int, default=0)
        parser.add_argument("--{}".format(self.option_equipment),
                    help="Create equipment and cables nodes", type=int, default=0)
        parser.add_argument("-d", "--{}".format(self.option_deleteall), action='store_true',
                    help="BEWARE: This command deletes information in the database")

    def handle(self, *args, **options):
        if options[self.option_deleteall]:
            self.delete_network_nodes()
            return

        if options[self.option_organizations]:
            numnodes = options[self.option_organizations]
            if numnodes > 0:
                self.stdout\
                    .write('Forging fake organizations: {} for each subtype:'\
                    .format(numnodes))
                self.create_organizations(numnodes)

        if options[self.option_equipment]:
            numnodes = options[self.option_equipment]
            if numnodes > 0:
                self.stdout\
                    .write('Forging fake equipement & cables: {} for each subtype:'\
                    .format(numnodes))
                self.create_equipment_cables(numnodes)

        return

    def create_entities(self, numnodes, create_funcs):
        total_nodes = numnodes * len(create_funcs)
        created_nodes = 0
        self.printProgressBar(0, total_nodes)

        for create_func in create_funcs:
            for i in range(numnodes):
                # dirty hack to get rid of accidental unscaped strings
                loop_lock = True
                safe_tries = 5

                while loop_lock and safe_tries > 0:
                    try:
                        node = create_func()
                        loop_lock = False
                    except:
                        safe_tries = safe_tries - 1

                created_nodes = created_nodes + 1
                self.printProgressBar(created_nodes, total_nodes)

    def create_organizations(self, numnodes):
        generator = NetworkFakeDataGenerator()

        create_funcs = [
            generator.create_customer,
            generator.create_end_user,
            generator.create_peering_partner,
            generator.create_peering_group,
            generator.create_site_owner,
        ]

        self.create_entities(numnodes, create_funcs)

    def create_equipment_cables(self, numnodes):
        generator = NetworkFakeDataGenerator()

        create_funcs = [
            generator.create_cable,
            generator.create_host,
            generator.create_router,
            generator.create_switch,
        ]

        self.create_entities(numnodes, create_funcs)

    def delete_network_nodes(self):
        if settings.DEBUG: # guard against accidental deletion on the wrong environment
            delete_types = self.generated_types

            total_nodes = 0

            for delete_type in delete_types:
                total_nodes = total_nodes + self.get_node_num(delete_type)

            if total_nodes > 0:
                self.stdout.write('Delete {} nodes:'.format(total_nodes))
                deleted_nodes = 0

                self.printProgressBar(deleted_nodes, total_nodes)

                for delete_type in delete_types:
                    deleted_nodes = self.delete_type(delete_type, deleted_nodes, total_nodes)

            # delete node types
            for delete_type in delete_types:
                NodeType.objects.filter(type=delete_type).delete()

    def get_nodetype(self, type_name):
        return NetworkFakeDataGenerator.get_nodetype(type_name)

    def get_node_num(self, type_name):
        node_type = self.get_nodetype(type_name)
        node_num = NodeHandle.objects.filter(node_type=node_type).count()

        return node_num

    def delete_type(self, type_name, deleted_nodes, total_nodes):
        node_type = self.get_nodetype(type_name)
        node_num = self.get_node_num(type_name)

        [x.delete() for x in NodeHandle.objects.filter(node_type=node_type)]
        deleted_nodes = deleted_nodes + node_num

        if node_num > 0:
            self.printProgressBar(deleted_nodes, total_nodes)

        return deleted_nodes

    def printProgressBar (self, iteration, total, prefix = 'Progress', suffix = 'Complete', decimals = 1, length = 100, fill = '█'):
        """
        Call in a loop to create terminal progress bar
        (from https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console)
        @params:
            iteration   - Required  : current iteration (Int)
            total       - Required  : total iterations (Int)
            prefix      - Optional  : prefix string (Str)
            suffix      - Optional  : suffix string (Str)
            decimals    - Optional  : positive number of decimals in percent complete (Int)
            length      - Optional  : character length of bar (Int)
            fill        - Optional  : bar fill character (Str)
        """
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        self.stdout.write('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), ending = '\r')
        # Print New Line on Complete
        if iteration == total:
            self.stdout.write('')
