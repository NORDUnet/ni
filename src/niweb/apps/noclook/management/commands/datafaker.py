# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import *
from apps.noclook.tests.stressload.data_generator import NetworkFakeDataGenerator
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

logger = logging.getLogger('noclook.management.datafaker')

class Command(BaseCommand):
    help = 'Create fake data for the Network module'

    def add_arguments(self, parser):
        parser.add_argument("--equipmentcables",
                    help="Create equipment and cables nodes", type=int, default=20)
        parser.add_argument("-d", "--deleteall", action='store_true',
                    help="BEWARE: This command deletes information in the database")

    def handle(self, *args, **options):
        if options['deleteall']:
            self.delete_network_nodes()
            return

        if options['equipmentcables']:
            numnodes = options['equipmentcables']
            self.create_equipment_cables(numnodes)
            return

    def create_equipment_cables(self, numnodes):
        generator = NetworkFakeDataGenerator()

        self.printProgressBar(0, numnodes)

        for i in range(numnodes):
            cable = generator.create_cable()
            self.printProgressBar(i, numnodes)

        self.printProgressBar(numnodes, numnodes)

    def delete_network_nodes(self):
        if settings.DEBUG: # guard against accidental deletion on the wrong environment
            cable_type = self.get_nodetype('Cable')
            provider_type = self.get_nodetype('Provider')
            port_type = self.get_nodetype('Port')

            cable_num = NodeHandle.objects.filter(node_type=cable_type).count()
            provider_num = NodeHandle.objects.filter(node_type=provider_type).count()
            ports_num = NodeHandle.objects.filter(node_type=port_type).count()

            total_nodes = cable_num + provider_num + ports_num

            if total_nodes > 0:
                deleted_nodes = 0

                self.printProgressBar(deleted_nodes, total_nodes)

                # delete cables
                [x.delete() for x in NodeHandle.objects.filter(node_type=cable_type)]
                deleted_nodes = deleted_nodes + cable_num
                self.printProgressBar(deleted_nodes, total_nodes)

                # delete providers
                [x.delete() for x in NodeHandle.objects.filter(node_type=provider_type)]
                deleted_nodes = deleted_nodes + provider_num
                self.printProgressBar(deleted_nodes, total_nodes)

                # delete ports
                [x.delete() for x in NodeHandle.objects.filter(node_type=port_type)]
                deleted_nodes = deleted_nodes + ports_num
                self.printProgressBar(deleted_nodes, total_nodes)

    def get_nodetype(self, type_name):
        return NodeType.objects.get_or_create(type=type_name, slug=type_name.lower())[0]

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
