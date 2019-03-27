# -*- coding: utf-8 -*-

from django.core.management import call_command

import norduniclient as nc
from norduniclient.exceptions import UniqueNodeError, NodeNotFound
import norduniclient.models as ncmodels

from apps.noclook.models import NodeHandle, NodeType, User

from ..neo4j_base import NeoTestCase

import tempfile

__author__ = 'ffuentes'

class CsvImportTest(NeoTestCase):
    cmd_name = 'csvimport'

    organizations_str = """"account_id";"account_name";"description";"phone";"website";"customer_id";"type";"parent_account"
1;"Tazz";;"453-896-3068";"https://studiopress.com";"DRIVE";"University, College";
2;"Wikizz";;"531-584-0224";"https://ihg.com";"DRIVE";"University, College";
3;"Browsecat";;"971-875-7084";"http://skyrock.com";"ROAD";"University, College";"Tazz"
4;"Dabfeed";;"855-843-6570";"http://merriam-webster.com";"LANE";"University, College";"Wikizz"
    """

    contacts_str = """"salutation";"first_name";"last_name";"title";"contact_role";"contact_type";"mailing_street";"mailing_city";"mailing_zip";"mailing_state";"mailing_country";"phone";"mobile";"fax";"email";"other_email";"PGP_fingerprint";"account_name"
"Honorable";"Caesar";"Newby";;"Computer Systems Analyst III";"Person";;;;;"China";"897-979-7799";"501-503-1550";;"cnewby0@joomla.org";;;"Gabtune"
"Mr";"Zilvia";"Linnard";;"Analog Circuit Design manager";"Person";;;;;"Indonesia";"205-934-3477";"473-256-5648";;"zlinnard1@wunderground.com";;;"Babblestorm"
"Honorable";"Reamonn";"Scriviner";;"Tax Accountant";"Person";;;;;"China";"200-111-4607";"419-639-2648";;"rscriviner2@moonfruit.com";;;"Babbleblab"
"Mrs";"Franny";"Bainton";;"Software Consultant";"Person";;;;;"China";"877-832-9647";"138-608-6235";;"fbainton3@si.edu";;;"Mudo"
"Rev";"Kiri";"Janosevic";;"Physical Therapy Assistant";"Person";;;;;"China";"568-690-1854";"118-569-1303";;"kjanosevic4@umich.edu";;;"Youspan"
    """

    secroles_str = """"Organisation";"Contact";"Role"
"Chalmers";"CTH Abuse";"Abuse"
"Chalmers";"CTH IRT";"IRT Gruppfunktion"
"Chalmers";"Hans Nilsson";"Övrig incidentkontakt"
"Chalmers";"Stefan Svensson";"Övrig incidentkontakt"
"Chalmers";"Karl Larsson";"Primär incidentkontakt"
    """

    def setUp(self):
        super(CsvImportTest, self).setUp()
        # write organizations csv file to disk
        self.organizations_file = self.write_string_to_disk(self.organizations_str)

        # write contacts csv file to disk
        self.contacts_file = self.write_string_to_disk(self.contacts_str)

        # write contacts csv file to disk
        self.secroles_file = self.write_string_to_disk(self.secroles_str)

        # create noclook user
        User.objects.get_or_create(username="noclook")[0]

    def tearDown(self):
        super(CsvImportTest, self).tearDown()
        # close organizations csv file
        self.organizations_file.close()

        # close contacts csv file
        self.contacts_file.close()

        # close contacts csv file
        self.secroles_file.close()

    def test_organizations_import(self):
        # call csvimport command (verbose 0)
        call_command(
            self.cmd_name,
            organizations=self.organizations_file,
            verbosity=0,
        )
        # check one of the organizations is present
        qs = NodeHandle.objects.filter(node_name='Browsecat')
        self.assertIsNotNone(qs)
        organization1 = qs.first()
        self.assertIsNotNone(organization1)
        self.assertIsInstance(organization1.get_node(), ncmodels.OrganizationModel)

        # check if one of them has a parent organization
        relations = organization1.get_node().get_relations()
        parent_relation = relations.get('Parent_of', None)
        self.assertIsNotNone(parent_relation)
        self.assertIsInstance(relations['Parent_of'][0]['node'], ncmodels.RelationModel)

    def test_contacts_import(self):
        # call csvimport command (verbose 0)
        call_command(
            self.cmd_name,
            contacts=self.contacts_file,
            verbosity=0,
        )
        # check one of the contacts is present
        full_name = '{} {}'.format('Caesar', 'Newby')
        qs = NodeHandle.objects.filter(node_name=full_name)
        self.assertIsNotNone(qs)
        contact1 = qs.first()
        self.assertIsNotNone(contact1)
        self.assertIsInstance(contact1.get_node(), ncmodels.ContactModel)

        # check if it has a role assigned
        qs = NodeHandle.objects.filter(node_name='Computer Systems Analyst III')
        self.assertIsNotNone(qs)
        role1 = qs.first()
        self.assertIsNotNone(role1)
        self.assertIsInstance(role1.get_node(), ncmodels.RoleModel)

        relations = role1.get_node().get_relations()
        relation = relations.get('Is', None)
        self.assertIsNotNone(relation)
        self.assertIsInstance(relations['Is'][0]['node'], ncmodels.RelationModel)

        # check if works for an organization
        qs = NodeHandle.objects.filter(node_name='Gabtune')
        self.assertIsNotNone(qs)
        organization1 = qs.first()
        self.assertIsNotNone(organization1)
        self.assertIsInstance(organization1.get_node(), ncmodels.OrganizationModel)

        relations = organization1.get_node().get_relations()
        relation = relations.get('Works_for', None)
        self.assertIsNotNone(relation)
        self.assertIsInstance(relations['Works_for'][0]['node'], ncmodels.RelationModel)

    def test_secroles_import(self):
        # call csvimport command (verbose 0)
        call_command(
            self.cmd_name,
            secroles=self.secroles_file,
            verbosity=0,
        )

        # check if the organization is present
        qs = NodeHandle.objects.filter(node_name='Chalmers')
        self.assertIsNotNone(qs)
        organization1 = qs.first()
        self.assertIsNotNone(organization1)

        # check a contact is present
        qs = NodeHandle.objects.filter(node_name='Hans Nilsson')
        self.assertIsNotNone(qs)
        contact1 = qs.first()
        self.assertIsNotNone(contact1)

        # check if role is created
        qs = NodeHandle.objects.filter(node_name='Övrig incidentkontakt')
        self.assertIsNotNone(qs)
        role1 = qs.first()
        self.assertIsNotNone(role1)

        relations = contact1.get_node().get_outgoing_relations()
        self.assertEquals(relations['Works_for'][0]['node'], organization1.get_node())
        self.assertIsInstance(relations['Works_for'][0]['node'], ncmodels.OrganizationModel)
        self.assertEquals(relations['Is'][0]['node'], role1.get_node())
        self.assertIsInstance(relations['Is'][0]['node'], ncmodels.RoleModel)

    def write_string_to_disk(self, string):
        # get random file
        tf = tempfile.NamedTemporaryFile()
        # write text
        tf.write(string)
        tf.flush()
        # return file descriptor
        return tf
